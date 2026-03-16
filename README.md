# BrokeButThriving

An end-to-end student finance copilot built for real data collection, model training, and interactive decision support.

## What this repository contains

- `src/brokebutthriving/api`: FastAPI backend for participant onboarding, expense logging, check-ins, simulation, and dataset export.
- `src/brokebutthriving/ml`: feature engineering, sequence dataset generation, and multi-task model training code.
- `frontend`: React + Vite interface for collecting real student data and visualizing finance insights.
- `data`: local SQLite storage for pilot data collection.
- `artifacts`: trained model outputs and exported datasets.

## Project direction

The system is intentionally built around real data:

1. onboard students with budget and living-context metadata
2. collect expenses, cash inflows, and daily emotional/context signals
3. build training-ready time-series datasets
4. train a multi-task model for archetype tendency, financial-risk forecasting, and spend forecasting
5. surface personalized what-if simulations and interventions in the UI

## Local development

### Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
bbt-api
```

The API starts on `http://127.0.0.1:8000` by default.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend expects the backend at `http://127.0.0.1:8000/api/v1`. Override it with `VITE_API_BASE_URL`.

### Training

```bash
source .venv/bin/activate
bbt-fetch-public-data --list
bbt-export --db-path data/bbt.db --output artifacts/daily_dataset.csv
bbt-train --db-path data/bbt.db --output-dir artifacts/run-001
bbt-train-public-benchmarks --benchmark-dir artifacts/benchmarks --output-dir artifacts/public-benchmark-runs/run-001
bbt-train-spend-sequences --benchmark-csv artifacts/benchmarks/bls_cex_spend_sequence_benchmark.csv --output-dir artifacts/sequence-runs/run-001
```

Training only uses collected data from the local SQLite database. No synthetic values are injected into the training pipeline.

The public benchmark trainer produces report-ready metrics, grouped respondent splits, saved model artifacts, and student-subset evaluation files for:

- `wellbeing_regression`
- `hardship_classification`
- `future_difficulty_classification`

The BLS sequence trainer produces grouped panel splits, baseline comparisons, a real LSTM checkpoint, prediction exports, and proxy young-adult/student subgroup metrics for next-quarter spend forecasting and high-burn risk.

### Public datasets

```bash
source .venv/bin/activate
bbt-fetch-public-data --list
bbt-fetch-public-data --dataset cfpb_mem --dataset cfpb_fwb --dataset fed_shed --dataset bls_cex_interview_recent
bbt-ingest-bls-cex --input-dir data/external/bls_cex_interview_recent --output artifacts/normalized/bls_cex_interview_quarterly.csv
bbt-build-bls-spend-sequences --input-csv artifacts/normalized/bls_cex_interview_quarterly.csv --output artifacts/benchmarks/bls_cex_spend_sequence_benchmark.csv --seq-len 2
bbt-ingest-mem --input-dir data/external/cfpb_mem --output artifacts/normalized/cfpb_mem_normalized.csv
bbt-ingest-fwb --input-csv data/external/cfpb_fwb/cfpb_nfwbs_2016_data.csv --output artifacts/normalized/cfpb_fwb_normalized.csv
bbt-ingest-shed --input-dir data/external/fed_shed --output artifacts/normalized/fed_shed_normalized.csv
bbt-build-public-benchmarks --normalized-dir artifacts/normalized --output-dir artifacts/benchmarks
```

The public-data downloader fetches official finance datasets that are script-downloadable and still flags sources that require manual acquisition, such as NCES NPSAS.

Current normalized public tables:

- `artifacts/normalized/fed_shed_normalized.csv`: `117,102` respondent-year rows from 2013-2024
- `artifacts/normalized/cfpb_mem_normalized.csv`: `21,839` respondent-wave rows from the CFPB Making Ends Meet public files
- `artifacts/normalized/cfpb_fwb_normalized.csv`: `6,394` respondent rows from the CFPB Financial Well-Being Survey
- `artifacts/normalized/bls_cex_interview_quarterly.csv`: `76,946` quarterly household interview rows from BLS CE 2021-2025 interview periods

Current benchmark outputs:

- `artifacts/benchmarks/public_finance_master.csv`: `145,335` unified sparse rows across all normalized public sources
- `artifacts/benchmarks/public_wellbeing_benchmark.csv`: `27,103` rows with real `fwb_score` targets
- `artifacts/benchmarks/public_hardship_benchmark.csv`: `128,912` rows with real hardship/strain targets
- `artifacts/benchmarks/public_future_difficulty_benchmark.csv`: `4,657` rows with future bill-difficulty labels from MEM
- `artifacts/benchmarks/public_student_finance_rows.csv`: `6,389` student-coded rows across SHED, MEM, and FWB
- `artifacts/benchmarks/bls_cex_spend_sequence_benchmark.csv`: `21,400` consecutive-quarter spend-sequence samples across `12,890` BLS panels

The benchmark builder intentionally keeps the normalized source tables intact and creates task-specific training tables on top. That avoids pretending the public surveys asked identical questions while still giving us real labeled data for model development.
