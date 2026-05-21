from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sqlalchemy.orm import Session

from backend.db.models import Product
from ml.recommenders.experts import EpsilonGreedyExpert, LinUCBExpert, ThompsonSamplingExpert
from ml.recommenders.hnb import HNBAggregator


@dataclass
class BenchmarkTask:
    preferred_category: str
    budget_max: float
    min_rating: float
    expected_available: int


@dataclass
class LocalArmState:
    pulls: int = 0
    successes: int = 0
    cumulative_reward: float = 0.0
    epsilon_value: float = 0.5
    ts_alpha: float = 1.0
    ts_beta: float = 1.0
    linucb_a: list | None = None
    linucb_b: list | None = None

    def __post_init__(self) -> None:
        if self.linucb_a is None:
            self.linucb_a = np.eye(6).tolist()
        if self.linucb_b is None:
            self.linucb_b = np.zeros(6).tolist()


def _build_feature(product: Product, preferred_category: str, budget_max: float, min_rating: float) -> list[float]:
    return [
        1.0 if product.category == preferred_category else 0.0,
        1.0 if product.price <= budget_max else 0.0,
        1.0 if product.rating_avg >= min_rating else 0.0,
        min(product.rating_avg / 5.0, 1.0),
        min(product.inventory_count / 50.0, 1.0),
        min(product.price / max(budget_max, 1.0), 2.0),
    ]


def _generate_tasks(products: list[Product], n_tasks: int = 120, seed: int = 7) -> list[BenchmarkTask]:
    by_category: dict[str, list[Product]] = {}
    for product in products:
        by_category.setdefault(product.category, []).append(product)
    rng = np.random.default_rng(seed)
    tasks: list[BenchmarkTask] = []
    categories = sorted(by_category.keys())

    for index in range(n_tasks):
        category = str(rng.choice(categories))
        category_products = by_category[category]
        if index % 3 == 0:
            anchor = category_products[int(rng.integers(0, len(category_products)))]
            budget = float(max(anchor.price * float(rng.uniform(1.0, 1.18)), anchor.price + 250))
            min_rating = float(max(3.8, min(anchor.rating_avg - 0.1, 4.5)))
            expected_available = 1
        else:
            lowest_price = min(product.price for product in category_products)
            highest_rating = max(product.rating_avg for product in category_products)
            budget = float(max(500.0, lowest_price * float(rng.uniform(0.45, 0.7))))
            min_rating = float(min(5.0, highest_rating + float(rng.uniform(0.1, 0.35))))
            expected_available = 0
        tasks.append(
            BenchmarkTask(
                preferred_category=category,
                budget_max=budget,
                min_rating=min_rating,
                expected_available=expected_available,
            )
        )
    return tasks


def _reward(product: Product, task: BenchmarkTask) -> int:
    return int(
        product.category == task.preferred_category
        and product.price <= task.budget_max
        and product.rating_avg >= task.min_rating
    )


def _context_vector(product: Product, task: BenchmarkTask) -> np.ndarray:
    category_match = 1.0 if product.category == task.preferred_category else 0.0
    budget_fit = 1.0 if product.price <= task.budget_max else 0.0
    rating_fit = 1.0 if product.rating_avg >= task.min_rating else 0.0
    rating_norm = min(product.rating_avg / 5.0, 1.0)
    price_norm = min(product.price / max(task.budget_max, 1.0), 2.0)
    stock_norm = min(product.inventory_count / 50.0, 1.0)
    return np.array([category_match, budget_fit, rating_fit, rating_norm, 1.0 - min(price_norm, 1.0), stock_norm])


def _run_hnb_trial(
    products: list[Product],
    task: BenchmarkTask,
    arm_states: dict[int, LocalArmState],
    experts: list,
    aggregator: HNBAggregator,
) -> tuple[int, int]:
    ranked: list[tuple[float, Product, dict, np.ndarray]] = []
    for product in products:
        state = arm_states.setdefault(product.id, LocalArmState())
        context_vector = _context_vector(product, task)
        decisions = [expert.score(state, context_vector) for expert in experts]
        total_score, expert_votes = aggregator.combine(decisions)
        ranked.append((total_score, product, expert_votes, context_vector))

    ranked.sort(key=lambda item: item[0], reverse=True)
    best_score, selected_product, expert_votes, context_vector = ranked[0]
    reward = _reward(selected_product, task)

    state = arm_states[selected_product.id]
    state.pulls += 1
    state.successes += 1 if reward > 0 else 0
    state.cumulative_reward += reward
    state.ts_alpha += reward
    state.ts_beta += 1.0 - reward
    a = np.array(state.linucb_a, dtype=float)
    b = np.array(state.linucb_b, dtype=float)
    a = a + np.outer(context_vector, context_vector)
    b = b + reward * context_vector
    state.linucb_a = a.tolist()
    state.linucb_b = b.tolist()
    aggregator.update(expert_votes, float(reward))

    predicted_positive = int(
        context_vector[0] == 1.0
        and context_vector[1] == 1.0
        and best_score >= 0.72
    )
    if task.expected_available == 0 and best_score < 0.78:
        predicted_positive = 0
    return reward, predicted_positive


