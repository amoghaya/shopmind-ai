from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.api.deps import db_session
from backend.core.metrics import RECOMMENDATION_COUNT
from backend.schemas.recommendations import (
    RecommendationFeedback,
    RecommendationRequest,
    RecommendationResponse,
)
from backend.services.recommendations import recommendation_service

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post("", response_model=RecommendationResponse)
def rank_products(payload: RecommendationRequest, db: Session = Depends(db_session)):
    response = recommendation_service.rank(db, payload.user_id, payload.top_k, payload.context_overrides)
    RECOMMENDATION_COUNT.labels(strategy=response.strategy).inc()
    return response


@router.get("/mock", response_model=RecommendationResponse)
def mock_recommendations(db: Session = Depends(db_session)):
    response = recommendation_service.rank(db, "demo-user", 5, {"preferred_category": "laptop"})
    RECOMMENDATION_COUNT.labels(strategy=response.strategy).inc()
    return response


@router.post("/feedback")
def recommendation_feedback(payload: RecommendationFeedback, db: Session = Depends(db_session)):
    return recommendation_service.apply_feedback(db, payload)


@router.get("/summary")
def recommendation_summary(db: Session = Depends(db_session)):
    return recommendation_service.get_summary(db)
