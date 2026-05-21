# Phase 1 Architecture

## Objectives

- replace the Streamlit-only prototype with a backend-centric research stack
- make observability and reproducibility first-class from the start
- avoid premature microservice sprawl by keeping one API service and one worker image

## Decisions

- FastAPI for the control plane and API surface
- PostgreSQL for state that needs auditability and later offline analysis
- Redis for queues, caching, and short-lived coordination
- Celery for asynchronous agent and price-tracking tasks
- Prometheus + Grafana for runtime metrics
- MLflow for later experiment tracking
- shared Python packages for `backend`, `ml`, and `agents` to avoid distributed-system overhead

## Phase 1 boundary

Implemented now:

- backend service skeleton
- DB schema for preferences, recommendations, and agent tasks
- recommendation scaffold with HNB-style expert fusion
- metrics endpoint and dashboards
- Docker Compose stack

Sandbox ecommerce environment is the primary execution target:

- controlled catalog, reviews, cart, checkout, sessions, and recommendation slots
- benchmark task definitions stored in the backend DB
- `shopsim` executor used for reproducible benchmarking
- `amazon` and `flipkart` adapters isolated as experimental-only extensions

Deferred to later phases:

- real dataset ingestion
- full online HNB training loop
- Playwright browser trace capture against the sandbox UI
- benchmark runner and ablation automation
- human-in-the-loop execution dashboard
