from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pandas as pd

from brokebutthriving.ml.train_public_benchmarks import (
    TASKS,
    BenchmarkPreprocessor,
    infer_feature_types,
    main,
    make_group_splits,
    prepare_task_frame,
)


def _build_wellbeing_frame() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for respondent in range(56):
        is_student = respondent % 3 != 2
        for wave in range(2):
            target = 42.0 + respondent * 0.6 + wave
            rows.append(
                {
                    "source_dataset": "cfpb_mem" if respondent % 2 == 0 else "cfpb_fwb",
                    "respondent_id": f"wb-{respondent}",
                    "survey_year": 2020 + (wave % 2),
                    "sample_id": 1 + (respondent % 3),
                    "wave_id": f"w{wave + 1}",
                    "student_status_proxy": "full_time_student" if is_student else "not_attending",
                    "checking_savings_balance_band": "101_to_500" if respondent % 2 == 0 else "5001_to_10000",
                    "has_checking_or_savings_account": "true" if respondent % 2 == 0 else "false",
                    "money_management_score": 1 + (respondent % 4),
                    "household_income_code": 1 + (respondent % 5),
                    "sample_weight": 0.5 + respondent / 100.0,
                    "benchmark_source_label": "cfpb_mem" if respondent % 2 == 0 else "cfpb_fwb",
                    "fwb_score": target,
                    "target_fwb_score": target,
                }
            )
    return pd.DataFrame(rows)


def _build_hardship_frame() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for respondent in range(54):
        target = respondent % 2 == 0
        for wave in range(2):
            rows.append(
                {
                    "source_dataset": "fed_shed" if respondent % 2 == 0 else "cfpb_mem",
                    "respondent_id": f"hs-{respondent}",
                    "survey_year": 2019 + wave,
                    "sample_id": 3 + (respondent % 2),
                    "wave_id": f"w{wave + 1}",
                    "student_status_proxy": "part_time_student" if respondent % 4 < 2 else "not_attending",
                    "financial_management_status": "finding_it_difficult" if target else "doing_okay",
                    "housing_status_code": 1 + (respondent % 3),
                    "checking_savings_balance_band": "lt_100" if target else "1001_to_5000",
                    "has_student_loan_debt": "yes" if respondent % 3 == 0 else "no",
                    "sample_weight": 1.0 + respondent / 200.0,
                    "benchmark_source_label": "fed_shed" if respondent % 2 == 0 else "cfpb_mem",
                    "is_financially_strained": target,
                    "had_bill_difficulty_past_12m": target,
                    "difficulty_paying_food": target,
                    "difficulty_paying_utilities": target,
                    "difficulty_paying_home_repair": target,
                    "difficulty_paying_taxes_or_legal_bills": target,
                    "difficulty_paying_mortgage_or_rent": target,
                    "medical_collection_contact": target,
                    "has_hardship_signal": target,
                    "target_financial_strain": target,
                }
            )
    return pd.DataFrame(rows)


def _build_future_difficulty_frame() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for respondent in range(60):
        target = respondent % 2 == 1
        for wave in range(2):
            rows.append(
                {
                    "source_dataset": "cfpb_mem",
                    "respondent_id": f"fd-{respondent}",
                    "survey_year": 2023 + wave,
                    "sample_id": 4,
                    "wave_id": f"w{wave + 1}",
                    "student_status_proxy": "full_time" if respondent % 3 == 0 else "part_time",
                    "checking_savings_balance_band": "lt_100" if target else "1001_to_5000",
                    "expense_coverage_horizon_band": "lt_2_weeks" if target else "3_to_6_months",
                    "has_credit_card": "1" if respondent % 2 == 0 else "0",
                    "medical_collection_count_band": "1_bill" if target else "2_to_4_bills",
                    "sample_weight": 0.8 + respondent / 150.0,
                    "benchmark_source_label": "cfpb_mem",
                    "expects_bill_difficulty_next_12m": target,
                    "target_future_bill_difficulty": target,
                }
            )
    return pd.DataFrame(rows)


def _write_benchmarks(benchmark_dir: Path) -> None:
    benchmark_dir.mkdir(parents=True, exist_ok=True)
    _build_wellbeing_frame().to_csv(
        benchmark_dir / TASKS["wellbeing_regression"].benchmark_filename, index=False
    )
    _build_hardship_frame().to_csv(
        benchmark_dir / TASKS["hardship_classification"].benchmark_filename, index=False
    )
    _build_future_difficulty_frame().to_csv(
        benchmark_dir / TASKS["future_difficulty_classification"].benchmark_filename, index=False
    )


