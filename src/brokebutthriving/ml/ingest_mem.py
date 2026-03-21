from __future__ import annotations

import argparse
import csv
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd


Row = dict[str, str]
Resolver = Callable[[Row], object]


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _to_int(value: str | None) -> int | None:
    cleaned = _clean(value)
    if cleaned is None:
        return None
    try:
        return int(float(cleaned))
    except ValueError:
        return None


def _to_float(value: str | None) -> float | None:
    cleaned = _clean(value)
    if cleaned is None:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _map_value(value: str | None, mapping: dict[str, object]) -> object:
    cleaned = _clean(value)
    if cleaned is None:
        return None
    return mapping.get(cleaned)


def _bool_01(value: str | None) -> bool | None:
    return _map_value(value, {"0": False, "1": True})


def _col(column: str, transform: Callable[[str | None], object] | None = None) -> Resolver:
    def resolver(row: Row) -> object:
        value = row.get(column)
        if transform is None:
            return _clean(value)
        return transform(value)

    return resolver


def _any_yes(columns: list[str]) -> Resolver:
    def resolver(row: Row) -> bool | None:
        values = [_clean(row.get(column)) for column in columns]
        present = [value for value in values if value is not None]
        if not present:
            return None
        return any(value == "1" for value in present)

    return resolver


def _map_band(mapping: dict[str, str]) -> Callable[[str | None], str | None]:
    def resolver(value: str | None) -> str | None:
        mapped = _map_value(value, mapping)
        return mapped if isinstance(mapped, str) or mapped is None else str(mapped)

    return resolver


ACCOUNT_BALANCE_BANDS = {
    "1": "0",
    "2": "lt_100",
    "3": "101_to_500",
    "4": "501_to_1000",
    "5": "1001_to_5000",
    "6": "5001_to_10000",
    "7": "10001_to_20000",
    "8": "20001_plus",
}

SAVINGS_HABIT_BANDS = {
    "1": "not_saving",
    "2": "saving_when_possible",
    "3": "saving_regularly",
}

EXPENSE_COVERAGE_BANDS = {
    "1": "lt_2_weeks",
    "2": "about_1_month",
    "3": "about_2_months",
    "4": "3_to_6_months",
    "5": "gt_6_months",
}

DIFFICULTY_FREQUENCY_BANDS = {
    "1": "once",
    "2": "twice",
    "3": "three_to_four_times",
    "4": "five_to_twelve_times",
    "5": "gt_twelve_times",
}

DIFFICULTY_RECENCY_3_BANDS = {
    "1": "1_to_3_months",
    "2": "4_to_6_months",
    "3": "7_to_12_months",
}

DIFFICULTY_RECENCY_4_BANDS = {
    "1": "lt_1_month",
    "2": "1_to_3_months",
    "3": "4_to_6_months",
    "4": "7_to_12_months",
}

EVENT_EXPECTEDNESS = {"1": "expected", "2": "unexpected"}
MEDICAL_COLLECTION_COUNT = {"1": "1_bill", "2": "2_to_4_bills", "3": "5_plus_bills"}
MEDICAL_COLLECTION_FREQUENCY = {
    "1": "more_than_weekly",
    "2": "weekly",
    "3": "few_times_per_month",
    "4": "monthly",
    "5": "once_every_few_months",
    "6": "once",
}
HOUSING_STATUS = {"1": "renter", "2": "homeowner", "3": "neither"}
CURRENT_SCHOOL_STATUS = {"1": "full_time", "2": "part_time", "3": "not_attending"}
MEDICAL_DEBT_SUED_STATUS = {"1": "yes_ongoing", "2": "yes_concluded", "3": "no"}


@dataclass(frozen=True)
class WaveConfig:
    sample_id: int
    wave_id: str
    survey_year: int
    weight_column: str | None
    field_resolvers: dict[str, Resolver]


