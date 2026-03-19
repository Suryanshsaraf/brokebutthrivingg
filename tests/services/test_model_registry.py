from __future__ import annotations

import json
from pathlib import Path

from brokebutthriving.services.model_registry import load_model_registry


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_load_model_registry_reads_public_and_sequence_runs(tmp_path: Path) -> None:
    public_root = tmp_path / "public-benchmark-runs"
    sequence_root = tmp_path / "sequence-runs"
    public_run = public_root / "run-001"
    sequence_run = sequence_root / "run-001"

    _write_json(
        public_run / "summary.json",
        {
            "future_difficulty_classification": {
                "task_type": "classification",
                "benchmark_file": "public_future_difficulty_benchmark.csv",
                "dataset_sources": ["cfpb_mem"],
                "note": "public note",
                "row_count": 120,
                "split_counts": {"train": 80, "val": 20, "test": 20},
                "feature_count": 15,
                "model_metrics": {
                    "logistic_regression": {"auroc": 0.81, "f1": 0.7},
                    "mlp": {"auroc": 0.84, "f1": 0.73},
                },
                "positive_class_rate": {"overall": 0.4},
            }
        },
    )
    _write_json(
        public_run / "future_difficulty_classification" / "feature_manifest.json",
        {
            "numeric_features": ["survey_year", "fwb_score"],
            "categorical_features": ["student_status_proxy"],
            "boolean_features": ["expects_bill_difficulty_next_12m"],
        },
    )
    _write_json(
        public_run / "future_difficulty_classification" / "student_subset_metrics.json",
        {
            "student_subset_test_rows": 12,
            "student_subset_group_count": 10,
            "metrics": {
                "logistic_regression": {"auroc": 0.8, "f1": 0.6},
                "mlp": {"auroc": 0.85, "f1": 0.64},
            },
        },
    )

    _write_json(
        sequence_run / "metrics.json",
        {
            "note": "sequence note",
            "row_count": 240,
            "split_counts": {"train": 160, "val": 40, "test": 40},
            "feature_count_flat": 20,
            "feature_count_sequence": 6,
            "positive_class_rate": {"overall": 0.25},
            "regression_metrics": {
                "hist_gradient_boosting": {"r2": 0.52, "mae": 3000.0},
                "lstm": {"r2": 0.55, "mae": 2900.0},
            },
            "classification_metrics": {
                "logistic_regression": {"auroc": 0.61, "f1": 0.42},
                "lstm": {"auroc": 0.64, "f1": 0.46},
            },
        },
    )
    _write_json(
        sequence_run / "feature_manifest.json",
        {
            "sequence_base_features": [
                "total_expenditure_q",
                "food_expenditure_q",
                "housing_expenditure_q",
                "after_tax_income_annual",
                "student_loan_balance",
                "family_size",
                "region_code",
            ]
        },
    )
    _write_json(
        sequence_run / "young_student_subset_metrics.json",
        {
            "young_or_student_test_rows": 18,
            "young_or_student_panel_count": 15,
            "regression_metrics": {
                "hist_gradient_boosting": {"r2": 0.5, "mae": 2800.0},
                "lstm": {"r2": 0.53, "mae": 2700.0},
            },
            "classification_metrics": {
                "logistic_regression": {"auroc": 0.62, "f1": 0.4},
                "lstm": {"auroc": 0.66, "f1": 0.48},
            },
        },
    )

    registry = load_model_registry(public_runs_root=public_root, sequence_runs_root=sequence_root)

    assert registry.public_benchmark_run_id == "run-001"
    assert registry.sequence_run_id == "run-001"
    assert registry.total_trained_tasks == 3
    assert registry.available_families == ["public_benchmark", "spend_sequence"]

    future_task = next(task for task in registry.tasks if task.task_id == "future_difficulty_classification")
    assert future_task.best_model == "Tabular MLP"
    assert future_task.subgroup_evaluation is not None
    assert future_task.feature_groups[0].name == "Numeric inputs"

    spend_task = next(task for task in registry.tasks if task.task_id == "bls_next_quarter_spend_regression")
    assert spend_task.best_model == "Sequence LSTM"
    assert spend_task.auxiliary_feature_count == 20
    assert spend_task.subgroup_evaluation is not None


def test_load_model_registry_reports_missing_artifacts(tmp_path: Path) -> None:
    registry = load_model_registry(
        public_runs_root=tmp_path / "missing-public",
        sequence_runs_root=tmp_path / "missing-sequence",
    )

    assert registry.total_trained_tasks == 0
    assert len(registry.missing_artifacts) == 2
