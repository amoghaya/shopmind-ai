from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.db.models import ExecutionRun
from backend.schemas.execution import ExecutionRunRead


def create_execution_run(db: Session, session_id: str, executor_name: str, intent: dict) -> ExecutionRun:
    run = ExecutionRun(
        run_id=f"exec-{uuid4().hex[:12]}",
        session_id=session_id,
        executor_name=executor_name,
        status="created",
        intent=intent,
        steps=[],
        screenshot_paths=[],
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def update_execution_run(
    db: Session,
    run_id: str,
    *,
    status: str,
    steps: list[dict],
    screenshot_paths: list[str],
    failure_category: str | None,
    latency_ms: int | None,
) -> ExecutionRun:
    run = db.query(ExecutionRun).filter_by(run_id=run_id).one()
    run.status = status
    run.steps = steps
    run.screenshot_paths = screenshot_paths
    run.failure_category = failure_category
    run.latency_ms = latency_ms
    run.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(run)
    return run


def list_execution_runs(db: Session, session_id: str | None = None) -> list[ExecutionRunRead]:
    query = db.query(ExecutionRun).order_by(ExecutionRun.created_at.desc())
    if session_id:
        query = query.filter_by(session_id=session_id)
    runs = query.limit(20).all()
    return [
        ExecutionRunRead(
            run_id=run.run_id,
            session_id=run.session_id,
            executor_name=run.executor_name,
            status=run.status,
            steps=run.steps,
            screenshot_paths=run.screenshot_paths,
            screenshot_urls=[f"/{str(path).replace(chr(92), '/')}" for path in run.screenshot_paths],
            failure_category=run.failure_category,
            latency_ms=run.latency_ms,
        )
        for run in runs
    ]


def fail_stale_execution_runs(db: Session, session_id: str | None = None, stale_after_seconds: int = 60) -> None:
    cutoff = datetime.utcnow() - timedelta(seconds=stale_after_seconds)
    query = db.query(ExecutionRun).filter(
        ExecutionRun.status.in_(["created", "running", "paused"]),
        ExecutionRun.updated_at < cutoff,
    )
    if session_id:
        query = query.filter_by(session_id=session_id)
    stale_runs = query.all()
    if not stale_runs:
        return

    for run in stale_runs:
        steps = list(run.steps or [])
        if steps:
            last_step = dict(steps[-1])
            if last_step.get("status") not in {"confirmed", "ok", "failed", "timeout"}:
                last_step["status"] = "timeout"
                steps[-1] = last_step
        else:
            steps = [{"action": "execution", "status": "timeout"}]
        run.status = "failed"
        run.steps = steps
        run.failure_category = "timeout"
        run.updated_at = datetime.utcnow()

    db.commit()
