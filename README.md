# ShopMind AI

Human-supervised autonomous shopping avatar with Hybrid-Neuro Bandit recommendations, a sandbox ecommerce site, adaptive user preference learning, price tracking, and a React demo dashboard.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi)
![React](https://img.shields.io/badge/React-Frontend-61DAFB?logo=react)
![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?logo=docker)
![AI Agents](https://img.shields.io/badge/AI-Multi--Agent-purple)
![Contextual Bandits](https://img.shields.io/badge/ML-Hybrid%20Neuro%20Bandit-success)
![Status](https://img.shields.io/badge/Status-Active-success)
![License](https://img.shields.io/badge/License-MIT-yellow)

## What This Project Is

ShopMind AI is a B.Tech major project prototype that combines:

- a digital shopping avatar that learns user preferences over time
- an HNB-style adaptive recommender using Thompson Sampling, LinUCB, and epsilon-greedy experts
- a controlled mock ecommerce sandbox for reproducible demos
- simulated autonomous purchase execution with human approval
- watchlist and 30-day price tracking
- a lightweight benchmark dashboard comparing HNB against simple baselines

The main idea is:

1. the user interacts with products by liking, disliking, watchlisting, adding to cart, and checking out
2. the avatar stores preference memory such as brands, categories, liked tags, disliked tags, and budget
3. the HNB recommender adapts using online feedback
4. the sandbox storefront and benchmark page make the system demo-friendly and reproducible

## Tech Stack

### Backend

- Python
- FastAPI
- SQLAlchemy
- PostgreSQL for Dockerized runs
- SQLite for lightweight local runs


### Frontend

- React
- Vite
- custom CSS dashboard UI

### ML / Recommendation

- NumPy
- scikit-learn
- Hybrid-Neuro Bandit style aggregation
- Thompson Sampling
- LinUCB
- epsilon-greedy

### Infra / Observability

- Docker
- Docker Compose


## Main Features

- `AI Avatar Profile`
  - learned brands, categories, budget memory, liked/disliked tags, watchlist
- `Storefront`
  - search, filters, product detail, recommendations, cart, checkout
- `Price Tracker`
  - 30-day synthetic price history for watched products
- `Autonomous Buy`
  - supervised simulated execution flow inside the app
- `Execution Logs`
  - step-by-step purchase execution view
- `Benchmarks`
  - live regret graph and HNB vs baseline comparison

## How Preference Learning Works

The avatar and recommender learn from these actions:

- `Like`
  - strong positive preference signal
- `Dislike`
  - negative preference signal
- `Watchlist`
  - mild positive signal and starts price tracking
- `Add to cart`
  - positive purchase-intent signal
- `Checkout`
  - strong successful-intent signal
- `Autonomous buy`
  - simulated purchase flow that reinforces successful recommendation selection



## Project Structure

```text
backend/         FastAPI app, APIs, DB models, services, metrics
frontend/        React dashboard and sandbox storefront
ml/              HNB logic, experts, recommender service
agents/          agent and executor modules
benchmarking/    benchmark scripts
datasets/        dataset placeholders / future ingestion area
evaluation/      evaluation placeholders / future analysis area
infra/           Prometheus, Grafana, dashboards
docker/          Dockerfiles
docs/            architecture and project notes
tests/           sanity and integration tests
ai-shopping-avatar/ legacy prototype kept as reference
```

## Screenshots


### AI Avatar Profile

`docs/screenshots/avatar-profile.png`

### Storefront

`docs/screenshots/storefront.png`

### Execution Logs

`docs/screenshots/execution-logs.png`

### Benchmark Page

`docs/screenshots/benchmarks.png`

## How To Run Locally Without Docker

### 1. Clone the repo

```bash
git clone <your-repo-url>
cd shopmind-ai-v2
```

### 2. Create env file

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

### 3. Start backend

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### 4. Start frontend

```bash
cd frontend
npm install
npm run dev
```

### 5. Open the app

- frontend: [http://localhost:5173](http://localhost:5173)
- backend: [http://localhost:8000](http://localhost:8000)
- API health: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

## How To Run With Docker

### 1. Clone the repo

```bash
git clone <your-repo-url>
cd shopmind-ai-v2
```

### 2. Create env file

```bash
cp .env.example .env
```

### 3. Start the stack

```bash
docker compose up --build
```

This starts:

- backend on `8000`
- frontend on `5173`
- postgres on `5432`
- redis on `6379`
- prometheus on `9090`
- grafana on `3001`
- mlflow on `5000`

### 4. Open services

- app: [http://localhost:5173](http://localhost:5173)
- backend: [http://localhost:8000](http://localhost:8000)
- Prometheus: [http://localhost:9090](http://localhost:9090)
- Grafana: [http://localhost:3001](http://localhost:3001)
- MLflow: [http://localhost:5000](http://localhost:5000)

## How To Reset Local State

### Local SQLite run

Delete:

- `shopmind.db`
- `artifacts/`

Then restart the app.

### Docker run

Stop containers and remove volumes:

```bash
docker compose down -v
```

Then start again:

```bash
docker compose up --build
```

## Benchmarking

You can run the benchmark either:

- from the React `Benchmarks` page
- or from the script:

```bash
python benchmarking/run_demo_benchmark.py
```

Current baseline comparison:

- HNB
- Logistic Regression
- Top Rated
- Random

## References

### Core recommendation idea

- Bansal, N., Bala, M., & Sharma, K.  
  *Hybrid-Neuro Bandit: A bandit model for online recommendation.*  
  Defence Science Journal, 74(6), 885-892.

### Supporting tools and frameworks

- FastAPI documentation
- React documentation
- Vite documentation
- Playwright documentation
- Prometheus documentation
- Grafana documentation
- MLflow documentation



## License / Academic Note

This project is intended as an academic B.Tech final-year applied AI systems project and demo prototype.
