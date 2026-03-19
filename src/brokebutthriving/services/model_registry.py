from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from brokebutthriving.core.config import settings
from brokebutthriving.schemas.api import (
    ModelFeatureGroup,
    ModelMetricSummary,
    ModelRegistrySummary,
    SubgroupEvaluationSummary,
    TrainedModelTask,
)


_PRIMARY_METRICS = {
    "classification": "auroc",
    "regression": "r2",
}

_TASK_TITLES = {
    "future_difficulty_classification": "Future Bill Difficulty",
    "hardship_classification": "Financial Hardship Detection",
    "wellbeing_regression": "Financial Well-Being Regression",
    "bls_next_quarter_spend_regression": "Next-Quarter Spend Forecast",
    "bls_high_burn_classification": "Next-Quarter High-Burn Risk",
}

_MODEL_LABELS = {
    "logistic_regression": "Logistic Regression",
    "hist_gradient_boosting": "HistGradientBoosting",
    "ridge": "Ridge Regression",
    "mlp": "Tabular MLP",
    "lstm": "Sequence LSTM",
}

_FEATURE_GROUP_LIMIT = 8


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _latest_run_directory(root: Path) -> Path | None:
    if not root.exists():
        return None

    directories = [path for path in root.iterdir() if path.is_dir()]
    if not directories:
        return None

    return sorted(directories, key=lambda item: (item.name, item.stat().st_mtime_ns))[-1]


def _title_for(task_id: str) -> str:
    return _TASK_TITLES.get(task_id, task_id.replace("_", " ").title())


def _metric_label(metric_name: str) -> str:
    labels = {
        "auroc": "AUROC",
        "f1": "F1",
        "precision": "Precision",
        "recall": "Recall",
        "accuracy": "Accuracy",
        "brier_score": "Brier score",
        "mae": "MAE",
        "rmse": "RMSE",
        "r2": "R²",
    }
    return labels.get(metric_name, metric_name.replace("_", " "))


def _build_metric_summaries(task_type: str, metrics: dict[str, dict[str, float]]) -> tuple[list[ModelMetricSummary], str, float]:
    primary_metric = _PRIMARY_METRICS.get(task_type, "auroc")
    best_model_id = max(metrics, key=lambda model_id: metrics[model_id].get(primary_metric, float("-inf")))
    summaries: list[ModelMetricSummary] = []
    for model_id, values in metrics.items():
        summaries.append(
            ModelMetricSummary(
                model_id=model_id,
                model_label=_MODEL_LABELS.get(model_id, model_id.replace("_", " ").title()),
                primary_metric_name=primary_metric,
                primary_metric_value=float(values.get(primary_metric, 0.0)),
                metrics={metric: float(value) for metric, value in values.items()},
                is_best=model_id == best_model_id,
            )
        )
    summaries.sort(key=lambda item: item.primary_metric_value, reverse=True)
    best = next(item for item in summaries if item.is_best)
    return summaries, best.model_label, best.primary_metric_value


def _preview(values: list[str], limit: int = _FEATURE_GROUP_LIMIT) -> list[str]:
    return [str(value) for value in values[:limit]]


def _feature_summary(groups: list[ModelFeatureGroup]) -> str:
    if not groups:
        return "Feature manifest unavailable."

    active_groups = [group for group in groups if group.features]
    if not active_groups:
        return "Feature manifest unavailable."

    group_labels = ", ".join(group.name.lower() for group in active_groups[:3])
    return f"Main inputs span {group_labels}."


def _parse_public_feature_groups(manifest: dict[str, Any]) -> list[ModelFeatureGroup]:
    return [
        ModelFeatureGroup(name="Numeric inputs", features=_preview(manifest.get("numeric_features", []))),
        ModelFeatureGroup(name="Categorical inputs", features=_preview(manifest.get("categorical_features", []))),
        ModelFeatureGroup(name="Boolean inputs", features=_preview(manifest.get("boolean_features", []))),
    ]


