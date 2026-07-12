# QuantML

QuantML is an end-to-end machine learning research platform for generating and evaluating stock signals.

The project covers the full ML lifecycle:

* Market data ingestion
* Feature engineering
* Walk-forward model training
* Hyperparameter tuning
* Out-of-sample evaluation
* Explainable predictions
* Portfolio construction and risk controls
* Cost-aware backtesting
* Model monitoring
* FastAPI backend
* Next.js dashboard
* Automated testing and CI

The aim is not simply to train a model. It is to show how an ML system can be built, tested, monitored, and served as a complete application.

> QuantML is a research platform. It does not provide financial advice or automatically place live trades.

## Key Results

The current pipeline processes:

* **117,561** daily market observations
* **55** NASDAQ-100 stocks
* **24** engineered features
* **56** latest model signals
* **6-fold** expanding walk-forward validation

### Model performance

| Metric                     | Result |
| -------------------------- | -----: |
| Walk-forward signal Sharpe |   1.19 |
| Out-of-sample AUC          |  0.540 |
| BUY hit rate               |  52.8% |
| Out-of-sample accuracy     |  36.6% |

### Net-of-cost backtest

| Metric                | Strategy |   QQQ |
| --------------------- | -------: | ----: |
| CAGR                  |    18.5% | 15.7% |
| Total return          |   112.0% | 90.5% |
| Sharpe ratio          |     0.88 |     — |
| Sortino ratio         |     1.24 |     — |
| Maximum drawdown      |   -29.7% |     — |
| Annualised volatility |    22.0% |     — |

The backtest uses only out-of-sample predictions and includes commission, slippage, portfolio limits, and turnover costs.

The model shows a modest predictive edge rather than unrealistic backtest performance. Both the frictionless signal result and the deployable after-cost result are reported to make the effect of real-world constraints clear.

## How the System Works

```text
Market Data
    │
    ▼
Data Ingestion
    │
    ▼
Feature Engineering
    │
    ▼
Data Validation
    │
    ▼
Walk-Forward Training
    │
    ▼
Model Evaluation and Registry
    │
    ▼
Signal Generation and SHAP Explanations
    │
    ▼
Portfolio and Risk Engine
    │
    ▼
Cost-Aware Backtest / Paper Execution
    │
    ▼
FastAPI Backend
    │
    ▼
Next.js Dashboard
```

### 1. Data pipeline

The pipeline downloads adjusted daily OHLCV market data and stores it in Parquet format.

It then creates 24 causal features covering areas such as:

* Momentum
* Volatility
* Trend
* Volume
* Relative strength
* Price range
* Market microstructure

Features are standardised across the stock universe for each date. This allows the model to compare stocks relative to one another and reduces sensitivity to changing market conditions.

### 2. Walk-forward model training

The model is trained using expanding walk-forward validation.

Each fold is trained only on historical data and evaluated on the next unseen period. The model is never allowed to train on information from the future.

XGBoost produces probabilities for three signal classes:

* `BUY`
* `HOLD`
* `AVOID`

Hyperparameters are selected with Optuna using out-of-sample risk-adjusted performance rather than training accuracy.

### 3. Explainable signals

Each prediction includes:

* Signal class
* Confidence
* Expected return
* Risk level
* Main feature drivers

XGBoost SHAP contributions are used to show which features had the strongest influence on each prediction.

This makes the model output easier to inspect than a single unexplained classification.

### 4. Portfolio and risk controls

The model does not place trades directly.

Signals first pass through a separate portfolio and risk engine that applies:

* Confidence-based position sizing
* Volatility adjustments
* Maximum 20% exposure per stock
* Maximum 40% exposure per sector
* Maximum 100% gross exposure

The engine produces proposed orders, which are then passed to a selected execution adapter.

### 5. Backtesting

The backtest uses the same signal and risk logic as the application.

It includes:

* Walk-forward out-of-sample predictions
* Commission
* Slippage
* Portfolio turnover
* Weekly rebalancing
* Position and sector limits
* QQQ benchmark comparison

This keeps the reported returns closer to what the strategy could realistically achieve after implementation costs.

## Production Hardening and MLOps

The project includes operational features that are often missing from portfolio ML projects.

### Data validation

Pipeline artifacts are checked for:

* Expected columns
* Missing values
* Invalid numerical values
* Minimum row counts
* Data freshness

Critical validation failures stop the pipeline before model training or scoring.

### Drift monitoring

Population Stability Index is used to compare current feature distributions with the historical training data.