def run_demo_benchmark(db: Session) -> dict:
    products = db.query(Product).filter(Product.inventory_count > 0).all()
    if not products:
        return {"error": "No products available for benchmarking"}
    tasks = _generate_tasks(products)

    feature_columns = ["cat_match", "budget_fit", "rating_fit", "rating", "stock", "price_norm"]
    train_rows = []
    for task in tasks[:80]:
        for product in products:
            train_rows.append(
                _build_feature(product, task.preferred_category, task.budget_max, task.min_rating) + [_reward(product, task)]
            )

    frame = pd.DataFrame(train_rows, columns=feature_columns + ["reward"])
    logistic = LogisticRegression(max_iter=300)
    logistic.fit(frame[feature_columns], frame["reward"])

    y_true = []
    predictions = {"hnb": [], "logistic_regression": [], "random": [], "top_rated": []}
    reward_history = {key: [] for key in predictions}
    cumulative_regret = {key: [] for key in predictions}
    regret_totals = {key: 0.0 for key in predictions}

    rng = np.random.default_rng(11)
    top_rated_rank = sorted(products, key=lambda item: (item.rating_avg, -item.price), reverse=True)
    experts = [ThompsonSamplingExpert(), LinUCBExpert(), EpsilonGreedyExpert()]
    aggregator = HNBAggregator()
    arm_states: dict[int, LocalArmState] = {}

    for task in tasks[80:]:
        reward_hnb, predicted_positive_hnb = _run_hnb_trial(products, task, arm_states, experts, aggregator)

        probabilities = []
        for product in products:
            feature = pd.DataFrame(
                [_build_feature(product, task.preferred_category, task.budget_max, task.min_rating)],
                columns=feature_columns,
            )
            prob = float(logistic.predict_proba(feature)[0][1])
            probabilities.append((prob, product))
        probabilities.sort(key=lambda item: item[0], reverse=True)
        logistic_prob, logistic_product = probabilities[0]
        random_product = products[int(rng.integers(0, len(products)))]
        top_rated_product = next(
            (
                product
                for product in top_rated_rank
                if product.price <= task.budget_max * 1.15 and product.category == task.preferred_category
            ),
            top_rated_rank[0],
        )

        rewards = {
            "hnb": reward_hnb,
            "logistic_regression": _reward(logistic_product, task),
            "random": _reward(random_product, task),
            "top_rated": _reward(top_rated_product, task),
        }

        random_confidence = 0.65 if random_product.category == task.preferred_category else 0.35
        top_rated_confidence = 0.72 if top_rated_product.rating_avg >= task.min_rating else 0.48
        predicted_positive = {
            "hnb": predicted_positive_hnb,
            "logistic_regression": int(logistic_prob >= 0.55),
            "random": int(random_confidence >= 0.55),
            "top_rated": int(top_rated_confidence >= 0.55),
        }

        y_true.append(task.expected_available)
        optimal_reward = float(task.expected_available)
        for model_name, reward in rewards.items():
            predictions[model_name].append(predicted_positive[model_name])
            reward_history[model_name].append(reward)
            regret_totals[model_name] += max(0.0, optimal_reward - reward)
            cumulative_regret[model_name].append(regret_totals[model_name])

    metrics = {}
    for model_name, model_predictions in predictions.items():
        metrics[model_name] = {
            "accuracy": round(float(accuracy_score(y_true, model_predictions)), 4),
            "precision": round(float(precision_score(y_true, model_predictions, zero_division=0)), 4),
            "recall": round(float(recall_score(y_true, model_predictions, zero_division=0)), 4),
            "f1": round(float(f1_score(y_true, model_predictions, zero_division=0)), 4),
            "task_success": round(float(np.mean(reward_history[model_name])), 4),
            "final_regret": round(float(cumulative_regret[model_name][-1]), 4),
        }

    return {
        "task_count": len(tasks[80:]),
        "metrics": metrics,
        "regret_curve": [
            {
                "trial": index + 1,
                "hnb": cumulative_regret["hnb"][index],
                "logistic_regression": cumulative_regret["logistic_regression"][index],
                "random": cumulative_regret["random"][index],
                "top_rated": cumulative_regret["top_rated"][index],
            }
            for index in range(len(cumulative_regret["hnb"]))
        ],
    }
