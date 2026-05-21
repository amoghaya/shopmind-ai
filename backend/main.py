from pathlib import Path
from time import perf_counter

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from backend.api.router import api_router
from backend.core.config import get_settings
from backend.core.logging import configure_logging, get_logger
from backend.core.metrics import REQUEST_COUNT, REQUEST_LATENCY
from backend.db.base import Base
from backend.services.ecommerce_seed import seed_mock_shop
from backend.db.session import engine
from backend.db.session import SessionLocal

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)

app = FastAPI(title=settings.app_name, default_response_class=ORJSONResponse)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_origin,
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://frontend:5173",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_prefix)
app.mount("/artifacts", StaticFiles(directory="artifacts"), name="artifacts")


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    Path(settings.execution_artifacts_dir).mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db:
        seed_mock_shop(db)
    logger.info("app.startup", env=settings.app_env)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = perf_counter()
    response = await call_next(request)
    latency = perf_counter() - start
    path = request.url.path
    REQUEST_COUNT.labels(method=request.method, path=path, status=response.status_code).inc()
    REQUEST_LATENCY.labels(method=request.method, path=path).observe(latency)
    return response


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
