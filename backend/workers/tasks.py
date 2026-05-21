from celery.utils.log import get_task_logger

from backend.workers.celery_app import celery_app

task_logger = get_task_logger(__name__)


@celery_app.task(name="price_tracking.run")
def run_price_tracking_task(product_ids: list[str]) -> dict:
    task_logger.info("price_tracking.start", product_count=len(product_ids))
    return {
        "status": "completed",
        "tracked_products": product_ids,
        "alerts": [],
    }

