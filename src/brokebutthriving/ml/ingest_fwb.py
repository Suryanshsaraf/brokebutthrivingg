from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


SELECTED_COLUMNS = [
    "PUF_ID",
    "sample",
    "fpl",
    "FWBscore",
    "FSscore",
    "LMscore",
    "KHscore",
    "SAVEHABIT",
    "FRUGALITY",
    "FINGOALS",
    "ENDSMEET",
    "HOUSING",
    "LIVINGARRANGEMENT",
    "SAVINGSRANGES",
    "PRODHAVE_1",
    "PRODHAVE_4",
    "PRODHAVE_8",
    "EARNERS",
    "VOLATILITY",
    "SNAP",
    "MATHARDSHIP_1",
    "MATHARDSHIP_2",
    "MATHARDSHIP_3",
    "MATHARDSHIP_4",
    "MATHARDSHIP_5",
    "MATHARDSHIP_6",
    "COLLECT",
    "ABSORBSHOCK",
    "COVERCOSTS",
    "EMPLOY",
    "EMPLOY1_2",
    "EMPLOY1_3",
    "EMPLOY1_5",
    "agecat",
    "HHEDUC",
    "PPEDUC",
    "PAREDUC",
    "PPINCIMP",
    "finalwt",
]


def _to_float(value: object, invalid_values: set[float] | None = None) -> float | None:
    if pd.isna(value):
        return None
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None
    if invalid_values and converted in invalid_values:
        return None
    return converted


def _to_int(value: object, invalid_values: set[int] | None = None) -> int | None:
    if pd.isna(value):
        return None
    try:
        converted = int(value)
    except (TypeError, ValueError):
        return None
    if invalid_values and converted in invalid_values:
        return None
    return converted


def _to_bool(value: object, true_value: int = 1, false_value: int = 0) -> bool | None:
    converted = _to_int(value)
    if converted == true_value:
        return True
    if converted == false_value:
        return False
    return None


def build_fwb_frame(input_csv: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(input_csv, usecols=SELECTED_COLUMNS)
    records: list[dict[str, object]] = []

    for row in frame.to_dict("records"):
        record = {
            "source_dataset": "cfpb_fwb",
            "survey_year": 2016,
            "respondent_id": _to_int(row.get("PUF_ID")),
            "sample_id": _to_int(row.get("sample")),
            "sample_weight": _to_float(row.get("finalwt")),
            "poverty_level_band_code": _to_int(row.get("fpl"), {-1}),
            "fwb_score": _to_float(row.get("FWBscore"), {-1.0, -4.0}),
            "financial_skill_score": _to_float(row.get("FSscore"), {-1.0}),
            "money_management_score": _to_int(row.get("LMscore"), {-1}),
            "health_knowledge_score": _to_float(row.get("KHscore")),
            "save_habit_code": _to_int(row.get("SAVEHABIT"), {-1}),
            "frugality_code": _to_int(row.get("FRUGALITY"), {-1}),
            "financial_goals_code": _to_int(row.get("FINGOALS"), {-1}),
            "ends_meet_code": _to_int(row.get("ENDSMEET"), {-1}),
            "housing_status_code": _to_int(row.get("HOUSING"), {-1}),
            "living_arrangement_code": _to_int(row.get("LIVINGARRANGEMENT"), {-1}),
            "savings_range_code": _to_int(row.get("SAVINGSRANGES"), {-1, 98, 99}),
            "has_checking_or_savings_account": _to_bool(row.get("PRODHAVE_1")),
            "has_retirement_account": _to_bool(row.get("PRODHAVE_4")),
            "has_student_education_loan": _to_bool(row.get("PRODHAVE_8")),
            "household_earners_code": _to_int(row.get("EARNERS"), {-1}),
            "income_volatility_code": _to_int(row.get("VOLATILITY"), {-1}),
            "received_snap": _to_bool(row.get("SNAP")),
            "food_worry_hardship_code": _to_int(row.get("MATHARDSHIP_1"), {-1}),
            "food_shortage_hardship_code": _to_int(row.get("MATHARDSHIP_2"), {-1}),
            "housing_hardship_code": _to_int(row.get("MATHARDSHIP_3"), {-1}),
            "medical_access_hardship_code": _to_int(row.get("MATHARDSHIP_4"), {-1}),
            "medication_cost_hardship_code": _to_int(row.get("MATHARDSHIP_5"), {-1}),
            "utilities_hardship_code": _to_int(row.get("MATHARDSHIP_6"), {-1}),
            "contacted_debt_collector_past_12m": _to_bool(row.get("COLLECT")),
            "absorb_shock_confidence_code": _to_int(row.get("ABSORBSHOCK"), {-1, 8}),
            "cover_costs_strategy_code": _to_int(row.get("COVERCOSTS"), {-1}),
            "primary_employment_status_code": _to_int(row.get("EMPLOY"), {99}),
            "works_full_time": _to_bool(row.get("EMPLOY1_2")),
            "works_part_time": _to_bool(row.get("EMPLOY1_3")),
            "is_full_time_student": _to_bool(row.get("EMPLOY1_5")),
            "age_category_code": _to_int(row.get("agecat"), {-1}),
            "household_education_code": _to_int(row.get("HHEDUC"), {-1}),
            "respondent_education_code": _to_int(row.get("PPEDUC"), {-1}),
            "parent_education_code": _to_int(row.get("PAREDUC"), {-1}),
            "household_income_code": _to_int(row.get("PPINCIMP"), {-1}),
        }
        records.append(record)

    return pd.DataFrame.from_records(records)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normalize the CFPB Financial Well-Being public CSV into a modeling table."
    )
    parser.add_argument(
        "--input-csv",
        default="data/external/cfpb_fwb/cfpb_nfwbs_2016_data.csv",
        help="Path to the downloaded CFPB Financial Well-Being CSV",
    )
    parser.add_argument(
        "--output",
        default="artifacts/normalized/cfpb_fwb_normalized.csv",
        help="CSV output path for the normalized table",
    )
    args = parser.parse_args()

    frame = build_fwb_frame(args.input_csv)
    if frame.empty:
        raise SystemExit("FWB CSV produced no rows.")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)

    summary = {
        "rows": int(len(frame)),
        "rows_with_fwb": int(frame["fwb_score"].notna().sum()),
        "rows_with_student_loan_flag": int(frame["has_student_education_loan"].notna().sum()),
        "full_time_student_rows": int(frame["is_full_time_student"].fillna(False).sum()),
        "output": str(output_path),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
