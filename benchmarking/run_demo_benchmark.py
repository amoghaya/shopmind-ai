from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import warnings

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
matplotlib.use("Agg")
warnings.filterwarnings("ignore", category=UserWarning)

from backend.db.base import Base
from backend.db.models import Product
from backend.db.session import SessionLocal, engine
from backend.schemas.recommendations import RecommendationFeedback
from backend.services.ecommerce_seed import seed_mock_shop
from backend.services.recommendations import recommendation_service


def build_feature(product: Product, preferred_category: str, budget_max: float) -> list[float]:
    return [
        1.0 if product.category == preferred_category else 0.0,
        1.0 if product.price <= budget_max else 0.0,
        min(product.rating_avg / 5.0, 1.0),
        min(product.inventory_count / 50.0, 1.0),
        min(product.price / max(budget_max, 1.0), 2.0),
    ]


def main() -> None:
    categories = ["laptop", "phone", "home", "fashion", "audio"]
    tasks = []
    rng = np.random.default_rng(7)
    for _ in range(120):
        category = rng.choice(categories)
        budget = float(rng.integers(4000, 65000))
        tasks.append({"preferred_category": category, "budget_max": budget})

    with TemporaryDirectory() as tmpdir:
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            seed_mock_shop(db)
            products = db.query(Product).all()
            feature_columns = ["cat_match", "budget_fit", "rating", "stock", "price_norm"]

            train_rows = []
            for task in tasks[:80]:
                for product in products:
                    reward = int(product.category == task["preferred_category"] and product.price <= task["budget_max"])
                    train_rows.append(build_feature(product, task["preferred_category"], task["budget_max"]) + [reward])

            frame = pd.DataFrame(train_rows, columns=feature_columns + ["reward"])
            model = LogisticRegression(max_iter=300)
            model.fit(frame[feature_columns], frame["reward"])

            y_true = []
            y_pred_hnb = []
            y_pred_lr = []
            cumulative_regret_hnb = []
            cumulative_regret_lr = []
            regret_hnb = 0.0
            regret_lr = 0.0

            for task in tasks[80:]:
                response = recommendation_service.rank(
                    db,
                    "benchmark-user",
                    3,
                    {
                        "preferred_category": task["preferred_category"],
                        "budget_max": task["budget_max"],
                    },
                )
                selected = response.items[0]
                selected_product = next(product for product in products if str(product.id) == selected.item_id)
                reward_hnb = int(
                    selected_product.category == task["preferred_category"]
                    and selected_product.price <= task["budget_max"]
                )
                recommendation_service.apply_feedback(
                    db,
                    RecommendationFeedback(
                        request_id=response.request_id,
                        user_id="benchmark-user",
                        selected_item_id=selected.item_id,
                        reward=reward_hnb,
                        accepted=bool(reward_hnb),
                    ),
                )

                probabilities = []
                for product in products:
                    feature = pd.DataFrame(
                        [build_feature(product, task["preferred_category"], task["budget_max"])],
                        columns=feature_columns,
                    )
                    prob = model.predict_proba(feature)[0][1]
                    probabilities.append((prob, product))
                probabilities.sort(key=lambda item: item[0], reverse=True)
                logistic_product = probabilities[0][1]
                reward_lr = int(
                    logistic_product.category == task["preferred_category"]
                    and logistic_product.price <= task["budget_max"]
                )

                y_true.append(1)
                y_pred_hnb.append(reward_hnb)
                y_pred_lr.append(reward_lr)
                regret_hnb += 1 - reward_hnb
                regret_lr += 1 - reward_lr
                cumulative_regret_hnb.append(regret_hnb)
                cumulative_regret_lr.append(regret_lr)

        metrics = {
            "hnb": {
                "accuracy": accuracy_score(y_true, y_pred_hnb),
                "precision": precision_score(y_true, y_pred_hnb, zero_division=0),
                "recall": recall_score(y_true, y_pred_hnb, zero_division=0),
                "f1": f1_score(y_true, y_pred_hnb, zero_division=0),
            },
            "logistic_regression": {
                "accuracy": accuracy_score(y_true, y_pred_lr),
                "precision": precision_score(y_true, y_pred_lr, zero_division=0),
                "recall": recall_score(y_true, y_pred_lr, zero_division=0),
                "f1": f1_score(y_true, y_pred_lr, zero_division=0),
            },
        }

        output_dir = Path("artifacts/benchmarks")
        output_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(
            {
                "trial": list(range(1, len(cumulative_regret_hnb) + 1)),
                "hnb_regret": cumulative_regret_hnb,
                "logistic_regret": cumulative_regret_lr,
            }
        ).to_csv(output_dir / "demo_regret_curve.csv", index=False)

        plt.figure(figsize=(8, 4.5))
        plt.plot(cumulative_regret_hnb, label="HNB")
        plt.plot(cumulative_regret_lr, label="Logistic Regression")
        plt.xlabel("Trial")
        plt.ylabel("Cumulative Regret")
        plt.title("Demo Benchmark Regret")
        plt.legend()
        plt.tight_layout()
        plt.savefig(output_dir / "demo_regret_curve.png")

        pd.DataFrame(metrics).T.to_csv(output_dir / "demo_metrics.csv")
        print(pd.DataFrame(metrics).T.to_string())


if __name__ == "__main__":
    main()
