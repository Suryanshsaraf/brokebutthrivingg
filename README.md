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
```

Training only uses collected data from the local SQLite database. No synthetic values are injected into the training pipeline.

### Public datasets

```bash
source .venv/bin/activate
bbt-fetch-public-data --list
bbt-fetch-public-data --dataset cfpb_fwb
bbt-fetch-public-data --dataset fed_shed
bbt-ingest-shed --input-dir data/external/fed_shed --output artifacts/normalized/fed_shed_normalized.csv
```

The public-data downloader fetches official finance datasets that are script-downloadable and flags sources that still require manual acquisition, such as BLS CE PUMD and NCES NPSAS.

The SHED ingester normalizes respondent-level finance and student-burden variables into a modeling table. Current output columns include financial strain, year-over-year financial change, student status, education level, employment, income band, housing concern, making-ends-meet concern, and student-loan burden indicators.
