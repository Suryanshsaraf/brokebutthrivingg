from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


ARCHETYPE_COLUMNS = {
    "stress_spending_score": "stress",
    "social_pressure_score": "social_pressure",
    "boredom_spending_score": "boredom",
}


def _read_table(connection: sqlite3.Connection, table_name: str) -> pd.DataFrame:
    try:
        return pd.read_sql_query(f"SELECT * FROM {table_name}", connection)
    except Exception:
        return pd.DataFrame()


def _normalize_datetime(df: pd.DataFrame, column: str) -> pd.DataFrame:
    if column in df.columns:
        df[column] = pd.to_datetime(df[column], utc=True, errors="coerce")
    return df


def _dominant_archetype(surveys: pd.DataFrame) -> pd.DataFrame:
    if surveys.empty:
        return pd.DataFrame(columns=["participant_id", "primary_archetype"])

    score_frame = surveys[["participant_id", *ARCHETYPE_COLUMNS.keys()]].copy()
    rename_map = ARCHETYPE_COLUMNS
    score_frame = score_frame.rename(columns=rename_map)
    archetype_cols = list(rename_map.values())
    score_frame["primary_archetype"] = score_frame[archetype_cols].idxmax(axis=1)
    return score_frame[["participant_id", "primary_archetype"]]