def test_prepare_task_frame_drops_missing_targets_and_coerces_boolean_values() -> None:
    frame = pd.DataFrame(
        {
            "source_dataset": ["cfpb_mem", "cfpb_mem", "cfpb_mem"],
            "respondent_id": ["a", "b", "c"],
            "student_status_proxy": ["full_time", "not_attending", "part_time"],
            "target_future_bill_difficulty": ["true", "false", None],
            "expects_bill_difficulty_next_12m": ["true", "false", "true"],
        }
    )

    task = replace(TASKS["future_difficulty_classification"], minimum_rows=1)
    prepared = prepare_task_frame(task, frame)

    assert len(prepared) == 2
    assert prepared["__target__"].tolist() == [1.0, 0.0]
    assert prepared["group_key"].tolist() == ["cfpb_mem::a", "cfpb_mem::b"]


def test_infer_feature_types_preserves_band_columns_and_boolean_flags() -> None:
    frame = pd.DataFrame(
        {
            "checking_savings_balance_band": ["lt_100", "1001_to_5000", None],
            "has_credit_card": ["1", "0", None],
            "survey_year": [2024, 2025, 2025],
            "spend_amount": [10.5, 20.0, 30.5],
            "student_status_proxy": ["full_time", "part_time", "not_attending"],
        }
    )

    numeric_features, boolean_features, categorical_features = infer_feature_types(
        frame,
        list(frame.columns),
    )
    preprocessor = BenchmarkPreprocessor(numeric_features, boolean_features, categorical_features)
    transformed = preprocessor.fit_transform(frame)

    assert "has_credit_card" in boolean_features
    assert "checking_savings_balance_band" in categorical_features
    assert "survey_year" in numeric_features
    assert transformed.shape[0] == len(frame)


def test_make_group_splits_are_group_safe_and_reasonably_sized() -> None:
    frame = _build_hardship_frame()
    prepared = prepare_task_frame(TASKS["hardship_classification"], frame)
    split = make_group_splits(
        prepared,
        task=TASKS["hardship_classification"],
        seed=7,
        student_subset_eval=True,
    )

    train_groups = set(prepared.iloc[split.train_indices]["group_key"])
    val_groups = set(prepared.iloc[split.val_indices]["group_key"])
    test_groups = set(prepared.iloc[split.test_indices]["group_key"])

    assert train_groups.isdisjoint(val_groups)
    assert train_groups.isdisjoint(test_groups)
    assert val_groups.isdisjoint(test_groups)

    total_rows = len(prepared)
    assert abs(len(split.train_indices) / total_rows - 0.70) < 0.20
    assert abs(len(split.val_indices) / total_rows - 0.15) < 0.12
    assert abs(len(split.test_indices) / total_rows - 0.15) < 0.12


def test_cli_trains_all_public_benchmark_tasks_and_writes_artifacts(tmp_path: Path) -> None:
    benchmark_dir = tmp_path / "benchmarks"
    output_dir = tmp_path / "outputs"
    _write_benchmarks(benchmark_dir)

    main(
        [
            "--benchmark-dir",
            str(benchmark_dir),
            "--output-dir",
            str(output_dir),
            "--seed",
            "11",
        ]
    )

    for task_id in TASKS:
        task_dir = output_dir / task_id
        assert (task_dir / "metrics.json").exists()
        assert (task_dir / "comparison.csv").exists()
        assert (task_dir / "predictions_test.csv").exists()
        assert (task_dir / "feature_manifest.json").exists()
        assert (task_dir / "split_manifest.json").exists()
        assert (task_dir / "student_subset_metrics.json").exists()
        assert (task_dir / "models" / "mlp_model.pt").exists()

        with (task_dir / "metrics.json").open("r", encoding="utf-8") as handle:
            metrics = json.load(handle)
        assert metrics["feature_count"] > 0
        assert metrics["row_count"] > 0
        assert metrics["note"]

    with (output_dir / "summary.json").open("r", encoding="utf-8") as handle:
        summary = json.load(handle)
    assert sorted(summary) == sorted(TASKS)
