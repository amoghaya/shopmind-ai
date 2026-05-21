from dataclasses import dataclass, field

from ml.recommenders.schemas import ExpertDecision


@dataclass
class HNBAggregator:
    weights: dict[str, float] = field(
        default_factory=lambda: {
            "thompson_sampling": 0.45,
            "linucb": 0.35,
            "epsilon_greedy": 0.20,
        }
    )
    bias: float = 0.0
    learning_rate: float = 0.08

    def combine(self, decisions: list[ExpertDecision]) -> tuple[float, dict]:
        weighted_scores = {}
        total = self.bias
        for decision in decisions:
            weight = self.weights.get(decision.expert_name, 0.0)
            contribution = weight * decision.score
            weighted_scores[decision.expert_name] = round(contribution, 4)
            total += contribution
        return total, weighted_scores

    def update(self, expert_votes: dict, reward: float) -> dict[str, float]:
        direction = 1.0 if reward > 0 else -1.0
        for expert_name, contribution in expert_votes.items():
            self.weights[expert_name] = max(
                0.05,
                self.weights.get(expert_name, 0.1) + self.learning_rate * direction * float(contribution),
            )
        total = sum(self.weights.values()) or 1.0
        self.weights = {name: round(weight / total, 6) for name, weight in self.weights.items()}
        return self.weights
