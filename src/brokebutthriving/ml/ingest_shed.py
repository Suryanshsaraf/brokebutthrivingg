from __future__ import annotations

import argparse
import csv
import json
import zipfile
from pathlib import Path

import pandas as pd


VALUE_MAPS = {
    "B2": {
        "1": "finding_it_difficult",
        "2": "just_getting_by",
        "3": "doing_okay",
        "4": "living_comfortably",
        "finding it very difficult to get by": "finding_it_difficult",
        "finding it difficult to get by": "finding_it_difficult",
        "just getting by": "just_getting_by",
        "doing okay": "doing_okay",
        "living comfortably": "living_comfortably",
    },
    "B3": {
        "1": "much_worse_off",
        "2": "somewhat_worse_off",
        "3": "about_the_same",
        "4": "somewhat_better_off",
        "5": "much_better_off",
        "much worse": "much_worse_off",
        "somewhat worse": "somewhat_worse_off",
        "much worse off": "much_worse_off",
        "somewhat worse off": "somewhat_worse_off",
        "about the same": "about_the_same",
        "somewhat better off": "somewhat_better_off",
        "much better off": "much_better_off",
    },
    "D1G": {
        "0": "not_currently_student",
        "1": "part_time_student",
        "2": "full_time_student",
        "no": "not_currently_student",
        "yes, as a part-time student": "part_time_student",
        "yes, as a full-time student": "full_time_student",
    },
    "ED0": {
        "1": "less_than_high_school",
        "2": "high_school_or_ged",
        "3": "some_college_no_degree",
        "4": "certificate_or_technical_degree",
        "5": "associate_degree",
        "6": "bachelors_degree",
        "7": "masters_degree",
        "8": "professional_degree",
        "9": "doctoral_degree",
        "less than high school degree": "less_than_high_school",
        "high school degree or ged": "high_school_or_ged",
        "some college but no degree (including currently enrolled in college)": "some_college_no_degree",
        "certificate or technical degree": "certificate_or_technical_degree",
        "associate degree": "associate_degree",
        "bachelor’s degree": "bachelors_degree",
        "bachelor's degree": "bachelors_degree",
        "master’s degree": "masters_degree",
        "master's degree": "masters_degree",
        "professional degree (e.g., mba, md, jd)": "professional_degree",
        "professional degree (e.g. mba, md, jd)": "professional_degree",
        "doctoral degree": "doctoral_degree",
    },
    "ED0B": {
        "1": "high_school_or_ged_program",
        "2": "vocational_or_technical_program",
        "3": "associates_program",
        "4": "bachelors_program",
        "5": "masters_program",
        "6": "professional_program",
        "7": "doctoral_program",
        "8": "other_program",
        "high school or ged program": "high_school_or_ged_program",
        "vocational or technical program": "vocational_or_technical_program",
        "associate degree program": "associates_program",
        "bachelor’s degree program": "bachelors_program",
        "bachelor's degree program": "bachelors_program",
        "master’s degree program": "masters_program",
        "master's degree program": "masters_program",
        "professional degree program": "professional_program",
        "doctoral degree program": "doctoral_program",
        "other": "other_program",
    },
    "X12_c": {"0": "not_a_concern", "1": "minor_concern", "2": "major_concern", "not a concern": "not_a_concern", "minor concern": "minor_concern", "major concern": "major_concern"},
    "X12_e": {"0": "not_a_concern", "1": "minor_concern", "2": "major_concern", "not a concern": "not_a_concern", "minor concern": "minor_concern", "major concern": "major_concern"},
    "X12_g": {"0": "not_a_concern", "1": "minor_concern", "2": "major_concern", "not a concern": "not_a_concern", "minor concern": "minor_concern", "major concern": "major_concern"},
    "SL1": {"0": "no", "1": "yes", "no": "no", "yes": "yes"},
    "SL6": {"0": "no", "1": "yes", "no": "no", "yes": "yes"},
    "ppemploy": {
        "1": "working_full_time",
        "2": "working_part_time",
        "3": "not_working",
        "working full-time": "working_full_time",
        "working part-time": "working_part_time",
        "not working": "not_working",
    },
    "ppgender": {"1": "male", "2": "female", "male": "male", "female": "female"},
    "ppinc7": {
        "1": "lt_10k",
        "2": "10k_24k",
        "3": "25k_49k",
        "4": "50k_74k",
        "5": "75k_99k",
        "6": "100k_149k",
        "7": "150k_plus",
        "less than $10,000": "lt_10k",
        "$10,000 to $24,999": "10k_24k",
        "$25,000 to $49,999": "25k_49k",
        "$50,000 to $74,999": "50k_74k",
        "$75,000 to $99,999": "75k_99k",
        "$100,000 to $149,999": "100k_149k",
        "$150,000 or more": "150k_plus",
    },
    "ppmarit5": {
        "1": "married",
        "2": "widowed",
        "3": "divorced",
        "4": "separated",
        "5": "never_married",
        "now married": "married",
        "widowed": "widowed",
        "divorced": "divorced",
        "separated": "separated",
        "never married": "never_married",
    },
}


SELECTED_COLUMNS = [
    "shedid",
    "weight",
    "weight_pop",
    "panel_weight",
    "panel_weight_pop",
    "B2",
    "B3",
    "B3A_a",
    "B3A_b",
    "X12_c",
    "X12_e",
    "X12_g",
    "D1G",
    "ED0",
    "ED0B",
    "SL1",
    "SL3",
    "SL4",
    "SL6",
    "ppage",
    "ppemploy",
    "ppgender",
    "ppinc7",
    "ppmarit5",
    "pphhsize",
    "pprent",
]