WAVE_CONFIGS: list[WaveConfig] = [
    WaveConfig(
        sample_id=1,
        wave_id="w1",
        survey_year=2019,
        weight_column="w1weight",
        field_resolvers={"fwb_score": _col("w1fwb", _to_float)},
    ),
    WaveConfig(
        sample_id=1,
        wave_id="w2",
        survey_year=2020,
        weight_column="w2weight",
        field_resolvers={"fwb_score": _col("w2fwb", _to_float)},
    ),
    WaveConfig(
        sample_id=1,
        wave_id="w3",
        survey_year=2021,
        weight_column="w3weight",
        field_resolvers={"fwb_score": _col("w3fwb", _to_float)},
    ),
    WaveConfig(
        sample_id=3,
        wave_id="w1",
        survey_year=2022,
        weight_column="weight",
        field_resolvers={
            "checking_savings_balance_band": _col("q15", _map_band(ACCOUNT_BALANCE_BANDS)),
            "savings_habit_band": _col("q16", _map_band(SAVINGS_HABIT_BANDS)),
            "expects_bill_difficulty_next_12m": _col("q49", _bool_01),
            "had_bill_difficulty_past_12m": _col("q50", _bool_01),
            "bill_difficulty_frequency_band": _col("q51", _map_band(DIFFICULTY_FREQUENCY_BANDS)),
            "bill_difficulty_recency_band": _col("q52", _map_band(DIFFICULTY_RECENCY_3_BANDS)),
            "difficulty_event_amount": _col("q54", _to_float),
            "difficulty_event_expectedness": _col("q55", _map_band(EVENT_EXPECTEDNESS)),
            "used_nonretirement_savings": _col("q56a", _bool_01),
            "used_retirement_savings": _col("q56b", _bool_01),
            "cut_nonessential_spending": _col("q56e", _bool_01),
            "used_credit": _col("q56h", _bool_01),
            "borrowed_from_family_or_friends": _col("q56i", _bool_01),
            "used_payday_or_auto_title_loan": _col("q56j", _bool_01),
            "housing_status": _col("housing", _map_band(HOUSING_STATUS)),
            "fwb_score": _col("fwb", _to_float),
        },
    ),
    WaveConfig(
        sample_id=3,
        wave_id="w2",
        survey_year=2023,
        weight_column="w2weight",
        field_resolvers={"fwb_score": _col("w2fwb", _to_float), "housing_status": _col("housing", _map_band(HOUSING_STATUS))},
    ),
    WaveConfig(
        sample_id=4,
        wave_id="w1",
        survey_year=2023,
        weight_column="weight",
        field_resolvers={
            "checking_savings_balance_band": _col("q17", _map_band(ACCOUNT_BALANCE_BANDS)),
            "expense_coverage_horizon_band": _col("q18", _map_band(EXPENSE_COVERAGE_BANDS)),
            "savings_habit_band": _col("q19", _map_band(SAVINGS_HABIT_BANDS)),
            "bill_difficulty_recency_band": _col("q37", _map_band(DIFFICULTY_RECENCY_4_BANDS)),
            "difficulty_event_caused_by_specific_event": _col("q38", _bool_01),
            "medical_debt_sued_status": _col("q49", _map_band(MEDICAL_DEBT_SUED_STATUS)),
            "has_medical_credit_card": _col("q50", _bool_01),
            "provider_threatened_collection": _col("q52", _bool_01),
            "medical_collection_contact": _col("q53", _bool_01),
            "medical_collection_count_band": _col("q54", _map_band(MEDICAL_COLLECTION_COUNT)),
            "medical_collection_amount": _col("q56", _to_float),
            "medical_collection_disputed": _col("q57", _bool_01),
            "housing_status": _col("housing", _map_band(HOUSING_STATUS)),
            "fwb_score": _col("fwb", _to_float),
        },
    ),
    WaveConfig(
        sample_id=4,
        wave_id="w2",
        survey_year=2024,
        weight_column="w2weight",
        field_resolvers={"housing_status": _col("w2housing", _map_band(HOUSING_STATUS)), "fwb_score": _col("w2fwb", _to_float)},
    ),
    WaveConfig(
        sample_id=5,
        wave_id="w1",
        survey_year=2024,
        weight_column="weight",
        field_resolvers={
            "has_checking_savings_account": _col("q15", _bool_01),
            "checking_savings_balance_band": _col("q16", _map_band(ACCOUNT_BALANCE_BANDS)),
            "owns_rental_property_for_income": _col("q24", _bool_01),
            "difficulty_paying_home_repair": _col("q44c", _bool_01),
            "difficulty_paying_food": _col("q44d", _bool_01),
            "difficulty_paying_utilities": _col("q44f", _bool_01),
            "difficulty_paying_taxes_or_legal_bills": _col("q44g", _bool_01),
            "medical_financed_with_credit_or_loan": _col("q50", _bool_01),
            "out_of_pocket_medical_expense_past_12m": _col("q52", _bool_01),
            "out_of_pocket_medical_amount": _col("q53", _to_float),
            "medical_collection_contact": _col("q55", _bool_01),
            "medical_collection_count_band": _col("q56", _map_band(MEDICAL_COLLECTION_COUNT)),
            "medical_collection_amount": _col("q57", _to_float),
            "housing_status": _col("housing", _map_band(HOUSING_STATUS)),
            "fwb_score": _col("fwb", _to_float),
            "any_unexpected_expense_past_12m": _any_yes(
                ["q37a1", "q37b1", "q37c1", "q37d1", "q37e1", "q37f1", "q37g1", "q37h1", "q37i1"]
            ),
            "any_income_loss_past_12m": _any_yes(
                ["q38a1", "q38b1", "q38c1", "q38d1", "q38e1", "q38f1", "q38g1", "q38h1", "q38i1", "q38j1", "q38l1"]
            ),
        },
    ),
    WaveConfig(
        sample_id=5,
        wave_id="w2",
        survey_year=2025,
        weight_column="w2weight_paper",
        field_resolvers={
            "medical_collection_contact": _col("w2q37", _bool_01),
            "medical_collection_count_band": _col("w2q38", _map_band(MEDICAL_COLLECTION_COUNT)),
            "medical_financed_with_credit_or_loan": _col("w2q50", _bool_01),
            "has_credit_card": _col("w2q56", _bool_01),
            "credit_card_late_fee_past_12m": _col("w2q57", _bool_01),
            "fwb_score": _col("w2fwb", _to_float),
        },
    ),
    WaveConfig(
        sample_id=6,
        wave_id="w1",
        survey_year=2025,
        weight_column="weight_paper",
        field_resolvers={
            "has_checking_savings_account": _col("q15", _bool_01),
            "checking_savings_balance_band": _col("q16", _map_band(ACCOUNT_BALANCE_BANDS)),
            "expense_coverage_horizon_band": _col("q20", _map_band(EXPENSE_COVERAGE_BANDS)),
            "emergency_savings_amount": _col("q24", _to_float),
            "expects_bill_difficulty_next_12m": _col("q37", _bool_01),
            "had_bill_difficulty_past_12m": _col("q38", _bool_01),
            "difficulty_paying_mortgage_or_rent": _col("q41e", _bool_01),
            "used_nonretirement_savings": _col("q44c", _bool_01),
            "used_retirement_savings": _col("q44d", _bool_01),
            "cut_nonessential_spending": _col("q44f", _bool_01),
            "skipped_other_bill_or_paid_late": _col("q44g", _bool_01),
            "medical_debt_past_due": _col("q50", _bool_01),
            "medical_payment_plan": _col("q51", _bool_01),
            "medical_financed_with_credit_or_loan": _col("q52", _bool_01),
            "has_medical_credit_card": _col("q53", _bool_01),
            "medical_collection_contact": _col("q54", _bool_01),
            "medical_collection_count_band": _col("q55", _map_band(MEDICAL_COLLECTION_COUNT)),
            "medical_collection_frequency_band": _col("q56", _map_band(MEDICAL_COLLECTION_FREQUENCY)),
            "medical_collection_amount": _col("q57", _to_float),
            "current_school_status": _col("q112", _map_band(CURRENT_SCHOOL_STATUS)),
            "housing_status": _col("housing", _map_band(HOUSING_STATUS)),
            "fwb_score": _col("fwb", _to_float),
        },
    ),
]