def _sequence_feature_groups(manifest: dict[str, Any]) -> list[ModelFeatureGroup]:
    base_features = [str(item) for item in manifest.get("sequence_base_features", [])]
    spend_inputs = [
        feature
        for feature in base_features
        if "expenditure" in feature or "spend" in feature or feature.endswith("_share")
    ]
    finance_inputs = [
        feature
        for feature in base_features
        if any(token in feature for token in ("income", "assets", "credit", "loan", "balance"))
    ]
    context_inputs = [
        feature
        for feature in base_features
        if feature not in spend_inputs and feature not in finance_inputs
    ]
    return [
        ModelFeatureGroup(name="Spend sequence inputs", features=_preview(spend_inputs)),
        ModelFeatureGroup(name="Financial context", features=_preview(finance_inputs)),
        ModelFeatureGroup(name="Household and demographic context", features=_preview(context_inputs)),
    ]


def _public_subgroup_summary(path: Path, task_type: str) -> SubgroupEvaluationSummary | None:
    if not path.exists():
        return None

    payload = _load_json(path)
    metrics = payload.get("metrics", {})
    if not metrics:
        return None

    summaries, best_model, best_value = _build_metric_summaries(task_type, metrics)
    return SubgroupEvaluationSummary(
        label="Student-coded subset",
        row_count=int(payload.get("student_subset_test_rows", 0)),
        group_count=int(payload.get("student_subset_group_count", 0)),
        best_model=best_model,
        primary_metric_name=summaries[0].primary_metric_name if summaries else None,
        primary_metric_value=best_value,
    )


def _sequence_subgroup_summary(path: Path, task_type: str) -> SubgroupEvaluationSummary | None:
    if not path.exists():
        return None

    payload = _load_json(path)
    metrics_key = "classification_metrics" if task_type == "classification" else "regression_metrics"
    metrics = payload.get(metrics_key, {})
    if not metrics:
        return None

    summaries, best_model, best_value = _build_metric_summaries(task_type, metrics)
    return SubgroupEvaluationSummary(
        label="Young-adult / student proxy subset",
        row_count=int(payload.get("young_or_student_test_rows", 0)),
        group_count=int(payload.get("young_or_student_panel_count", 0)),
        best_model=best_model,
        primary_metric_name=summaries[0].primary_metric_name if summaries else None,
        primary_metric_value=best_value,
    )


def _build_public_tasks(run_dir: Path) -> list[TrainedModelTask]:
    summary_path = run_dir / "summary.json"
    if not summary_path.exists():
        return []

    summary = _load_json(summary_path)
    tasks: list[TrainedModelTask] = []

    for task_id, payload in summary.items():
        task_dir = run_dir / task_id
        manifest = _load_json(task_dir / "feature_manifest.json") if (task_dir / "feature_manifest.json").exists() else {}
        metric_summaries, best_model, best_value = _build_metric_summaries(
            payload["task_type"],
            payload["model_metrics"],
        )
        primary_metric_name = metric_summaries[0].primary_metric_name
        feature_groups = _parse_public_feature_groups(manifest)
        subgroup = _public_subgroup_summary(task_dir / "student_subset_metrics.json", payload["task_type"])

        highlight = (
            f"{best_model} leads this benchmark with {_metric_label(primary_metric_name)} "
            f"{best_value:.3f} on {int(payload['row_count']):,} public survey rows."
        )

        tasks.append(
            TrainedModelTask(
                task_id=task_id,
                title=_title_for(task_id),
                family="public_benchmark",
                task_type=payload["task_type"],
                benchmark_file=payload.get("benchmark_file"),
                run_id=run_dir.name,
                note=str(payload.get("note", "")),
                dataset_sources=[str(source) for source in payload.get("dataset_sources", [])],
                row_count=int(payload["row_count"]),
                split_counts={key: int(value) for key, value in payload["split_counts"].items()},
                feature_count=int(payload["feature_count"]),
                positive_class_rate=(
                    float(payload["positive_class_rate"]["overall"])
                    if payload["task_type"] == "classification"
                    else None
                ),
                best_model=best_model,
                primary_metric_name=primary_metric_name,
                primary_metric_value=best_value,
                highlight=highlight,
                feature_summary=_feature_summary(feature_groups),
                feature_groups=feature_groups,
                metrics=metric_summaries,
                subgroup_evaluation=subgroup,
            )
        )

    return tasks