def _iter_rows_from_zip(zip_path: Path):
    with zipfile.ZipFile(zip_path) as archive:
        csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if not csv_names:
            raise ValueError(f"No CSV file found in {zip_path}")

        with archive.open(csv_names[0]) as handle:
            data = handle.read()
            text = None
            for encoding in ("utf-8-sig", "cp1252", "latin-1"):
                try:
                    text = data.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            if text is None:
                raise ValueError(f"Could not decode CSV contents from {zip_path}")

            reader = csv.DictReader(text.splitlines())
            for row in reader:
                yield row


def _dataset_year(zip_path: Path) -> int:
    stem = zip_path.stem
    for part in stem.split("_"):
        if part.isdigit() and len(part) == 4:
            return int(part)
    raise ValueError(f"Could not infer year from {zip_path.name}")


def _normalize_value(column: str, value: str | None):
    if value is None or value == "":
        return None
    cleaned = value.strip()
    if cleaned.lower() in {"refused", "not in universe (not asked)", "don’t know", "don't know"}:
        return None
    mapped = VALUE_MAPS.get(column)
    if mapped is None:
        return cleaned
    return mapped.get(value, mapped.get(cleaned.lower(), cleaned))


def _to_float(value: str | None) -> float | None:
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _to_int(value: str | None) -> int | None:
    if value in {None, ""}:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def build_shed_frame(input_dir: str | Path) -> pd.DataFrame:
    input_dir = Path(input_dir)
    zip_paths = sorted(input_dir.glob("shed_*.zip"))
    records: list[dict[str, object]] = []

    for zip_path in zip_paths:
        year = _dataset_year(zip_path)
        for row in _iter_rows_from_zip(zip_path):
            record = {
                "source_dataset": "fed_shed",
                "survey_year": year,
                "respondent_id": row.get("shedid"),
                "sample_weight": _to_float(row.get("weight")),
                "population_weight": _to_float(row.get("weight_pop")),
                "panel_weight": _to_float(row.get("panel_weight")),
                "panel_population_weight": _to_float(row.get("panel_weight_pop")),
                "age": _to_int(row.get("ppage")),
                "household_size": _to_int(row.get("pphhsize")),
                "housing_tenure_code": _to_int(row.get("pprent")),
                "current_student_status": _normalize_value("D1G", row.get("D1G")),
                "education_level": _normalize_value("ED0", row.get("ED0")),
                "current_program_type": _normalize_value("ED0B", row.get("ED0B")),
                "employment_status": _normalize_value("ppemploy", row.get("ppemploy")),
                "gender": _normalize_value("ppgender", row.get("ppgender")),
                "household_income_band": _normalize_value("ppinc7", row.get("ppinc7")),
                "marital_status": _normalize_value("ppmarit5", row.get("ppmarit5")),
                "financial_management_status": _normalize_value("B2", row.get("B2")),
                "financial_change_12m": _normalize_value("B3", row.get("B3")),
                "lower_income_flag": _to_int(row.get("B3A_a")),
                "higher_expenses_flag": _to_int(row.get("B3A_b")),
                "housing_concern_level": _normalize_value("X12_c", row.get("X12_c")),
                "making_ends_meet_concern": _normalize_value("X12_e", row.get("X12_e")),
                "student_loan_concern": _normalize_value("X12_g", row.get("X12_g")),
                "has_student_loan_debt": _normalize_value("SL1", row.get("SL1")),
                "student_loan_amount_band": _to_int(row.get("SL3")),
                "student_loan_payment_band": _to_int(row.get("SL4")),
                "student_loan_delinquent": _normalize_value("SL6", row.get("SL6")),
            }

            record["is_current_student"] = int(record["current_student_status"] in {"part_time_student", "full_time_student"})
            record["is_full_time_student"] = int(record["current_student_status"] == "full_time_student")
            record["is_financially_strained"] = int(
                record["financial_management_status"] in {"finding_it_difficult", "just_getting_by"}
            )
            record["is_worse_off_than_last_year"] = int(
                record["financial_change_12m"] in {"much_worse_off", "somewhat_worse_off"}
            )
            record["has_hardship_signal"] = int(
                any(
                    value in {"major_concern", "minor_concern"}
                    for value in (
                        record["making_ends_meet_concern"],
                        record["housing_concern_level"],
                        record["student_loan_concern"],
                    )
                )
            )

            records.append(record)

    return pd.DataFrame.from_records(records)


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize downloaded SHED ZIP files into a modeling table.")
    parser.add_argument("--input-dir", default="data/external/fed_shed", help="Directory with SHED zip files")
    parser.add_argument(
        "--output",
        default="artifacts/normalized/fed_shed_normalized.csv",
        help="CSV output path for the normalized table",
    )
    args = parser.parse_args()

    frame = build_shed_frame(args.input_dir)
    if frame.empty:
        raise SystemExit("No SHED ZIP files found to ingest.")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)

    summary = {
        "rows": int(len(frame)),
        "years": sorted(frame["survey_year"].dropna().unique().tolist()),
        "current_student_rows": int(frame["is_current_student"].sum()),
        "financially_strained_rows": int(frame["is_financially_strained"].sum()),
        "output": str(output_path),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
