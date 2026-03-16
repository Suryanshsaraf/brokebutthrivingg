from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from torch import nn
from torch.utils.data import DataLoader

from brokebutthriving.ml.dataset import (
    FEATURE_COLUMNS,
    MultiTaskSequenceDataset,
    build_sequence_samples,
    split_participants,
)
from brokebutthriving.ml.features import build_daily_dataset
from brokebutthriving.ml.models import MultiTaskSequenceModel


def _filter_by_participants(samples, allowed_ids):
    return [sample for sample in samples if sample.participant_id in allowed_ids]


def _build_tabular_arrays(samples):
    x = np.array([sample.features[-1] for sample in samples], dtype=np.float32)
    risk = np.array([sample.risk_target for sample in samples], dtype=np.float32)
    archetype = np.array([sample.archetype_target for sample in samples], dtype=np.int64)
    spend = np.array([sample.spend_target for sample in samples], dtype=np.float32)
    return x, risk, archetype, spend


def _safe_auc(y_true, y_score) -> float | None:
    if len(np.unique(y_true)) < 2:
        return None
    return float(roc_auc_score(y_true, y_score))


def run_baseline(train_samples, test_samples) -> dict[str, float | None]:
    x_train, y_train_risk, _, _ = _build_tabular_arrays(train_samples)
    x_test, y_test_risk, _, _ = _build_tabular_arrays(test_samples)

    pipeline = Pipeline(
        [("scaler", StandardScaler()), ("model", LogisticRegression(max_iter=500, class_weight="balanced"))]
    )
    pipeline.fit(x_train, y_train_risk)
    probabilities = pipeline.predict_proba(x_test)[:, 1]
    predictions = (probabilities >= 0.5).astype(int)

    return {
        "risk_auc": _safe_auc(y_test_risk, probabilities),
        "risk_f1": float(f1_score(y_test_risk, predictions, zero_division=0)),
        "risk_precision": float(precision_score(y_test_risk, predictions, zero_division=0)),
        "risk_recall": float(recall_score(y_test_risk, predictions, zero_division=0)),
    }


def _evaluate_multitask(model, loader, device):
    model.eval()
    risk_targets = []
    risk_scores = []
    archetype_targets = []
    archetype_predictions = []
    spend_targets = []
    spend_predictions = []

    with torch.no_grad():
        for batch in loader:
            features = batch["features"].to(device)
            outputs = model(features)
            risk_probability = torch.sigmoid(outputs["risk_logits"]).cpu().numpy()
            archetype_prediction = torch.argmax(outputs["archetype_logits"], dim=1).cpu().numpy()
            spend_prediction = outputs["spend_prediction"].cpu().numpy()

            risk_scores.extend(risk_probability.tolist())
            risk_targets.extend(batch["risk_target"].numpy().tolist())
            archetype_targets.extend(batch["archetype_target"].numpy().tolist())
            archetype_predictions.extend(archetype_prediction.tolist())
            spend_targets.extend(batch["spend_target"].numpy().tolist())
            spend_predictions.extend(spend_prediction.tolist())

    spend_targets_raw = np.expm1(np.array(spend_targets))
    spend_predictions_raw = np.expm1(np.clip(np.array(spend_predictions), a_min=0, a_max=None))
    risk_binary = (np.array(risk_scores) >= 0.5).astype(int)

    metrics = {
        "risk_auc": _safe_auc(np.array(risk_targets), np.array(risk_scores)),
        "risk_f1": float(f1_score(risk_targets, risk_binary, zero_division=0)),
        "risk_precision": float(precision_score(risk_targets, risk_binary, zero_division=0)),
        "risk_recall": float(recall_score(risk_targets, risk_binary, zero_division=0)),
        "archetype_accuracy": float(accuracy_score(archetype_targets, archetype_predictions)),
        "archetype_macro_f1": float(
            f1_score(archetype_targets, archetype_predictions, average="macro", zero_division=0)
        ),
        "spend_mae": float(mean_absolute_error(spend_targets_raw, spend_predictions_raw)),
        "spend_rmse": float(mean_squared_error(spend_targets_raw, spend_predictions_raw) ** 0.5),
    }
    return metrics


