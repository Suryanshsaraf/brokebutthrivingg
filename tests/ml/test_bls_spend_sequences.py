from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pandas as pd

from brokebutthriving.ml.build_bls_spend_sequences import build_bls_spend_sequence_benchmark
from brokebutthriving.ml.ingest_bls_cex import build_bls_cex_interview_frame
from brokebutthriving.ml.train_spend_sequences import main


def _fmli_row(
    cuid: int,
    interview_number: int,
    year: int,
    month: int,
    total: float,
    age: int = 28,
    student_debt: float | None = 0.0,
) -> dict[str, object]:
    return {
        "NEWID": int(f"{cuid}{interview_number}"),
        "CUID": cuid,
        "INTERI": interview_number,
        "QINTRVYR": year,
        "QINTRVMO": month,
        "FINLWT21": 1000.0,
        "AGE_REF": age,
        "FAM_SIZE": 2,
        "BLS_URBN": 1,
        "CUTENURE": 2,
        "REGION": 3,
        "EDUC_REF": 16,
        "HIGH_EDU": 16,
        "PERSLT18": 0,
        "PERSOT64": 0,
        "NO_EARNR": 1,
        "NUM_AUTO": 1,
        "VEHQ": 1,
        "INC_RANK": 0.5,
        "INCLASS2": 3,
        "FINCBTAX": 48000.0,
        "FSALARYX": 42000.0,
        "INTRDVX": 250.0,
        "LIQUIDX": 5000.0,
        "CREDITX": 1200.0,
        "STUDNTX": student_debt,
        "TOTEXPPQ": total,
        "FOODPQ": total * 0.18,
        "FDHOMEPQ": total * 0.10,
        "FDAWAYPQ": total * 0.08,
        "ALCBEVPQ": total * 0.01,
        "HOUSPQ": total * 0.32,
        "SHELTPQ": total * 0.22,
        "UTILPQ": total * 0.07,
        "HOUSEQPQ": total * 0.03,
        "APPARPQ": total * 0.04,
        "TRANSPQ": total * 0.14,
        "GASMOPQ": total * 0.03,
        "VEHFINPQ": total * 0.02,
        "PUBTRAPQ": total * 0.01,
        "HEALTHPQ": total * 0.08,
        "ENTERTPQ": total * 0.05,
        "PERSCAPQ": total * 0.02,
        "READPQ": total * 0.01,
        "EDUCAPQ": total * 0.02,
        "TOBACCPQ": 0.0,
        "MISCPQ": total * 0.02,
        "CASHCOPQ": total * 0.01,
        "PERINSPQ": total * 0.03,
        "RETPENPQ": total * 0.01,
    }


