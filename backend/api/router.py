from fastapi import APIRouter

from backend.api.routes.benchmarking import router as benchmarking_router
from backend.api.routes.execution import router as execution_router
from backend.api.routes.health import router as health_router
from backend.api.routes.ecommerce import router as ecommerce_router
from backend.api.routes.preferences import router as preference_router
from backend.api.routes.recommendations import router as recommendation_router
from backend.api.routes.tasks import router as task_router

api_router = APIRouter()
api_router.include_router(benchmarking_router)
api_router.include_router(health_router)
api_router.include_router(ecommerce_router)
api_router.include_router(execution_router)
api_router.include_router(preference_router)
api_router.include_router(recommendation_router)
api_router.include_router(task_router)