def _iter_mem_rows(zip_path: Path):
    with zipfile.ZipFile(zip_path) as archive:
        csv_name = next(name for name in archive.namelist() if name.lower().endswith(".csv"))
        with archive.open(csv_name) as handle:
            reader = csv.DictReader((line.decode("utf-8-sig") for line in handle))
            for row in reader:
                yield row


def build_mem_frame(input_dir: str | Path) -> pd.DataFrame:
    input_dir = Path(input_dir)
    records: list[dict[str, object]] = []

    for config in WAVE_CONFIGS:
        zip_path = input_dir / f"cfpb_making-ends-meet_sample-{config.sample_id}.zip"
        if not zip_path.exists():
            continue

        for row in _iter_mem_rows(zip_path):
            record: dict[str, object] = {
                "source_dataset": "cfpb_mem",
                "sample_id": config.sample_id,
                "wave_id": config.wave_id,
                "survey_year": config.survey_year,
                "respondent_id": _clean(row.get("ID")),
                "sample_weight": _to_float(row.get(config.weight_column)) if config.weight_column else None,
            }

            populated = False
            for field_name, resolver in config.field_resolvers.items():
                value = resolver(row)
                record[field_name] = value
                populated = populated or value is not None

            if populated:
                records.append(record)

    return pd.DataFrame.from_records(records)


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize downloaded CFPB Making Ends Meet ZIP files.")
    parser.add_argument("--input-dir", default="data/external/cfpb_mem", help="Directory with MEM zip files")
    parser.add_argument(
        "--output",
        default="artifacts/normalized/cfpb_mem_normalized.csv",
        help="CSV output path for the normalized table",
    )
    args = parser.parse_args()

    frame = build_mem_frame(args.input_dir)
    if frame.empty:
        raise SystemExit("No MEM ZIP files found to ingest.")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)

    summary = {
        "rows": int(len(frame)),
        "sample_wave_counts": (
            frame.groupby(["sample_id", "wave_id"])["respondent_id"].count().rename("rows").reset_index().to_dict("records")
        ),
        "rows_with_fwb": int(frame["fwb_score"].notna().sum()) if "fwb_score" in frame else 0,
        "rows_with_housing": int(frame["housing_status"].notna().sum()) if "housing_status" in frame else 0,
        "output": str(output_path),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
