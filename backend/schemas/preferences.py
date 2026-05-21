from pydantic import BaseModel, Field


class PreferenceUpsert(BaseModel):
    user_id: str
    context_features: dict = Field(default_factory=dict)
    preference_summary: dict = Field(default_factory=dict)


class PreferenceRead(PreferenceUpsert):
    pass

