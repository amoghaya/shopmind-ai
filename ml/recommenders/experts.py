import random

import numpy as np

from ml.recommenders.schemas import ExpertDecision


class ThompsonSamplingExpert:
    name = "thompson_sampling"

    def score(self, state, context_vector: np.ndarray) -> ExpertDecision:
        sample = random.betavariate(max(state.ts_alpha, 1e-3), max(state.ts_beta, 1e-3))
        contextual_bonus = float(0.15 * context_vector[1] + 0.1 * context_vector[2] + 0.1 * context_vector[3])
        return ExpertDecision(self.name, sample + contextual_bonus, sample)


class LinUCBExpert:
    name = "linucb"

    def __init__(self, alpha: float = 0.8) -> None:
        self.alpha = alpha

    def score(self, state, context_vector: np.ndarray) -> ExpertDecision:
        a = np.array(state.linucb_a, dtype=float)
        b = np.array(state.linucb_b, dtype=float)
        a_inv = np.linalg.inv(a)
        theta = a_inv @ b
        mean = float(theta.T @ context_vector)
        bonus = float(self.alpha * np.sqrt(context_vector.T @ a_inv @ context_vector))
        return ExpertDecision(self.name, mean + bonus, bonus)


class EpsilonGreedyExpert:
    name = "epsilon_greedy"

    def __init__(self, epsilon: float = 0.15) -> None:
        self.epsilon = epsilon

    def score(self, state, context_vector: np.ndarray) -> ExpertDecision:
        avg_reward = state.cumulative_reward / state.pulls if state.pulls else 0.5
        exploration = random.random() if random.random() < self.epsilon else 0.0
        contextual_bonus = float(0.1 * context_vector[1] + 0.05 * context_vector[2])
        return ExpertDecision(self.name, avg_reward + exploration + contextual_bonus, 1.0 - self.epsilon)
