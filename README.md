# FinPilot AI

FinPilot AI is a local-first personal finance assistant built with Flask, SQLite, and machine learning. It combines a web dashboard with a multi-agent workflow for financial analysis, health scoring, budget optimization, purchase decisions, savings forecasts, and recommendations.

## Features

- Dashboard with financial summaries, health score, spending insights, and forecasts
- Transaction creation, editing, deletion, filtering, and CSV import
- Savings goals with progress tracking and monthly contribution guidance
- What-if simulator for exploring changes to income, expenses, and savings
- Purchase check workflow powered by the purchase decision model
- Chat-style financial assistant backed by coordinated specialist agents
- Local SQLite persistence with seeded demo data
- Four local scikit-learn model artifacts that are verified or retrained at startup

## Architecture

The request workflow is coordinated by `backend/agents/coordinator.py`:

1. Intent detection
2. Financial analysis
3. Financial health prediction
4. Budget optimization
5. Purchase decision analysis
6. Savings forecasting
7. Prediction validation and correction
8. Recommendation generation

The Flask application and API routes live in `backend/app.py`. HTML templates are in `templates/`, browser code is in `static/`, and model training utilities are in `backend/training/`.

## Requirements

- Python 3.10 or newer
- pip

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

## Run Locally

From the project root:

```bash
python run.py
```

Open http://127.0.0.1:5000 in a browser.

On first launch, FinPilot AI creates `backend/finpilot.db` with demo data. It also verifies the four model files in `backend/models/` and trains missing or invalid models automatically.

## Train Models Manually

To regenerate all local model artifacts:

```bash
python -m backend.training.train_models
```

## Project Structure

```text
.
├── backend/
│   ├── agents/          Multi-agent finance workflow
│   ├── database/        SQLite connection and schema
│   ├── models/          Local scikit-learn model artifacts
│   └── training/        Dataset generation and model training
├── static/              CSS and browser JavaScript
├── templates/           Flask/Jinja pages
├── requirements.txt
└── run.py               Application entry point
```

## Notes

This project is intended for local development and educational use. It does not provide regulated financial advice. The included data is demo data; review the application configuration and data handling before using it with real financial information.
