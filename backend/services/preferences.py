from sqlalchemy.orm import Session

from backend.db.models import UserPreferenceProfile
from backend.schemas.preferences import PreferenceUpsert


DEFAULT_PREFERENCE_SUMMARY = {
    "user_name": "Demo User",
    "preferred_categories": [],
    "preferred_brands": [],
    "budget_max": 70000,
    "liked_tags": [],
    "disliked_tags": [],
    "watchlist_product_ids": [],
}


def upsert_preferences(db: Session, payload: PreferenceUpsert) -> UserPreferenceProfile:
    profile = db.query(UserPreferenceProfile).filter_by(user_id=payload.user_id).one_or_none()
    if profile is None:
        profile = UserPreferenceProfile(user_id=payload.user_id)
        db.add(profile)
    merged_context = {**(profile.context_features or {}), **payload.context_features}
    merged_summary = {**DEFAULT_PREFERENCE_SUMMARY, **(profile.preference_summary or {}), **payload.preference_summary}
    profile.context_features = merged_context
    profile.preference_summary = merged_summary
    db.commit()
    db.refresh(profile)
    return profile


def get_preferences(db: Session, user_id: str) -> UserPreferenceProfile | None:
    profile = db.query(UserPreferenceProfile).filter_by(user_id=user_id).one_or_none()
    if profile is None:
        profile = UserPreferenceProfile(
            user_id=user_id,
            context_features={},
            preference_summary=dict(DEFAULT_PREFERENCE_SUMMARY),
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    else:
        profile.preference_summary = {**DEFAULT_PREFERENCE_SUMMARY, **(profile.preference_summary or {})}
        db.commit()
        db.refresh(profile)
    return profile
