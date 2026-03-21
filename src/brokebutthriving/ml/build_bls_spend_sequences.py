from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from brokebutthriving.ml.bls_cex import BLS_SEQUENCE_BASE_FEATURES


HIGH_BURN_MULTIPLIER = 1.15


def build_bls_spend_sequence_benchmark(
    input_csv: str | Path,
    seq_len: int = 2,
    high_burn_multiplier: float = HIGH_BURN_MULTIPLIER,
) -> pd.DataFrame:
    frame = pd.read_csv(input_csv, low_memory=False)
    if frame.empty:
        return pd.DataFrame()

    for feature in BLS_SEQUENCE_BASE_FEATURES:
        if feature not in frame.columns:
            frame[feature] = pd.NA

    numeric_features = [
        feature
        for feature in BLS_SEQUENCE_BASE_FEATURES
        if feature not in {"urban_flag", "housing_tenure_code", "region_code", "education_ref_code", "highest_education_code", "income_class_code"}
        and not feature.endswith("_proxy")
    ]
    frame[numeric_features] = frame[numeric_features].apply(pd.to_numeric, errors="coerce")

    records: list[dict[str, object]] = []
    required_window = seq_len + 1

    for panel_id, group in frame.groupby("panel_id"):
        ordered = group.sort_values("quarter_index").reset_index(drop=True)
        if len(ordered) < required_window:
            continue

        for start_idx in range(0, len(ordered) - required_window + 1):
            window = ordered.iloc[start_idx : start_idx + required_window].copy()
            quarter_gaps = window["quarter_index"].diff().dropna()
            if not (quarter_gaps == 1).all():
                continue

            history = window.iloc[:-1]
            target = window.iloc[-1]
            history_total_mean = pd.to_numeric(history["total_expenditure_q"], errors="coerce").mean()
            target_total = pd.to_numeric(target["total_expenditure_q"], errors="coerce")
            if pd.isna(history_total_mean) or pd.isna(target_total):
                continue

            record: dict[str, object] = {
                "source_dataset": "bls_cex_interview",
                "panel_id": str(panel_id),
                "seq_len": seq_len,
                "history_start_quarter_label": history.iloc[0]["quarter_label"],
                "target_quarter_label": target["quarter_label"],
                "target_quarter_index": int(target["quarter_index"]),
                "target_sample_weight": float(target["sample_weight"]) if pd.notna(target["sample_weight"]) else None,
                "young_adult_proxy": int(target["young_adult_proxy"]),
                "student_debt_proxy": int(target["student_debt_proxy"]),
                "young_or_student_proxy": int(
                    bool(target["young_adult_proxy"]) or bool(target["student_debt_proxy"])
                ),
                "target_next_total_expenditure_q": float(target_total),
                "target_high_burn_next_q": int(target_total > history_total_mean * high_burn_multiplier),
            }

            for lag_idx, (_, lag_row) in enumerate(history.iterrows(), start=1):
                prefix = f"lag{seq_len - lag_idx + 1}"
                record[f"{prefix}_quarter_label"] = lag_row["quarter_label"]
                for feature in BLS_SEQUENCE_BASE_FEATURES:
                    record[f"{prefix}_{feature}"] = lag_row.get(feature)

            records.append(record)

    return pd.DataFrame.from_records(records)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a consecutive-quarter BLS spend-sequence benchmark from normalized interview data."
    )
    parser.add_argument(
        "--input-csv",
        default="artifacts/normalized/bls_cex_interview_quarterly.csv",
        help="Path to the normalized BLS interview quarterly CSV",
    )
    parser.add_argument(
        "--output",
        default="artifacts/benchmarks/bls_cex_spend_sequence_benchmark.csv",
        help="Output CSV path for the flattened sequence benchmark",
    )
    parser.add_argument("--seq-len", type=int, default=2)
    parser.add_argument("--high-burn-multiplier", type=float, default=HIGH_BURN_MULTIPLIER)
    args = parser.parse_args()

    frame = build_bls_spend_sequence_benchmark(
        input_csv=args.input_csv,
        seq_len=args.seq_len,
        high_burn_multiplier=args.high_burn_multiplier,
    )
    if frame.empty:
        raise SystemExit("No valid BLS sequence samples could be created.")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)

    summary = {
        "rows": int(len(frame)),
        "panel_count": int(frame["panel_id"].nunique()),
        "seq_len": int(args.seq_len),
        "positive_rate": float(frame["target_high_burn_next_q"].mean()),
        "young_or_student_rows": int(frame["young_or_student_proxy"].sum()),
        "output": str(output_path),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