def _build_sequence_tasks(run_dir: Path) -> list[TrainedModelTask]:
    metrics_path = run_dir / "metrics.json"
    if not metrics_path.exists():
        return []

    payload = _load_json(metrics_path)
    manifest = _load_json(run_dir / "feature_manifest.json") if (run_dir / "feature_manifest.json").exists() else {}
    feature_groups = _sequence_feature_groups(manifest)
    subgroup_path = run_dir / "young_student_subset_metrics.json"

    tasks: list[TrainedModelTask] = []
    sequence_specs = [
        ("bls_next_quarter_spend_regression", "regression", payload["regression_metrics"]),
        ("bls_high_burn_classification", "classification", payload["classification_metrics"]),
    ]

    for task_id, task_type, task_metrics in sequence_specs:
        metric_summaries, best_model, best_value = _build_metric_summaries(task_type, task_metrics)
        primary_metric_name = metric_summaries[0].primary_metric_name
        subgroup = _sequence_subgroup_summary(subgroup_path, task_type)
        highlight = (
            f"{best_model} is currently strongest on this BLS sequence task with "
            f"{_metric_label(primary_metric_name)} {best_value:.3f} across {int(payload['row_count']):,} panel rows."
        )

        tasks.append(
            TrainedModelTask(
                task_id=task_id,
                title=_title_for(task_id),
                family="spend_sequence",
                task_type=task_type,
                benchmark_file="bls_cex_spend_sequence_benchmark.csv",
                run_id=run_dir.name,
                note=str(payload.get("note", "")),
                dataset_sources=["bls_cex_interview"],
                row_count=int(payload["row_count"]),
                split_counts={key: int(value) for key, value in payload["split_counts"].items()},
                feature_count=int(payload["feature_count_sequence"]),
                auxiliary_feature_count=int(payload["feature_count_flat"]),
                auxiliary_feature_label="Flat baseline features",
                positive_class_rate=(
                    float(payload["positive_class_rate"]["overall"]) if task_type == "classification" else None
                ),
                best_model=best_model,
                primary_metric_name=primary_metric_name,
                primary_metric_value=best_value,
                highlight=highlight,
                feature_summary=_feature_summary(feature_groups),
                feature_groups=feature_groups,
                metrics=metric_summaries,
                subgroup_evaluation=subgroup,
            )
        )

    return tasks


def load_model_registry(
    public_runs_root: Path | None = None,
    sequence_runs_root: Path | None = None,
) -> ModelRegistrySummary:
    public_root = public_runs_root or settings.public_benchmark_runs_root
    sequence_root = sequence_runs_root or settings.sequence_runs_root

    tasks: list[TrainedModelTask] = []
    missing_artifacts: list[str] = []

    public_run = _latest_run_directory(public_root)
    if public_run is None:
        missing_artifacts.append(f"No public benchmark runs found under {public_root}.")
    else:
        tasks.extend(_build_public_tasks(public_run))

    sequence_run = _latest_run_directory(sequence_root)
    if sequence_run is None:
        missing_artifacts.append(f"No sequence runs found under {sequence_root}.")
    else:
        tasks.extend(_build_sequence_tasks(sequence_run))

    tasks.sort(key=lambda item: (item.family, item.title))
    available_families = sorted({task.family for task in tasks})

    return ModelRegistrySummary(
        public_benchmark_run_id=public_run.name if public_run else None,
        sequence_run_id=sequence_run.name if sequence_run else None,
        total_trained_tasks=len(tasks),
        available_families=available_families,
        note=(
            "These cards summarize real offline benchmark runs from public U.S. finance datasets. "
            "They are honest benchmark evaluations, not live personalized scores for the student app workspace."
        ),
        missing_artifacts=missing_artifacts,
        tasks=tasks,
    )
