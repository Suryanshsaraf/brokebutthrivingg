from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
import torch
from joblib import dump
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from brokebutthriving.ml.models import TabularMLP


TASK_NOTE = "Benchmark trained on public U.S. finance survey data, not college-specific proprietary logs."
STUDENT_MARKERS = {"full_time", "part_time", "full_time_student", "part_time_student"}
WEIGHT_COLUMNS = {"sample_weight", "population_weight", "panel_weight", "panel_population_weight"}
DEFAULT_SEED = 7
DEFAULT_BATCH_SIZE = 512
DEFAULT_MAX_EPOCHS = 20
DEFAULT_PATIENCE = 4
DEFAULT_ATTEMPTS = 50


@dataclass(frozen=True)
class TaskConfig:
    task_id: str
    task_type: Literal["classification", "regression"]
    benchmark_filename: str
    target_column: str
    leakage_columns: tuple[str, ...]
    minimum_rows: int = 100


@dataclass(frozen=True)
class TrainingConfig:
    batch_size: int = DEFAULT_BATCH_SIZE
    max_epochs: int = DEFAULT_MAX_EPOCHS
    patience: int = DEFAULT_PATIENCE


@dataclass
class SplitResult:
    train_indices: np.ndarray
    val_indices: np.ndarray
    test_indices: np.ndarray
    effective_seed: int


TASKS: dict[str, TaskConfig] = {
    "wellbeing_regression": TaskConfig(
        task_id="wellbeing_regression",
        task_type="regression",
        benchmark_filename="public_wellbeing_benchmark.csv",
        target_column="target_fwb_score",
        leakage_columns=("fwb_score",),
    ),
    "hardship_classification": TaskConfig(
        task_id="hardship_classification",
        task_type="classification",
        benchmark_filename="public_hardship_benchmark.csv",
        target_column="target_financial_strain",
        leakage_columns=(
            "is_financially_strained",
            "had_bill_difficulty_past_12m",
            "difficulty_paying_food",
            "difficulty_paying_utilities",
            "difficulty_paying_home_repair",
            "difficulty_paying_taxes_or_legal_bills",
            "difficulty_paying_mortgage_or_rent",
            "medical_collection_contact",
            "has_hardship_signal",
        ),
    ),
    "future_difficulty_classification": TaskConfig(
        task_id="future_difficulty_classification",
        task_type="classification",
        benchmark_filename="public_future_difficulty_benchmark.csv",
        target_column="target_future_bill_difficulty",
        leakage_columns=("expects_bill_difficulty_next_12m",),
    ),
}


def _set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _json_default(value: object) -> object:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(f"Object of type {type(value)!r} is not JSON serializable")


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, default=_json_default)