def _write_zip_with_frame(path: Path, member_name: str, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(member_name, frame.to_csv(index=False))


def test_bls_ingest_deduplicates_revised_quarter_rows(tmp_path: Path) -> None:
    intrvw23 = pd.DataFrame(
        [
            _fmli_row(900001, 4, 2024, 1, 1000.0),
        ]
    )
    intrvw24_revised = pd.DataFrame(
        [
            _fmli_row(900001, 4, 2024, 1, 1250.0),
            _fmli_row(900001, 1, 2024, 4, 1400.0),
        ]
    )

    _write_zip_with_frame(tmp_path / "intrvw23.zip", "intrvw23/fmli241.csv", intrvw23)
    _write_zip_with_frame(tmp_path / "intrvw24.zip", "intrvw24/fmli241x.csv", intrvw24_revised.iloc[[0]])
    with zipfile.ZipFile(tmp_path / "intrvw24.zip", "a") as archive:
        archive.writestr("intrvw24/fmli242.csv", intrvw24_revised.iloc[[1]].to_csv(index=False))

    frame = build_bls_cex_interview_frame(tmp_path)

    assert len(frame) == 2
    q1 = frame.loc[frame["quarter_label"] == "2024Q1", "total_expenditure_q"].iloc[0]
    assert q1 == 1250.0


def test_bls_sequence_builder_uses_only_consecutive_quarters(tmp_path: Path) -> None:
    normalized = pd.DataFrame(
        [
            _fmli_row(101001, 2, 2023, 4, 1000.0),
            _fmli_row(101001, 3, 2023, 7, 1100.0),
            _fmli_row(101001, 4, 2023, 10, 1500.0),
            _fmli_row(202002, 2, 2023, 4, 1000.0),
            _fmli_row(202002, 4, 2023, 10, 1600.0),
            _fmli_row(202002, 1, 2024, 4, 1700.0),
        ]
    )
    normalized["panel_id"] = normalized["CUID"].astype(str)
    normalized["quarter_index"] = [8092, 8093, 8094, 8092, 8094, 8096]
    normalized["quarter_label"] = ["2023Q2", "2023Q3", "2023Q4", "2023Q2", "2023Q4", "2024Q2"]
    normalized["sample_weight"] = 1000.0
    normalized["young_adult_proxy"] = 1
    normalized["student_debt_proxy"] = 0
    normalized["quarterly_income_proxy"] = 12000.0
    normalized["essential_spend_q"] = normalized["TOTEXPPQ"] * 0.7
    normalized["discretionary_spend_q"] = normalized["TOTEXPPQ"] * 0.2
    normalized["spend_to_income_proxy_q"] = normalized["TOTEXPPQ"] / 12000.0
    normalized["food_away_share"] = 0.08
    normalized["housing_share"] = 0.32
    normalized["transport_share"] = 0.14
    normalized["entertainment_share"] = 0.05
    normalized = normalized.rename(
        columns={
            "INTERI": "interview_number",
            "AGE_REF": "age_ref",
            "FAM_SIZE": "family_size",
            "BLS_URBN": "urban_flag",
            "CUTENURE": "housing_tenure_code",
            "REGION": "region_code",
            "EDUC_REF": "education_ref_code",
            "HIGH_EDU": "highest_education_code",
            "PERSLT18": "children_count",
            "PERSOT64": "older_adults_count",
            "NO_EARNR": "earners_count",
            "NUM_AUTO": "autos_count",
            "VEHQ": "vehicles_count",
            "INC_RANK": "income_rank",
            "INCLASS2": "income_class_code",
            "FINCBTAX": "after_tax_income_annual",
            "FSALARYX": "salary_income_annual",
            "INTRDVX": "interest_dividend_income_annual",
            "LIQUIDX": "liquid_assets",
            "CREDITX": "consumer_credit_balance",
            "STUDNTX": "student_loan_balance",
            "TOTEXPPQ": "total_expenditure_q",
            "FOODPQ": "food_expenditure_q",
            "FDHOMEPQ": "food_home_q",
            "FDAWAYPQ": "food_away_q",
            "ALCBEVPQ": "alcohol_beverages_q",
            "HOUSPQ": "housing_expenditure_q",
            "SHELTPQ": "shelter_expenditure_q",
            "UTILPQ": "utilities_expenditure_q",
            "HOUSEQPQ": "household_equipment_q",
            "APPARPQ": "apparel_expenditure_q",
            "TRANSPQ": "transportation_expenditure_q",
            "GASMOPQ": "gasoline_q",
            "VEHFINPQ": "vehicle_finance_q",
            "PUBTRAPQ": "public_transport_q",
            "HEALTHPQ": "healthcare_expenditure_q",
            "ENTERTPQ": "entertainment_expenditure_q",
            "PERSCAPQ": "personal_care_q",
            "READPQ": "reading_q",
            "EDUCAPQ": "education_expenditure_q",
            "TOBACCPQ": "tobacco_expenditure_q",
            "MISCPQ": "misc_expenditure_q",
            "CASHCOPQ": "cash_contributions_q",
            "PERINSPQ": "personal_insurance_q",
            "RETPENPQ": "retirement_pension_q",
        }
    )
    normalized_path = tmp_path / "normalized.csv"
    normalized.to_csv(normalized_path, index=False)

    benchmark = build_bls_spend_sequence_benchmark(normalized_path, seq_len=2, high_burn_multiplier=1.15)

    assert len(benchmark) == 1
    assert benchmark["panel_id"].iloc[0] == "101001"
    assert benchmark["target_high_burn_next_q"].iloc[0] == 1


def test_bls_sequence_training_smoke(tmp_path: Path) -> None:
    rows: list[dict[str, object]] = []
    for panel in range(220):
        subset = panel % 2 == 0
        lag2_total = 900.0 + panel * 20
        lag1_total = lag2_total + 80.0
        target = lag1_total * (1.25 if subset else 1.05)
        high_burn = int(target > ((lag2_total + lag1_total) / 2.0) * 1.15)
        rows.append(
            {
                "source_dataset": "bls_cex_interview",
                "panel_id": f"panel-{panel}",
                "seq_len": 2,
                "history_start_quarter_label": "2023Q2",
                "target_quarter_label": "2023Q4",
                "target_quarter_index": 8094 + panel,
                "target_sample_weight": 1000.0 + panel,
                "young_adult_proxy": int(subset),
                "student_debt_proxy": int(subset),
                "young_or_student_proxy": int(subset),
                "target_next_total_expenditure_q": target,
                "target_high_burn_next_q": high_burn,
                "lag2_total_expenditure_q": lag2_total,
                "lag1_total_expenditure_q": lag1_total,
                "lag2_food_expenditure_q": lag2_total * 0.2,
                "lag1_food_expenditure_q": lag1_total * 0.2,
                "lag2_after_tax_income_annual": 48000.0 + panel * 250,
                "lag1_after_tax_income_annual": 48500.0 + panel * 250,
                "lag2_quarterly_income_proxy": 12000.0 + panel * 60,
                "lag1_quarterly_income_proxy": 12100.0 + panel * 60,
                "lag2_spend_to_income_proxy_q": lag2_total / (12000.0 + panel * 60),
                "lag1_spend_to_income_proxy_q": lag1_total / (12100.0 + panel * 60),
                "lag2_region_code": 1 + (panel % 4),
                "lag1_region_code": 1 + (panel % 4),
                "lag2_housing_tenure_code": 1 + (panel % 3),
                "lag1_housing_tenure_code": 1 + (panel % 3),
                "lag2_young_adult_proxy": int(subset),
                "lag1_young_adult_proxy": int(subset),
                "lag2_student_debt_proxy": int(subset),
                "lag1_student_debt_proxy": int(subset),
            }
        )

    benchmark_path = tmp_path / "bls_benchmark.csv"
    output_dir = tmp_path / "run"
    pd.DataFrame(rows).to_csv(benchmark_path, index=False)

    main(
        [
            "--benchmark-csv",
            str(benchmark_path),
            "--output-dir",
            str(output_dir),
            "--seed",
            "17",
        ]
    )

    assert (output_dir / "metrics.json").exists()
    assert (output_dir / "comparison.csv").exists()
    assert (output_dir / "predictions_test.csv").exists()
    assert (output_dir / "feature_manifest.json").exists()
    assert (output_dir / "split_manifest.json").exists()
    assert (output_dir / "young_student_subset_metrics.json").exists()
    assert (output_dir / "models" / "spend_sequence_model.pt").exists()

    with (output_dir / "metrics.json").open("r", encoding="utf-8") as handle:
        metrics = json.load(handle)
    assert metrics["feature_count_flat"] > 0
    assert metrics["feature_count_sequence"] > 0
