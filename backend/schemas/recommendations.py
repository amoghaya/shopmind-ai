from pydantic import BaseModel, Field


class RecommendationRequest(BaseModel):
    user_id: str
    top_k: int = 5
    context_overrides: dict = Field(default_factory=dict)


class RecommendationItem(BaseModel):
    item_id: str
    score: float
    expert_votes: dict
    explanation: dict


class RecommendationResponse(BaseModel):
    request_id: str | None = None
    strategy: str
    items: list[RecommendationItem]


class RecommendationFeedback(BaseModel):
    request_id: str
    user_id: str
    selected_item_id: str
    reward: float
    accepted: bool = True