def train_model(train_samples, val_samples, test_samples, epochs: int, batch_size: int):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = MultiTaskSequenceModel(input_dim=len(FEATURE_COLUMNS)).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    risk_loss_fn = nn.BCEWithLogitsLoss()
    archetype_loss_fn = nn.CrossEntropyLoss()
    spend_loss_fn = nn.SmoothL1Loss()

    train_loader = DataLoader(MultiTaskSequenceDataset(train_samples), batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(MultiTaskSequenceDataset(val_samples), batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(MultiTaskSequenceDataset(test_samples), batch_size=batch_size, shuffle=False)

    best_state = None
    best_val_loss = float("inf")

    for _ in range(epochs):
        model.train()
        running_loss = 0.0
        for batch in train_loader:
            optimizer.zero_grad()
            features = batch["features"].to(device)
            risk_target = batch["risk_target"].to(device)
            archetype_target = batch["archetype_target"].to(device)
            spend_target = batch["spend_target"].to(device)

            outputs = model(features)
            loss = (
                risk_loss_fn(outputs["risk_logits"], risk_target)
                + archetype_loss_fn(outputs["archetype_logits"], archetype_target)
                + spend_loss_fn(outputs["spend_prediction"], spend_target)
            )
            loss.backward()
            optimizer.step()
            running_loss += loss.item()

        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for batch in val_loader:
                features = batch["features"].to(device)
                risk_target = batch["risk_target"].to(device)
                archetype_target = batch["archetype_target"].to(device)
                spend_target = batch["spend_target"].to(device)
                outputs = model(features)
                batch_loss = (
                    risk_loss_fn(outputs["risk_logits"], risk_target)
                    + archetype_loss_fn(outputs["archetype_logits"], archetype_target)
                    + spend_loss_fn(outputs["spend_prediction"], spend_target)
                )
                val_loss += batch_loss.item()

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = model.state_dict()

    if best_state is not None:
        model.load_state_dict(best_state)

    return model, _evaluate_multitask(model, test_loader, device)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the multi-task student finance model.")
    parser.add_argument("--db-path", required=True, help="Path to the SQLite database")
    parser.add_argument("--output-dir", required=True, help="Directory for saved artifacts")
    parser.add_argument("--seq-len", type=int, default=30)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()

    frame = build_daily_dataset(args.db_path)
    if frame.empty:
        raise SystemExit("No dataset rows found. Collect participant data before training.")

    samples = build_sequence_samples(frame, seq_len=args.seq_len)
    participant_ids = [sample.participant_id for sample in samples]
    unique_ids = sorted(set(participant_ids))
    if len(unique_ids) < 3:
        raise SystemExit("Need data from at least 3 participants with surveys to create train/val/test splits.")

    train_ids, val_ids, test_ids = split_participants(unique_ids)
    train_samples = _filter_by_participants(samples, train_ids)
    val_samples = _filter_by_participants(samples, val_ids)
    test_samples = _filter_by_participants(samples, test_ids)

    if not train_samples or not val_samples or not test_samples:
        raise SystemExit("Insufficient sequence coverage after participant split. Collect more data.")

    baseline_metrics = run_baseline(train_samples, test_samples)
    model, multitask_metrics = train_model(
        train_samples=train_samples,
        val_samples=val_samples,
        test_samples=test_samples,
        epochs=args.epochs,
        batch_size=args.batch_size,
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    torch.save(
        {
            "model_state": model.state_dict(),
            "feature_columns": FEATURE_COLUMNS,
            "seq_len": args.seq_len,
        },
        output_dir / "multitask_model.pt",
    )
    frame.to_csv(output_dir / "daily_dataset.csv", index=False)

    metrics = {
        "sample_count": len(samples),
        "participant_count": len(unique_ids),
        "baseline_metrics": baseline_metrics,
        "multitask_metrics": multitask_metrics,
    }
    with (output_dir / "metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2)

    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
