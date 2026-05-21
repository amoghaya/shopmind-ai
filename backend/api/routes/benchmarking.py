from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.api.deps import db_session
from backend.services.demo_benchmark import run_demo_benchmark

router = APIRouter(prefix="/benchmark", tags=["benchmark"])


@router.post("/demo")
def demo_benchmark(db: Session = Depends(db_session)):
    return run_demo_benchmark(db)
