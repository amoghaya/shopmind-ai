from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import numpy as np
from sqlalchemy.orm import Session

from backend.core.metrics import REGRET_GAUGE
from backend.db.models import BanditArmState, Product, RecommendationEvent, RecommenderState
from backend.schemas.recommendations import (
    RecommendationFeedback,
    RecommendationItem,
    RecommendationResponse,
)
from ml.recommenders.experts import EpsilonGreedyExpert, LinUCBExpert, ThompsonSamplingExpert
from ml.recommenders.hnb import HNBAggregator


class RecommendationService:
    def __init__(self) -> None:
        self.experts = [
            ThompsonSamplingExpert(),
            LinUCBExpert(),
            EpsilonGreedyExpert(),
        ]

    def rank(
        self,
        db: Session,
        user_id: str,
        top_k: int,
        context_overrides: dict,
    ) -> RecommendationResponse:
        products = db.query(Product).filter(Product.inventory_count > 0).all()
        recommender_state = self._ensure_recommender_state(db)
        aggregator = HNBAggregator(weights=dict(recommender_state.weights), bias=recommender_state.bias)
        context = self._build_context(context_overrides)

        ranked: list[tuple[float, RecommendationItem]] = []
        for product in products:
            arm_state = self._ensure_arm_state(db, product.id)
            context_vector = self._context_vector(product, context)
            decisions = [expert.score(arm_state, context_vector) for expert in self.experts]
            total_score, expert_votes = aggregator.combine(decisions)
            ranked.append(
                (
                    total_score,
                    RecommendationItem(
                        item_id=str(product.id),
                        score=round(total_score, 4),
                        expert_votes=expert_votes,
                        explanation={
                            "category_match": product.category == context["preferred_category"],
                            "budget_fit": product.price <= context["budget_max"],
                            "rating_fit": product.rating_avg >= context.get("min_rating", 0.0),
                            "rating": product.rating_avg,
                            "brand": product.brand,
                        },
                    ),
                )
            )

        ranked.sort(key=lambda item: item[0], reverse=True)
        request_id = f"rec-{uuid4().hex[:12]}"
        best_score = ranked[0][0] if ranked else 0.0
        selected_item = ranked[0][1] if ranked else None
        db.add(
            RecommendationEvent(
                user_id=user_id,
                request_id=request_id,
                strategy="hnb_live",
                selected_item_id=selected_item.item_id if selected_item else "none",
                reward=None,
                context=context,
                top_k=[
                    {
                        "item_id": item.item_id,
                        "score": item.score,
                        "expert_votes": item.expert_votes,
                        "explanation": item.explanation,
                    }
                    for _, item in ranked[:top_k]
                ],
                selected_score=selected_item.score if selected_item else 0.0,
                best_score=best_score,
                regret=0.0,
                explanation=selected_item.explanation if selected_item else {},
            )
        )
        db.commit()
        return RecommendationResponse(
            request_id=request_id,
            strategy="hnb_live",
            items=[item for _, item in ranked[:top_k]],
        )

    def apply_feedback(self, db: Session, payload: RecommendationFeedback) -> dict:
        event = db.query(RecommendationEvent).filter_by(request_id=payload.request_id).one()
        recommender_state = self._ensure_recommender_state(db)
        aggregator = HNBAggregator(weights=dict(recommender_state.weights), bias=recommender_state.bias)

        top_k = event.top_k or []
        selected = next((item for item in top_k if item["item_id"] == payload.selected_item_id), None)
        if selected is None:
            selected = next((item for item in top_k if item["item_id"] == event.selected_item_id), None)
        if selected is None:
            return {"status": "ignored", "reason": "selected item not found"}

        reward = float(payload.reward)
        event.selected_item_id = selected["item_id"]
        event.reward = reward
        event.selected_score = float(selected["score"])
        event.best_score = max((float(item["score"]) for item in top_k), default=float(selected["score"]))
        event.regret = max(0.0, event.best_score - (reward * event.selected_score))
        recommender_state.cumulative_regret += event.regret
        recommender_state.total_feedback += 1
        if reward > 0:
            recommender_state.successful_feedback += 1
        REGRET_GAUGE.set(recommender_state.cumulative_regret)

        arm_state = self._ensure_arm_state(db, int(selected["item_id"]))
        arm_state.pulls += 1
        arm_state.successes += 1 if reward > 0 else 0
        arm_state.cumulative_reward += reward
        arm_state.ts_alpha += reward
        arm_state.ts_beta += 1.0 - reward

        context_vector = self._context_vector_from_event(event, selected)
        a = np.array(arm_state.linucb_a, dtype=float)
        b = np.array(arm_state.linucb_b, dtype=float)
        a = a + np.outer(context_vector, context_vector)
        b = b + reward * context_vector
        arm_state.linucb_a = a.tolist()
        arm_state.linucb_b = b.tolist()
        arm_state.updated_at = datetime.utcnow()

        recommender_state.weights = aggregator.update(selected["expert_votes"], reward)
        recommender_state.bias = aggregator.bias
        recommender_state.updated_at = datetime.utcnow()
        db.commit()
        return {
            "status": "updated",
            "weights": recommender_state.weights,
            "cumulative_regret": recommender_state.cumulative_regret,
        }

    def get_summary(self, db: Session) -> dict:
        state = self._ensure_recommender_state(db)
        success_rate = (
            state.successful_feedback / state.total_feedback if state.total_feedback else 0.0
        )
        return {
            "weights": state.weights,
            "cumulative_regret": state.cumulative_regret,
            "total_feedback": state.total_feedback,
            "success_rate": round(success_rate, 4),
        }

    def _ensure_recommender_state(self, db: Session) -> RecommenderState:
        state = db.query(RecommenderState).filter_by(state_key="global").one_or_none()
        if state is None:
            state = RecommenderState(
                state_key="global",
                weights={
                    "thompson_sampling": 0.45,
                    "linucb": 0.35,
                    "epsilon_greedy": 0.20,
                },
                bias=0.0,
            )
            db.add(state)
            db.commit()
            db.refresh(state)
        return state

    def _ensure_arm_state(self, db: Session, product_id: int) -> BanditArmState:
        state = db.query(BanditArmState).filter_by(product_id=product_id).one_or_none()
        dim = 6
        if state is None:
            state = BanditArmState(
                product_id=product_id,
                linucb_a=np.eye(dim).tolist(),
                linucb_b=np.zeros(dim).tolist(),
            )
            db.add(state)
            db.commit()
            db.refresh(state)
        else:
            a = np.array(state.linucb_a, dtype=float)
            b = np.array(state.linucb_b, dtype=float)
            if a.shape != (dim, dim) or b.shape != (dim,):
                state.linucb_a = np.eye(dim).tolist()
                state.linucb_b = np.zeros(dim).tolist()
                db.commit()
                db.refresh(state)
        return state

    def _build_context(self, context_overrides: dict) -> dict:
        return {
            "preferred_category": context_overrides.get("preferred_category"),
            "budget_max": float(context_overrides.get("budget_max", 60000)),
            "preferred_brand": context_overrides.get("preferred_brand"),
            "min_rating": float(context_overrides.get("min_rating", 0.0)),
        }

    def _context_vector(self, product: Product, context: dict) -> np.ndarray:
        category_match = 1.0 if context.get("preferred_category") == product.category else 0.0
        budget_fit = 1.0 if product.price <= context["budget_max"] else 0.0
        rating_fit = 1.0 if product.rating_avg >= context.get("min_rating", 0.0) else 0.0
        rating_norm = min(product.rating_avg / 5.0, 1.0)
        price_norm = min(product.price / max(context["budget_max"], 1.0), 2.0)
        stock_norm = min(product.inventory_count / 50.0, 1.0)
        return np.array(
            [category_match, budget_fit, rating_fit, rating_norm, 1.0 - min(price_norm, 1.0), stock_norm]
        )

    def _context_vector_from_event(self, event: RecommendationEvent, selected: dict) -> np.ndarray:
        explanation = selected.get("explanation", {})
        return np.array(
            [
                1.0 if explanation.get("category_match") else 0.0,
                1.0 if explanation.get("budget_fit") else 0.0,
                1.0 if explanation.get("rating_fit") else 0.0,
                min(float(explanation.get("rating", 0.0)) / 5.0, 1.0),
                1.0 - min(float(selected.get("score", 0.0)) / 3.0, 1.0),
                0.5,
            ]
        )