def _load_benchmark_frame(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Benchmark file not found: {path}")
    return pd.read_csv(path, low_memory=False)


def _coerce_bool(value: object) -> float | None:
    if pd.isna(value):
        return None
    if isinstance(value, bool):
        return float(value)

    cleaned = str(value).strip().lower()
    if cleaned in {"1", "true", "yes", "y", "t"}:
        return 1.0
    if cleaned in {"0", "false", "no", "n", "f"}:
        return 0.0
    return None


def _coerce_bool_series(series: pd.Series) -> pd.Series:
    return series.map(_coerce_bool)


def _is_bool_like(series: pd.Series) -> bool:
    non_null = series.dropna()
    if non_null.empty:
        return False
    coerced = non_null.map(_coerce_bool)
    return bool(coerced.notna().all())


def _is_student_status(value: object) -> bool:
    if pd.isna(value):
        return False
    cleaned = str(value).strip().lower()
    return cleaned in STUDENT_MARKERS


def _coerce_target(frame: pd.DataFrame, task: TaskConfig) -> pd.Series:
    raw_target = frame[task.target_column]
    if task.task_type == "classification":
        return _coerce_bool_series(raw_target)
    return pd.to_numeric(raw_target, errors="coerce")


def _build_group_key(frame: pd.DataFrame) -> pd.Series:
    if "source_dataset" not in frame or "respondent_id" not in frame:
        raise ValueError("Benchmark frame must include source_dataset and respondent_id columns.")
    group_source = frame["source_dataset"].fillna("missing_source").astype(str)
    group_id = frame["respondent_id"].fillna("missing_id").astype(str)
    return group_source + "::" + group_id


def prepare_task_frame(task: TaskConfig, frame: pd.DataFrame) -> pd.DataFrame:
    if task.target_column not in frame:
        raise ValueError(f"{task.target_column} is missing from benchmark frame for {task.task_id}.")

    prepared = frame.copy()
    prepared["__target__"] = _coerce_target(prepared, task)
    prepared = prepared[prepared["__target__"].notna()].reset_index(drop=True)
    prepared["group_key"] = _build_group_key(prepared)

    if len(prepared) < task.minimum_rows:
        raise ValueError(
            f"{task.task_id} has only {len(prepared)} usable rows; expected at least {task.minimum_rows}."
        )

    if task.task_type == "classification":
        unique_classes = sorted(prepared["__target__"].dropna().unique().tolist())
        if len(unique_classes) < 2:
            raise ValueError(f"{task.task_id} has only one target class after filtering.")

    return prepared


def infer_feature_types(
    train_frame: pd.DataFrame, candidate_columns: list[str]
) -> tuple[list[str], list[str], list[str]]:
    numeric_features: list[str] = []
    boolean_features: list[str] = []
    categorical_features: list[str] = []

    categorical_markers = ("_code", "_band", "_status")
    categorical_columns = {"source_dataset", "sample_id", "wave_id", "student_status_proxy"}

    for column in candidate_columns:
        series = train_frame[column]
        if _is_bool_like(series):
            boolean_features.append(column)
            continue

        if column in categorical_columns or any(marker in column for marker in categorical_markers):
            categorical_features.append(column)
            continue

        if pd.api.types.is_numeric_dtype(series):
            numeric_features.append(column)
            continue

        numeric_attempt = pd.to_numeric(series, errors="coerce")
        if numeric_attempt.notna().mean() >= 0.95:
            numeric_features.append(column)
            continue

        categorical_features.append(column)

    return numeric_features, boolean_features, categorical_features


class BenchmarkPreprocessor:
    def __init__(
        self,
        numeric_features: list[str],
        boolean_features: list[str],
        categorical_features: list[str],
    ) -> None:
        self.numeric_features = numeric_features
        self.boolean_features = boolean_features
        self.categorical_features = categorical_features
        self.numeric_imputer = SimpleImputer(strategy="median") if numeric_features else None
        self.numeric_scaler = StandardScaler() if numeric_features else None
        self.boolean_imputer = (
            SimpleImputer(strategy="most_frequent", add_indicator=True) if boolean_features else None
        )
        self.categorical_imputer = (
            SimpleImputer(strategy="constant", fill_value="__missing__")
            if categorical_features
            else None
        )
        self.categorical_encoder = (
            OneHotEncoder(handle_unknown="ignore", sparse_output=False)
            if categorical_features
            else None
        )
        self._feature_names: list[str] = []
        self.active_numeric_features = list(numeric_features)
        self.active_boolean_features = list(boolean_features)
        self.dropped_all_missing_features: list[str] = []

    def _numeric_frame(self, frame: pd.DataFrame) -> np.ndarray:
        numeric_frame = frame[self.active_numeric_features].apply(pd.to_numeric, errors="coerce")
        return numeric_frame.to_numpy(dtype=np.float32)

    def _boolean_frame(self, frame: pd.DataFrame) -> np.ndarray:
        boolean_frame = frame[self.active_boolean_features].apply(_coerce_bool_series)
        return boolean_frame.to_numpy(dtype=np.float32)

    def _categorical_frame(self, frame: pd.DataFrame) -> np.ndarray:
        categorical_frame = frame[self.categorical_features].astype("object").where(
            frame[self.categorical_features].notna(), None
        )
        return categorical_frame.to_numpy(dtype=object)

    def fit(self, frame: pd.DataFrame) -> "BenchmarkPreprocessor":
        feature_names: list[str] = []

        if self.numeric_features:
            numeric_frame = frame[self.numeric_features].apply(pd.to_numeric, errors="coerce")
            self.active_numeric_features = [
                column for column in self.numeric_features if numeric_frame[column].notna().any()
            ]
            self.dropped_all_missing_features.extend(
                [column for column in self.numeric_features if column not in self.active_numeric_features]
            )
            if self.active_numeric_features:
                numeric_values = self._numeric_frame(frame)
                imputed_numeric = self.numeric_imputer.fit_transform(numeric_values)
                self.numeric_scaler.fit(imputed_numeric)
                feature_names.extend(self.active_numeric_features)

        if self.boolean_features:
            boolean_frame = frame[self.boolean_features].apply(_coerce_bool_series)
            self.active_boolean_features = [
                column for column in self.boolean_features if boolean_frame[column].notna().any()
            ]
            self.dropped_all_missing_features.extend(
                [column for column in self.boolean_features if column not in self.active_boolean_features]
            )
            if self.active_boolean_features:
                boolean_values = self._boolean_frame(frame)
                self.boolean_imputer.fit(boolean_values)
                feature_names.extend(self.active_boolean_features)
                indicator = self.boolean_imputer.indicator_
                if indicator is not None:
                    missing_columns = [
                        self.active_boolean_features[index] for index in indicator.features_
                    ]
                    feature_names.extend([f"{column}__missing" for column in missing_columns])

        if self.categorical_features:
            categorical_values = self._categorical_frame(frame)
            imputed_categorical = self.categorical_imputer.fit_transform(categorical_values)
            self.categorical_encoder.fit(imputed_categorical)
            feature_names.extend(
                self.categorical_encoder.get_feature_names_out(self.categorical_features).tolist()
            )

        self._feature_names = feature_names
        return self

    def transform(self, frame: pd.DataFrame) -> np.ndarray:
        matrices: list[np.ndarray] = []

        if self.numeric_features:
            if self.active_numeric_features:
                numeric_values = self._numeric_frame(frame)
                imputed_numeric = self.numeric_imputer.transform(numeric_values)
                matrices.append(self.numeric_scaler.transform(imputed_numeric).astype(np.float32))

        if self.boolean_features:
            if self.active_boolean_features:
                boolean_values = self._boolean_frame(frame)
                imputed_boolean = self.boolean_imputer.transform(boolean_values)
                matrices.append(imputed_boolean.astype(np.float32))

        if self.categorical_features:
            categorical_values = self._categorical_frame(frame)
            imputed_categorical = self.categorical_imputer.transform(categorical_values)
            matrices.append(self.categorical_encoder.transform(imputed_categorical).astype(np.float32))

        if not matrices:
            raise ValueError("No feature columns available after preprocessing.")

        return np.hstack(matrices).astype(np.float32)

    def fit_transform(self, frame: pd.DataFrame) -> np.ndarray:
        self.fit(frame)
        return self.transform(frame)

    def get_feature_names_out(self) -> list[str]:
        return list(self._feature_names)


def build_feature_manifest(task: TaskConfig, frame: pd.DataFrame) -> dict[str, object]:
    excluded_columns = {
        "respondent_id",
        "group_key",
        task.target_column,
        "__target__",
        *WEIGHT_COLUMNS,
        *task.leakage_columns,
    }
    excluded_columns.update(column for column in frame.columns if column.startswith("target_"))

    candidate_columns = [
        column for column in frame.columns if column not in excluded_columns and column != "benchmark_source_label"
    ]
    numeric_features, boolean_features, categorical_features = infer_feature_types(frame, candidate_columns)

    return {
        "candidate_columns": candidate_columns,
        "numeric_features": numeric_features,
        "boolean_features": boolean_features,
        "categorical_features": categorical_features,
        "dropped_columns": sorted(set(frame.columns) - set(candidate_columns)),
    }


def make_group_splits(
    frame: pd.DataFrame,
    task: TaskConfig,
    seed: int,
    student_subset_eval: bool,
    max_attempts: int = DEFAULT_ATTEMPTS,
) -> SplitResult:
    groups = frame["group_key"].to_numpy()
    indices = np.arange(len(frame))
    targets = frame["__target__"].to_numpy()
    student_mask = frame["student_status_proxy"].map(_is_student_status).to_numpy()

    for attempt in range(max_attempts):
        effective_seed = seed + attempt
        outer = GroupShuffleSplit(n_splits=1, test_size=0.30, random_state=effective_seed)
        train_indices, temp_indices = next(outer.split(indices, groups=groups))

        inner = GroupShuffleSplit(n_splits=1, test_size=0.50, random_state=effective_seed)
        val_relative, test_relative = next(inner.split(temp_indices, groups=groups[temp_indices]))
        val_indices = temp_indices[val_relative]
        test_indices = temp_indices[test_relative]

        if min(len(train_indices), len(val_indices), len(test_indices)) == 0:
            continue

        if task.task_type == "classification":
            if len(np.unique(targets[train_indices])) < 2 or len(np.unique(targets[test_indices])) < 2:
                continue

        if student_subset_eval and not student_mask[test_indices].any():
            continue

        return SplitResult(
            train_indices=train_indices,
            val_indices=val_indices,
            test_indices=test_indices,
            effective_seed=effective_seed,
        )

    raise ValueError(
        f"Could not create a valid grouped 70/15/15 split for {task.task_id} after {max_attempts} attempts."
    )


def _classification_metrics(targets: np.ndarray, probabilities: np.ndarray) -> dict[str, float]:
    predictions = (probabilities >= 0.5).astype(int)
    return {
        "auroc": float(roc_auc_score(targets, probabilities)),
        "f1": float(f1_score(targets, predictions, zero_division=0)),
        "precision": float(precision_score(targets, predictions, zero_division=0)),
        "recall": float(recall_score(targets, predictions, zero_division=0)),
        "accuracy": float(accuracy_score(targets, predictions)),
        "brier_score": float(brier_score_loss(targets, probabilities)),
    }


def _regression_metrics(targets: np.ndarray, predictions: np.ndarray) -> dict[str, float]:
    return {
        "mae": float(mean_absolute_error(targets, predictions)),
        "rmse": float(mean_squared_error(targets, predictions) ** 0.5),
        "r2": float(r2_score(targets, predictions)),
    }


def _dataset_tensor(features: np.ndarray, targets: np.ndarray) -> TensorDataset:
    return TensorDataset(
        torch.tensor(features, dtype=torch.float32),
        torch.tensor(targets, dtype=torch.float32),
    )


def train_mlp_model(
    task: TaskConfig,
    train_features: np.ndarray,
    train_targets: np.ndarray,
    val_features: np.ndarray,
    val_targets: np.ndarray,
    seed: int,
    config: TrainingConfig,
) -> tuple[TabularMLP, list[dict[str, float]]]:
    _set_seed(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = TabularMLP(input_dim=train_features.shape[1]).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

    if task.task_type == "classification":
        positive_count = max(float(train_targets.sum()), 1.0)
        negative_count = max(float(len(train_targets) - train_targets.sum()), 1.0)
        pos_weight = torch.tensor([negative_count / positive_count], dtype=torch.float32, device=device)
        loss_fn: nn.Module = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    else:
        loss_fn = nn.SmoothL1Loss()

    train_loader = DataLoader(
        _dataset_tensor(train_features, train_targets),
        batch_size=config.batch_size,
        shuffle=True,
    )
    val_loader = DataLoader(
        _dataset_tensor(val_features, val_targets),
        batch_size=config.batch_size,
        shuffle=False,
    )

    best_state = None
    best_val_loss = float("inf")
    epochs_without_improvement = 0
    history: list[dict[str, float]] = []

    for epoch in range(config.max_epochs):
        model.train()
        running_train_loss = 0.0
        train_batches = 0

        for batch_features, batch_targets in train_loader:
            batch_features = batch_features.to(device)
            batch_targets = batch_targets.to(device)

            optimizer.zero_grad()
            logits = model(batch_features).squeeze(-1)
            loss = loss_fn(logits, batch_targets)
            loss.backward()
            optimizer.step()

            running_train_loss += float(loss.item())
            train_batches += 1

        model.eval()
        running_val_loss = 0.0
        val_batches = 0
        with torch.no_grad():
            for batch_features, batch_targets in val_loader:
                batch_features = batch_features.to(device)
                batch_targets = batch_targets.to(device)
                logits = model(batch_features).squeeze(-1)
                loss = loss_fn(logits, batch_targets)
                running_val_loss += float(loss.item())
                val_batches += 1

        train_loss = running_train_loss / max(train_batches, 1)
        val_loss = running_val_loss / max(val_batches, 1)
        history.append({"epoch": float(epoch + 1), "train_loss": train_loss, "val_loss": val_loss})

        if val_loss < best_val_loss - 1e-6:
            best_val_loss = val_loss
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= config.patience:
                break

    if best_state is not None:
        model.load_state_dict(best_state)

    return model, history


def predict_mlp(
    task: TaskConfig,
    model: TabularMLP,
    features: np.ndarray,
    batch_size: int,
) -> np.ndarray:
    device = next(model.parameters()).device
    loader = DataLoader(
        TensorDataset(torch.tensor(features, dtype=torch.float32)),
        batch_size=batch_size,
        shuffle=False,
    )
    outputs: list[np.ndarray] = []
    model.eval()
    with torch.inference_mode():
        for (batch_features,) in loader:
            logits = model(batch_features.to(device)).squeeze(-1).cpu().numpy()
            if task.task_type == "classification":
                outputs.append(1.0 / (1.0 + np.exp(-logits)))
            else:
                outputs.append(logits)

    return np.concatenate(outputs, axis=0)


def run_task_training(
    task: TaskConfig,
    benchmark_dir: Path,
    output_dir: Path,
    seed: int,
    student_subset_eval: bool,
    training_config: TrainingConfig | None = None,
) -> dict[str, object]:
    training_config = training_config or TrainingConfig()
    benchmark_path = benchmark_dir / task.benchmark_filename
    raw_frame = _load_benchmark_frame(benchmark_path)
    prepared_frame = prepare_task_frame(task, raw_frame)

    split_result = make_group_splits(
        prepared_frame,
        task=task,
        seed=seed,
        student_subset_eval=student_subset_eval,
    )

    train_frame = prepared_frame.iloc[split_result.train_indices].reset_index(drop=True)
    val_frame = prepared_frame.iloc[split_result.val_indices].reset_index(drop=True)
    test_frame = prepared_frame.iloc[split_result.test_indices].reset_index(drop=True)

    feature_manifest = build_feature_manifest(task, train_frame)
    preprocessor = BenchmarkPreprocessor(
        numeric_features=feature_manifest["numeric_features"],
        boolean_features=feature_manifest["boolean_features"],
        categorical_features=feature_manifest["categorical_features"],
    )

    train_features = preprocessor.fit_transform(train_frame[feature_manifest["candidate_columns"]])
    val_features = preprocessor.transform(val_frame[feature_manifest["candidate_columns"]])
    test_features = preprocessor.transform(test_frame[feature_manifest["candidate_columns"]])

    feature_manifest["transformed_feature_names"] = preprocessor.get_feature_names_out()
    feature_manifest["transformed_feature_count"] = len(feature_manifest["transformed_feature_names"])
    feature_manifest["numeric_features"] = preprocessor.active_numeric_features
    feature_manifest["boolean_features"] = preprocessor.active_boolean_features
    feature_manifest["dropped_all_missing_features"] = sorted(preprocessor.dropped_all_missing_features)
    feature_manifest["dropped_columns"] = sorted(
        set(feature_manifest["dropped_columns"]) | set(preprocessor.dropped_all_missing_features)
    )

    train_targets = train_frame["__target__"].to_numpy(dtype=np.float32)
    val_targets = val_frame["__target__"].to_numpy(dtype=np.float32)
    test_targets = test_frame["__target__"].to_numpy(dtype=np.float32)

    model_dir = output_dir / task.task_id / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    dump(preprocessor, model_dir / "preprocessor.joblib")

    comparison_rows: list[dict[str, object]] = []
    prediction_payload = test_frame[
        ["source_dataset", "respondent_id", "group_key", "student_status_proxy"]
    ].copy()
    prediction_payload["actual_target"] = test_targets

    model_metrics: dict[str, dict[str, float]] = {}

    if task.task_type == "classification":
        baseline_models = {
            "logistic_regression": LogisticRegression(
                max_iter=1000,
                class_weight="balanced",
                random_state=seed,
                solver="liblinear",
            ),
            "hist_gradient_boosting": HistGradientBoostingClassifier(random_state=seed),
        }
    else:
        baseline_models = {
            "ridge": Ridge(),
            "hist_gradient_boosting": HistGradientBoostingRegressor(random_state=seed),
        }

    for model_name, model in baseline_models.items():
        model.fit(train_features, train_targets)
        if task.task_type == "classification":
            predictions = model.predict_proba(test_features)[:, 1]
            metrics = _classification_metrics(test_targets.astype(int), predictions)
            prediction_payload[f"{model_name}_probability"] = predictions
            prediction_payload[f"{model_name}_prediction"] = (predictions >= 0.5).astype(int)
        else:
            predictions = model.predict(test_features)
            metrics = _regression_metrics(test_targets, predictions)
            prediction_payload[f"{model_name}_prediction"] = predictions

        model_metrics[model_name] = metrics
        comparison_rows.append({"model_name": model_name, **metrics})
        dump(model, model_dir / f"{model_name}.joblib")

    mlp_model, training_history = train_mlp_model(
        task=task,
        train_features=train_features,
        train_targets=train_targets,
        val_features=val_features,
        val_targets=val_targets,
        seed=seed,
        config=training_config,
    )
    mlp_predictions = predict_mlp(
        task=task,
        model=mlp_model,
        features=test_features,
        batch_size=training_config.batch_size,
    )

    if task.task_type == "classification":
        mlp_metrics = _classification_metrics(test_targets.astype(int), mlp_predictions)
        prediction_payload["mlp_probability"] = mlp_predictions
        prediction_payload["mlp_prediction"] = (mlp_predictions >= 0.5).astype(int)
    else:
        mlp_metrics = _regression_metrics(test_targets, mlp_predictions)
        prediction_payload["mlp_prediction"] = mlp_predictions

    model_metrics["mlp"] = mlp_metrics
    comparison_rows.append({"model_name": "mlp", **mlp_metrics})
    torch.save(
        {
            "task_id": task.task_id,
            "task_type": task.task_type,
            "seed": seed,
            "feature_names": feature_manifest["transformed_feature_names"],
            "model_state": mlp_model.state_dict(),
            "history": training_history,
        },
        model_dir / "mlp_model.pt",
    )
    _write_json(model_dir / "mlp_history.json", training_history)

    prediction_payload.to_csv(output_dir / task.task_id / "predictions_test.csv", index=False)
    pd.DataFrame(comparison_rows).to_csv(output_dir / task.task_id / "comparison.csv", index=False)

    train_groups = sorted(train_frame["group_key"].unique().tolist())
    val_groups = sorted(val_frame["group_key"].unique().tolist())
    test_groups = sorted(test_frame["group_key"].unique().tolist())
    split_manifest = {
        "task_id": task.task_id,
        "benchmark_file": task.benchmark_filename,
        "base_seed": seed,
        "effective_seed": split_result.effective_seed,
        "split_ratio_target": {"train": 0.70, "val": 0.15, "test": 0.15},
        "row_counts": {
            "train": int(len(train_frame)),
            "val": int(len(val_frame)),
            "test": int(len(test_frame)),
        },
        "group_counts": {
            "train": int(len(train_groups)),
            "val": int(len(val_groups)),
            "test": int(len(test_groups)),
        },
        "train_group_keys": train_groups,
        "val_group_keys": val_groups,
        "test_group_keys": test_groups,
    }

    _write_json(output_dir / task.task_id / "feature_manifest.json", feature_manifest)
    _write_json(output_dir / task.task_id / "split_manifest.json", split_manifest)

    student_subset_mask = test_frame["student_status_proxy"].map(_is_student_status)
    student_subset_count = int(student_subset_mask.sum())
    if student_subset_eval and student_subset_count == 0:
        raise ValueError(f"{task.task_id} has no valid student subset rows in the test split.")

    student_subset_metrics: dict[str, object] = {
        "student_subset_test_rows": student_subset_count,
        "student_subset_group_count": int(test_frame.loc[student_subset_mask, "group_key"].nunique()),
        "metrics": {},
    }

    if student_subset_count > 0:
        subset_targets = test_targets[student_subset_mask.to_numpy()]
        for model_name in model_metrics:
            if task.task_type == "classification":
                probabilities = prediction_payload.loc[student_subset_mask, f"{model_name}_probability"].to_numpy()
                student_subset_metrics["metrics"][model_name] = _classification_metrics(
                    subset_targets.astype(int),
                    probabilities,
                )
            else:
                predictions = prediction_payload.loc[student_subset_mask, f"{model_name}_prediction"].to_numpy()
                student_subset_metrics["metrics"][model_name] = _regression_metrics(
                    subset_targets,
                    predictions,
                )

    _write_json(output_dir / task.task_id / "student_subset_metrics.json", student_subset_metrics)

    metrics_payload: dict[str, object] = {
        "task_id": task.task_id,
        "task_type": task.task_type,
        "benchmark_file": task.benchmark_filename,
        "dataset_sources": sorted(prepared_frame["source_dataset"].dropna().astype(str).unique().tolist()),
        "note": TASK_NOTE,
        "row_count": int(len(prepared_frame)),
        "split_counts": split_manifest["row_counts"],
        "feature_count": int(feature_manifest["transformed_feature_count"]),
        "raw_feature_count": int(len(feature_manifest["candidate_columns"])),
        "model_metrics": model_metrics,
        "student_subset_eval_enabled": bool(student_subset_eval),
        "student_subset_test_rows": student_subset_count,
        "student_subset_group_count": student_subset_metrics["student_subset_group_count"],
        "survey_weights_used_for_training": False,
    }

    if task.task_type == "classification":
        metrics_payload["positive_class_rate"] = {
            "overall": float(prepared_frame["__target__"].mean()),
            "train": float(train_frame["__target__"].mean()),
            "val": float(val_frame["__target__"].mean()),
            "test": float(test_frame["__target__"].mean()),
        }

    _write_json(output_dir / task.task_id / "metrics.json", metrics_payload)
    return metrics_payload


def parse_task_selection(selection: str) -> list[TaskConfig]:
    if selection == "all":
        return [TASKS[task_id] for task_id in sorted(TASKS)]

    task_ids = [item.strip() for item in selection.split(",") if item.strip()]
    unknown = sorted(set(task_ids) - set(TASKS))
    if unknown:
        raise ValueError(f"Unknown task ids: {', '.join(unknown)}")
    return [TASKS[task_id] for task_id in task_ids]


def run_public_benchmark_training(
    benchmark_dir: Path,
    output_dir: Path,
    tasks: list[TaskConfig],
    seed: int,
    student_subset_eval: bool,
    training_config: TrainingConfig | None = None,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary: dict[str, object] = {}
    for task in tasks:
        summary[task.task_id] = run_task_training(
            task=task,
            benchmark_dir=benchmark_dir,
            output_dir=output_dir,
            seed=seed,
            student_subset_eval=student_subset_eval,
            training_config=training_config,
        )
    _write_json(output_dir / "summary.json", summary)
    return summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Train public benchmark models on the generated finance benchmark CSVs."
    )
    parser.add_argument(
        "--benchmark-dir",
        default="artifacts/benchmarks",
        help="Directory containing public benchmark CSVs",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory for benchmark training outputs",
    )
    parser.add_argument(
        "--tasks",
        default="all",
        help="Comma-separated task ids or 'all'",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--student-subset-eval",
        default=True,
        action=argparse.BooleanOptionalAction,
        help="Compute test-split student subset metrics",
    )
    args = parser.parse_args(argv)

    _set_seed(args.seed)
    benchmark_dir = Path(args.benchmark_dir)
    output_dir = Path(args.output_dir)
    tasks = parse_task_selection(args.tasks)

    summary = run_public_benchmark_training(
        benchmark_dir=benchmark_dir,
        output_dir=output_dir,
        tasks=tasks,
        seed=args.seed,
        student_subset_eval=args.student_subset_eval,
    )
    print(json.dumps(summary, indent=2, default=_json_default))


if __name__ == "__main__":
    main()
