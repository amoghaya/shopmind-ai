from dataclasses import dataclass


@dataclass
class ExpertDecision:
    expert_name: str
    score: float
    confidence: float

