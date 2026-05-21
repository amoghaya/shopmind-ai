# ShopMind AI

Human-supervised autonomous shopping avatar with Hybrid-Neuro Bandit recommendations, a sandbox ecommerce site, adaptive user preference learning, price tracking, and a React demo dashboard.

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
- Redis

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
- Prometheus
- Grafana
- MLflow

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

## Does A GitHub Clone Start With My Preferences?

Yes, it can start fresh for each user, as long as you **do not commit your local runtime state**.

Do **not** push these to GitHub:

- `.env`
- `shopmind.db`
- `artifacts/`
- `__pycache__/`
- `.pytest_cache/`

Why:

- local profile memory is stored in the local database
- if `shopmind.db` is committed, another user may inherit your saved `demo-user` profile
- if `shopmind.db` is not committed, each clone will generate its own fresh local state
- for Docker runs, each user gets their own local Postgres volume on their own machine

Important current limitation:

- the app currently uses a default demo persona id: `demo-user`
- so one machine has one shared local demo profile unless you later add real user auth or user switching

For GitHub submission, this is acceptable as long as the database is not committed.

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

Add screenshots here before publishing:

### Dashboard Banner

`docs/screenshots/banner.png`

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

## What To Remove Before Pushing To GitHub

Remove generated local/runtime files:

- `shopmind.db`
- `artifacts/`
- `.pytest_cache/`
- all `__pycache__/`
- any local `node_modules/`
- any local `dist/`

Optional cleanup:

- keep `ai-shopping-avatar/` if you want to preserve the legacy prototype as a reference
- remove `ai-shopping-avatar/` if you want a cleaner final submission and you are no longer using it

## Recommended Final GitHub Repo State

Keep:

- `backend/`
- `frontend/`
- `ml/`
- `agents/`
- `infra/`
- `docker/`
- `tests/`
- `docs/`
- `benchmarking/`

Do not commit:

- local DB
- local env files
- benchmark output artifacts
- execution screenshots
- caches

## License / Academic Note

This project is intended as an academic B.Tech final-year applied AI systems project and demo prototype.
