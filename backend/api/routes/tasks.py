from fastapi import APIRouter

from backend.workers.tasks import run_price_tracking_task

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/price-tracking")
def launch_price_tracking(product_ids: list[str]):
    task = run_price_tracking_task.delay(product_ids)
    return {"task_id": task.id, "status": "queued"}

