from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.deps import db_session
from backend.schemas.preferences import PreferenceRead, PreferenceUpsert
from backend.services.preferences import get_preferences, upsert_preferences

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.post("", response_model=PreferenceRead)
def save_preferences(payload: PreferenceUpsert, db: Session = Depends(db_session)):
    profile = upsert_preferences(db, payload)
    return PreferenceRead(
        user_id=profile.user_id,
        context_features=profile.context_features,
        preference_summary=profile.preference_summary,
    )


@router.get("/{user_id}", response_model=PreferenceRead)
def fetch_preferences(user_id: str, db: Session = Depends(db_session)):
    profile = get_preferences(db, user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="profile not found")
    return PreferenceRead(
        user_id=profile.user_id,
        context_features=profile.context_features,
        preference_summary=profile.preference_summary,
    )

