import asyncio

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from agents.executors.base import ExecutionRequest
from agents.executors.shopsim_executor import ShopSimExecutor
from backend.api.deps import db_session
from backend.core.config import get_settings
from backend.core.metrics import (
    EXECUTION_COUNT,
    EXECUTION_FAILURE_COUNT,
    EXECUTION_LATENCY,
    TASK_SUCCESS_RATE,
)
from backend.schemas.execution import ExecutionIntent
from backend.services.execution_store import (
    create_execution_run,
    fail_stale_execution_runs,
    list_execution_runs,
    update_execution_run,
)

router = APIRouter(prefix="/execution", tags=["execution"])
settings = get_settings()


@router.post("/shopsim")
async def execute_shopsim(payload: ExecutionIntent, db: Session = Depends(db_session)):
    run = create_execution_run(db, payload.session_id, "shopsim", payload.model_dump())
    
    def progress_hook(
        *,
        status: str,
        steps: list[dict],
        screenshot_paths: list[str],
        failure_category: str | None,
        latency_ms: int | None,
    ) -> None:
        update_execution_run(
            db,
            run.run_id,
            status=status,
            steps=steps,
            screenshot_paths=screenshot_paths,
            failure_category=failure_category,
            latency_ms=latency_ms,
        )

    executor = ShopSimExecutor(
        base_url=settings.shopsim_base_url,
        artifacts_dir=settings.execution_artifacts_dir,
        headless=settings.playwright_headless,
        progress_hook=progress_hook,
    )
    try:
        result = await asyncio.wait_for(
            executor.run(
                ExecutionRequest(
                    session_id=payload.session_id,
                    query=payload.query,
                    category=payload.category,
                    filters=payload.filters,
                    product_id=payload.product_id,
                    checkout_approved=bool(payload.filters.get("checkout_approved", False)),
                    run_id=run.run_id,
                )
            ),
            timeout=55,
        )
    except Exception:
        run = update_execution_run(
            db,
            run.run_id,
            status="failed",
            steps=[{"action": "execution", "status": "failed"}],
            screenshot_paths=[],
            failure_category="execution_error",
            latency_ms=None,
        )
        EXECUTION_COUNT.labels(executor="shopsim", outcome="failed").inc()
        EXECUTION_FAILURE_COUNT.labels(category="execution_error").inc()
        runs = list_execution_runs(db, payload.session_id)
        successes = sum(1 for item in runs if item.status == "success")
        TASK_SUCCESS_RATE.set(successes / len(runs) if runs else 0.0)
        return {"run_id": run.run_id, "status": "failed", "steps": run.steps, "screenshots": []}

    status = "success" if result.success else "failed"
    update_execution_run(
        db,
        run.run_id,
        status=status,
        steps=result.steps,
        screenshot_paths=result.screenshot_paths,
        failure_category=result.failure_category,
        latency_ms=result.latency_ms,
    )
    EXECUTION_COUNT.labels(executor="shopsim", outcome=status).inc()
    EXECUTION_LATENCY.labels(executor="shopsim").observe(result.latency_ms / 1000.0)
    if result.failure_category:
        EXECUTION_FAILURE_COUNT.labels(category=result.failure_category).inc()

    runs = list_execution_runs(db, payload.session_id)
    successes = sum(1 for item in runs if item.status == "success")
    TASK_SUCCESS_RATE.set(successes / len(runs) if runs else 0.0)
    return {"run_id": run.run_id, "status": status, "steps": result.steps, "screenshots": result.screenshot_paths}


@router.get("/runs")
def execution_runs(session_id: str | None = None, db: Session = Depends(db_session)):
    fail_stale_execution_runs(db, session_id=session_id, stale_after_seconds=60)
    return list_execution_runs(db, session_id)
