from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path

import pandas as pd

from brokebutthriving.ml.bls_cex import (
    BLS_INTERVIEW_RAW_COLUMNS,
    BLS_INTERVIEW_RENAME_MAP,
    quarter_index,
)


def _infer_archive_year(zip_path: Path) -> int:
    match = re.search(r"(\d{2})", zip_path.stem)
    if not match:
        raise ValueError(f"Could not infer archive year from {zip_path.name}")
    return 2000 + int(match.group(1))


def _revision_priority(filename: str) -> int:
    return 1 if filename.lower().endswith("x.csv") else 0


def _read_fmli_csvs(zip_path: Path) -> list[pd.DataFrame]:
    frames: list[pd.DataFrame] = []
    archive_year = _infer_archive_year(zip_path)
    with zipfile.ZipFile(zip_path) as archive:
        fmli_names = sorted(
            name for name in archive.namelist() if "/fmli" in name.lower() and name.lower().endswith(".csv")
        )
        for filename in fmli_names:
            with archive.open(filename) as handle:
                frame = pd.read_csv(
                    handle,
                    usecols=lambda column: column in BLS_INTERVIEW_RAW_COLUMNS,
                    low_memory=False,
                )
            for column in BLS_INTERVIEW_RAW_COLUMNS:
                if column not in frame.columns:
                    frame[column] = pd.NA
            frame = frame[BLS_INTERVIEW_RAW_COLUMNS]
            frame["archive_year"] = archive_year
            frame["source_file"] = filename
            frame["revision_priority"] = _revision_priority(filename)
            frames.append(frame)
    return frames


def build_bls_cex_interview_frame(input_dir: str | Path) -> pd.DataFrame:
    input_dir = Path(input_dir)
    zip_paths = sorted(input_dir.glob("intrvw*.zip"))
    if not zip_paths:
        return pd.DataFrame()

    raw_frames: list[pd.DataFrame] = []
    for zip_path in zip_paths:
        raw_frames.extend(_read_fmli_csvs(zip_path))

    frame = pd.concat(raw_frames, ignore_index=True)
    frame = frame.rename(columns=BLS_INTERVIEW_RENAME_MAP)
    frame["source_dataset"] = "bls_cex_interview"
    frame["panel_id"] = frame["panel_id"].astype("Int64").astype(str)
    frame["quarter_index"] = frame.apply(
        lambda row: quarter_index(int(row["interview_year"]), int(row["interview_month"])),
        axis=1,
    )

    frame = frame.sort_values(
        ["panel_id", "quarter_index", "archive_year", "revision_priority", "source_file"]
    )
    frame = frame.drop_duplicates(subset=["panel_id", "quarter_index"], keep="last").reset_index(drop=True)

    frame["quarter_label"] = frame["interview_year"].astype("Int64").astype(str) + "Q" + (
        ((frame["interview_month"].astype(float) - 1) // 3 + 1).astype("Int64").astype(str)
    )
    frame["quarterly_income_proxy"] = pd.to_numeric(frame["after_tax_income_annual"], errors="coerce") / 4.0
    frame["young_adult_proxy"] = (pd.to_numeric(frame["age_ref"], errors="coerce") <= 30).astype(int)
    frame["student_debt_proxy"] = (
        pd.to_numeric(frame["student_loan_balance"], errors="coerce").fillna(0) > 0
    ).astype(int)

    frame["essential_spend_q"] = frame[
        [
            "food_expenditure_q",
            "housing_expenditure_q",
            "utilities_expenditure_q",
            "transportation_expenditure_q",
            "healthcare_expenditure_q",
        ]
    ].apply(pd.to_numeric, errors="coerce").sum(axis=1, min_count=1)
    frame["discretionary_spend_q"] = frame[
        [
            "entertainment_expenditure_q",
            "apparel_expenditure_q",
            "alcohol_beverages_q",
            "tobacco_expenditure_q",
            "misc_expenditure_q",
            "reading_q",
            "education_expenditure_q",
            "cash_contributions_q",
        ]
    ].apply(pd.to_numeric, errors="coerce").sum(axis=1, min_count=1)

    total_spend = pd.to_numeric(frame["total_expenditure_q"], errors="coerce")
    quarterly_income = pd.to_numeric(frame["quarterly_income_proxy"], errors="coerce")
    frame["spend_to_income_proxy_q"] = total_spend / quarterly_income.replace({0: pd.NA})
    frame["food_away_share"] = pd.to_numeric(frame["food_away_q"], errors="coerce") / total_spend.replace(
        {0: pd.NA}
    )
    frame["housing_share"] = pd.to_numeric(
        frame["housing_expenditure_q"], errors="coerce"
    ) / total_spend.replace({0: pd.NA})
    frame["transport_share"] = pd.to_numeric(
        frame["transportation_expenditure_q"], errors="coerce"
    ) / total_spend.replace({0: pd.NA})
    frame["entertainment_share"] = pd.to_numeric(
        frame["entertainment_expenditure_q"], errors="coerce"
    ) / total_spend.replace({0: pd.NA})

    return frame


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normalize BLS Consumer Expenditure Interview PUMD ZIP files into quarterly household rows."
    )
    parser.add_argument(
        "--input-dir",
        default="data/external/bls_cex_interview_recent",
        help="Directory containing downloaded BLS interview ZIP files",
    )
    parser.add_argument(
        "--output",
        default="artifacts/normalized/bls_cex_interview_quarterly.csv",
        help="CSV output path for the normalized quarterly table",
    )
    args = parser.parse_args()

    frame = build_bls_cex_interview_frame(args.input_dir)
    if frame.empty:
        raise SystemExit("No BLS interview ZIP files found to ingest.")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)

    panel_lengths = frame.groupby("panel_id")["quarter_index"].nunique()
    summary = {
        "rows": int(len(frame)),
        "panel_count": int(frame["panel_id"].nunique()),
        "years": sorted(frame["interview_year"].dropna().astype(int).unique().tolist()),
        "panels_with_2_quarters": int((panel_lengths >= 2).sum()),
        "panels_with_3_quarters": int((panel_lengths >= 3).sum()),
        "panels_with_4_quarters": int((panel_lengths >= 4).sum()),
        "young_adult_rows": int(frame["young_adult_proxy"].sum()),
        "student_debt_rows": int(frame["student_debt_proxy"].sum()),
        "output": str(output_path),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