Each feature receives an `OK`, `WARN`, or `ALERT` status so it is possible to see when the model may be receiving unfamiliar inputs.

### Model registry

Each trained model is versioned with its parameters and evaluation metrics.

Model promotion is controlled by validation thresholds, and previous model versions can be restored when needed.

### Pipeline orchestration

A single pipeline command manages the main stages:

```text
ingest → features → validate → train → score → drift
```

Individual stages can also be run separately for development, debugging, or scheduled jobs.

### Monitoring and observability

The backend provides:

* Request counts
* Per-route response times
* Model health
* Data-quality status
* Feature-drift status
* Prometheus-compatible metrics
* Request IDs for tracing API calls through logs

## Testing and Continuous Integration

The project includes **137 deterministic tests** covering the most important parts of the system.

Tests include:

* Transaction costs and turnover
* Sharpe ratio, CAGR, and drawdown calculations
* Feature generation
* Forward-looking label checks
* Walk-forward data separation
* Portfolio and sector limits
* Model registry behaviour
* Execution safety
* API response contracts
* Live-trading protection

The tests run offline using seeded fixtures, so they do not depend on network access or existing model artifacts.

GitHub Actions runs the following on every push and pull request:

```bash
ruff check ml backend tests
pytest
npm run build
```

This checks Python formatting and imports, runs the test suite, validates TypeScript, and confirms that the frontend builds successfully.

## Technology Stack

| Area             | Technology                    |
| ---------------- | ----------------------------- |
| Machine learning | XGBoost, scikit-learn, Optuna |
| Data processing  | pandas, NumPy, PyArrow        |
| Backend          | FastAPI, Pydantic, Uvicorn    |
| Frontend         | Next.js, React, TypeScript    |
| Visualisation    | Recharts                      |
| Styling          | Tailwind CSS                  |
| Testing          | pytest, Ruff                  |
| CI               | GitHub Actions                |
| Storage          | Parquet and JSON artifacts    |
| Deployment       | Docker Compose                |
| Paper execution  | Alpaca API                    |

## Project Structure

```text
QuantML/
├── ml/
│   ├── ingestion/       Market data collection
│   ├── features/        Feature engineering
│   ├── labels/          Target generation
│   ├── training/        Walk-forward model training
│   ├── inference/       Signal generation
│   ├── research/        Tuning, drift and robustness studies
│   ├── validation.py    Data-quality checks
│   ├── registry.py      Model versioning and promotion
│   └── pipeline.py      Pipeline orchestration
│
├── backend/
│   ├── backtesting/     Cost-aware simulation
│   ├── execution/       Backtest, paper and live adapters
│   ├── portfolio/       Position sizing and risk limits
│   ├── services/        Artifact loading
│   └── main.py          FastAPI application
│
├── frontend/
│   ├── app/             Dashboard pages
│   ├── components/      Reusable interface components
│   └── lib/             API client and fallback data
│
├── tests/               Automated Python test suite
├── .github/workflows/   Continuous integration
└── docker-compose.yml   Full-stack local environment
```

## Getting Started

### Requirements

* Python 3.11 or later
* Node.js 20 or later

### Install Python dependencies

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows:

```bash
.venv\Scripts\activate
```

```bash
pip install -r ml/requirements.txt
pip install -r backend/requirements.txt
pip install -r requirements-dev.txt
```

### Run the ML pipeline

```bash
python -m ml.ingestion.download
python -m ml.features.build
python -m ml.training.walk_forward
python -m ml.inference.score
```

Or run the complete pipeline:

```bash
python -m ml.pipeline
```

### Start the backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

API documentation:

```text
http://localhost:8000/docs
```

### Start the frontend

From the repository root:

```bash
npm install
npm run dev
```

Dashboard:

```text
http://localhost:3000
```

### Run the tests

```bash
ruff check ml backend tests
pytest
```

### Run with Docker

```bash
docker compose up --build
```

## What This Project Demonstrates

QuantML demonstrates practical experience across the responsibilities of an ML engineer:

* Building reproducible data and feature pipelines
* Preventing time-series leakage
* Training and tuning models using realistic validation
* Comparing models against simple baselines
* Explaining individual predictions
* Turning model outputs into constrained decisions
* Evaluating performance after real-world costs
* Monitoring data quality and feature drift
* Versioning and promoting models
* Serving predictions through a typed API
* Building a frontend around real model artifacts
* Writing deterministic tests for ML and backend logic
* Running automated CI checks
* Designing safe separation between prediction, risk, and execution
