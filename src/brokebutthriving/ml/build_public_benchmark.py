from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, low_memory=False)


def _coerce_bool(value: object) -> bool | None:
    if pd.isna(value):
        return None
    if isinstance(value, bool):
        return value
    cleaned = str(value).strip().lower()
    if cleaned in {"true", "1", "yes"}:
        return True
    if cleaned in {"false", "0", "no"}:
        return False
    return None


def _coerce_bool_series(series: pd.Series) -> pd.Series:
    return series.map(_coerce_bool)


def _student_status_from_fwb(frame: pd.DataFrame) -> pd.Series:
    is_full_time_student = _coerce_bool_series(frame["is_full_time_student"])
    return is_full_time_student.map(
        lambda value: "full_time_student" if value is True else None
    )


def build_master_frame(shed: pd.DataFrame, mem: pd.DataFrame, fwb: pd.DataFrame) -> pd.DataFrame:
    frames = [frame for frame in [shed, mem, fwb] if not frame.empty]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False)


def build_wellbeing_benchmark(mem: pd.DataFrame, fwb: pd.DataFrame) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []

    if not mem.empty and "fwb_score" in mem:
        mem_frame = mem.copy()
        mem_frame["target_fwb_score"] = pd.to_numeric(mem_frame["fwb_score"], errors="coerce")
        mem_frame["student_status_proxy"] = mem_frame.get("current_school_status")
        mem_frame["benchmark_source_label"] = "cfpb_mem"
        frames.append(mem_frame[mem_frame["target_fwb_score"].notna()])

    if not fwb.empty and "fwb_score" in fwb:
        fwb_frame = fwb.copy()
        fwb_frame["target_fwb_score"] = pd.to_numeric(fwb_frame["fwb_score"], errors="coerce")
        fwb_frame["student_status_proxy"] = _student_status_from_fwb(fwb_frame)
        fwb_frame["benchmark_source_label"] = "cfpb_fwb"
        frames.append(fwb_frame[fwb_frame["target_fwb_score"].notna()])

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False)


def build_hardship_benchmark(shed: pd.DataFrame, mem: pd.DataFrame) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []

    if not shed.empty and "is_financially_strained" in shed:
        shed_frame = shed.copy()
        shed_frame["target_financial_strain"] = _coerce_bool_series(
            shed_frame["is_financially_strained"]
        )
        shed_frame["student_status_proxy"] = shed_frame.get("current_student_status")
        shed_frame["benchmark_source_label"] = "fed_shed"
        frames.append(shed_frame[shed_frame["target_financial_strain"].notna()])

    if not mem.empty:
        mem_frame = mem.copy()
        hardship_columns = [
            "had_bill_difficulty_past_12m",
            "difficulty_paying_food",
            "difficulty_paying_utilities",
            "difficulty_paying_home_repair",
            "difficulty_paying_taxes_or_legal_bills",
            "difficulty_paying_mortgage_or_rent",
            "medical_collection_contact",
        ]
        available_columns = [column for column in hardship_columns if column in mem_frame.columns]
        if available_columns:
            hardship_signals = mem_frame[available_columns].apply(_coerce_bool_series)
            has_observation = hardship_signals.notna().any(axis=1)
            hardship_target = hardship_signals.eq(True).any(axis=1)
            mem_frame["target_financial_strain"] = hardship_target.where(has_observation, other=pd.NA)
            mem_frame["student_status_proxy"] = mem_frame.get("current_school_status")
            mem_frame["benchmark_source_label"] = "cfpb_mem"
            frames.append(mem_frame[mem_frame["target_financial_strain"].notna()])

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False)


def build_future_difficulty_benchmark(mem: pd.DataFrame) -> pd.DataFrame:
    if mem.empty or "expects_bill_difficulty_next_12m" not in mem:
        return pd.DataFrame()

    mem_frame = mem.copy()
    mem_frame["target_future_bill_difficulty"] = _coerce_bool_series(
        mem_frame["expects_bill_difficulty_next_12m"]
    )
    mem_frame["student_status_proxy"] = mem_frame.get("current_school_status")
    mem_frame["benchmark_source_label"] = "cfpb_mem"
    return mem_frame[mem_frame["target_future_bill_difficulty"].notna()]


def build_student_subset(
    shed: pd.DataFrame, mem: pd.DataFrame, fwb: pd.DataFrame
) -> pd.DataFrame:
    student_frames: list[pd.DataFrame] = []

    if not shed.empty and "is_current_student" in shed:
        shed_frame = shed.copy()
        shed_frame["student_status_proxy"] = shed_frame.get("current_student_status")
        student_mask = _coerce_bool_series(shed_frame["is_current_student"]).fillna(False)
        student_frames.append(shed_frame[student_mask])

    if not mem.empty and "current_school_status" in mem:
        mem_frame = mem.copy()
        mem_frame["student_status_proxy"] = mem_frame.get("current_school_status")
        student_frames.append(
            mem_frame[mem_frame["current_school_status"].isin(["full_time", "part_time"])]
        )

    if not fwb.empty and "is_full_time_student" in fwb:
        fwb_frame = fwb.copy()
        fwb_frame["student_status_proxy"] = _student_status_from_fwb(fwb_frame)
        student_mask = _coerce_bool_series(fwb_frame["is_full_time_student"]).fillna(False)
        student_frames.append(fwb_frame[student_mask])

    if not student_frames:
        return pd.DataFrame()
    return pd.concat(student_frames, ignore_index=True, sort=False)


def _write_csv(frame: pd.DataFrame, path: Path) -> int:
    if frame.empty:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return int(len(frame))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build task-specific benchmark tables from normalized public finance datasets."
    )
    parser.add_argument(
        "--normalized-dir",
        default="artifacts/normalized",
        help="Directory containing normalized dataset CSVs",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/benchmarks",
        help="Directory for benchmark CSV outputs",
    )
    args = parser.parse_args()

    normalized_dir = Path(args.normalized_dir)
    output_dir = Path(args.output_dir)

    shed = _load_csv(normalized_dir / "fed_shed_normalized.csv")
    mem = _load_csv(normalized_dir / "cfpb_mem_normalized.csv")
    fwb = _load_csv(normalized_dir / "cfpb_fwb_normalized.csv")

    master = build_master_frame(shed, mem, fwb)
    wellbeing = build_wellbeing_benchmark(mem, fwb)
    hardship = build_hardship_benchmark(shed, mem)
    future_difficulty = build_future_difficulty_benchmark(mem)
    student_subset = build_student_subset(shed, mem, fwb)

    summary = {
        "master_rows": _write_csv(master, output_dir / "public_finance_master.csv"),
        "wellbeing_rows": _write_csv(
            wellbeing, output_dir / "public_wellbeing_benchmark.csv"
        ),
        "hardship_rows": _write_csv(
            hardship, output_dir / "public_hardship_benchmark.csv"
        ),
        "future_difficulty_rows": _write_csv(
            future_difficulty, output_dir / "public_future_difficulty_benchmark.csv"
        ),
        "student_subset_rows": _write_csv(
            student_subset, output_dir / "public_student_finance_rows.csv"
        ),
        "output_dir": str(output_dir),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