def build_daily_dataset(db_path: str | Path) -> pd.DataFrame:
    db_path = Path(db_path)
    if not db_path.exists():
        return pd.DataFrame()

    with sqlite3.connect(db_path) as connection:
        participants = _read_table(connection, "participant")
        surveys = _read_table(connection, "behaviorsurvey")
        expenses = _read_table(connection, "expenseentry")
        cashflows = _read_table(connection, "cashflowentry")
        checkins = _read_table(connection, "dailycheckin")

    if participants.empty:
        return pd.DataFrame()

    participants["created_at"] = pd.to_datetime(participants["created_at"], utc=True, errors="coerce")
    participants["created_at"] = participants["created_at"].dt.tz_convert(None)
    if not expenses.empty:
        expenses = _normalize_datetime(expenses, "occurred_at")
        expenses["date"] = expenses["occurred_at"].dt.date
    if not cashflows.empty:
        cashflows = _normalize_datetime(cashflows, "occurred_at")
        cashflows["date"] = cashflows["occurred_at"].dt.date
    if not checkins.empty:
        checkins["check_in_date"] = pd.to_datetime(checkins["check_in_date"], errors="coerce").dt.date

    records: list[pd.DataFrame] = []
    archetypes = _dominant_archetype(surveys)

    for participant in participants.to_dict("records"):
        participant_id = participant["id"]
        participant_expenses = expenses[expenses["participant_id"] == participant_id].copy()
        participant_cashflows = cashflows[cashflows["participant_id"] == participant_id].copy()
        participant_checkins = checkins[checkins["participant_id"] == participant_id].copy()

        event_dates: list[pd.Timestamp] = []
        if not participant_expenses.empty:
            event_dates.append(pd.to_datetime(participant_expenses["date"]).min())
        if not participant_cashflows.empty:
            event_dates.append(pd.to_datetime(participant_cashflows["date"]).min())
        if not participant_checkins.empty:
            event_dates.append(pd.to_datetime(participant_checkins["check_in_date"]).min())
        event_dates.append(pd.Timestamp(participant["created_at"]).normalize())

        start_date = min(event_dates)
        end_date = max(pd.Timestamp.now().normalize(), start_date)
        date_range = pd.date_range(start=start_date, end=end_date, freq="D")
        frame = pd.DataFrame({"date": date_range.date})
        frame["participant_id"] = participant_id

        if not participant_expenses.empty:
            spend_daily = (
                participant_expenses.groupby("date")
                .agg(
                    spend_total=("amount", "sum"),
                    tx_count=("id", "count"),
                    social_tx_count=("is_social", "sum"),
                    essential_tx_count=("is_essential", "sum"),
                )
                .reset_index()
            )
            category_daily = (
                participant_expenses.pivot_table(
                    index="date",
                    columns="category",
                    values="amount",
                    aggfunc="sum",
                    fill_value=0,
                )
                .reset_index()
            )
            category_daily.columns = [
                "date" if column == "date" else f"spend_{column}" for column in category_daily.columns
            ]
            frame = frame.merge(spend_daily, on="date", how="left").merge(category_daily, on="date", how="left")
        else:
            frame["spend_total"] = 0.0
            frame["tx_count"] = 0
            frame["social_tx_count"] = 0
            frame["essential_tx_count"] = 0

        if not participant_cashflows.empty:
            inflow_daily = (
                participant_cashflows.groupby("date")
                .agg(inflow_total=("amount", "sum"), inflow_tx_count=("id", "count"))
                .reset_index()
            )
            frame = frame.merge(inflow_daily, on="date", how="left")
        else:
            frame["inflow_total"] = 0.0
            frame["inflow_tx_count"] = 0

        if not participant_checkins.empty:
            checkin_daily = participant_checkins.rename(columns={"check_in_date": "date"})[
                [
                    "date",
                    "opening_balance",
                    "closing_balance",
                    "stress_level",
                    "exam_pressure",
                    "social_pressure",
                    "mood_energy",
                    "sleep_hours",
                ]
            ]
            frame = frame.merge(checkin_daily, on="date", how="left")

        for column, default_value in {
            "opening_balance": np.nan,
            "closing_balance": np.nan,
            "stress_level": 3,
            "exam_pressure": 1,
            "social_pressure": 1,
            "mood_energy": 3,
            "sleep_hours": 7.0,
        }.items():
            if column not in frame.columns:
                frame[column] = default_value

        frame = frame.fillna(
            {
                "spend_total": 0.0,
                "tx_count": 0,
                "social_tx_count": 0,
                "essential_tx_count": 0,
                "inflow_total": 0.0,
                "inflow_tx_count": 0,
                "stress_level": 3,
                "exam_pressure": 1,
                "social_pressure": 1,
                "mood_energy": 3,
                "sleep_hours": 7.0,
            }
        )

        category_columns = [column for column in frame.columns if column.startswith("spend_")]
        for column in category_columns:
            frame[column] = frame[column].fillna(0.0)

        frame["day_of_week"] = pd.to_datetime(frame["date"]).dt.dayofweek
        frame["day_of_month"] = pd.to_datetime(frame["date"]).dt.day
        frame["days_remaining_in_month"] = (
            pd.to_datetime(frame["date"]).dt.days_in_month - frame["day_of_month"]
        )
        frame["is_weekend"] = (frame["day_of_week"] >= 5).astype(int)
        frame["net_flow"] = frame["inflow_total"] - frame["spend_total"]
        frame["estimated_balance"] = participant["starting_balance"] + frame["net_flow"].cumsum()

        if "closing_balance" in frame.columns:
            frame["reported_closing_balance"] = frame["closing_balance"]
        else:
            frame["reported_closing_balance"] = np.nan

        frame["rolling_spend_7d"] = frame["spend_total"].rolling(7, min_periods=1).mean()
        frame["rolling_spend_14d"] = frame["spend_total"].rolling(14, min_periods=1).mean()
        frame["rolling_social_7d"] = frame["social_tx_count"].rolling(7, min_periods=1).mean()

        future_min = (
            frame["estimated_balance"]
            .iloc[::-1]
            .rolling(14, min_periods=1)
            .min()
            .iloc[::-1]
            .shift(-1)
        )
        future_spend = (
            frame["spend_total"]
            .iloc[::-1]
            .rolling(7, min_periods=1)
            .sum()
            .iloc[::-1]
            .shift(-1)
        )
        frame["risk_label_14d"] = (future_min <= 0).astype(int)
        frame["spend_next_7d"] = future_spend.fillna(0.0)

        frame["monthly_budget"] = participant["monthly_budget"]
        frame["monthly_income"] = participant["monthly_income"]
        frame["living_situation"] = participant["living_situation"]
        frame["dietary_preference"] = participant["dietary_preference"]

        records.append(frame)

    dataset = pd.concat(records, ignore_index=True)
    dataset = dataset.merge(archetypes, on="participant_id", how="left")

    dataset["budget_utilization_ratio"] = dataset["spend_total"] / dataset["monthly_budget"].replace(0, np.nan)
    dataset["budget_utilization_ratio"] = dataset["budget_utilization_ratio"].replace([np.inf, -np.inf], 0).fillna(0)

    return dataset.sort_values(["participant_id", "date"]).reset_index(drop=True)
