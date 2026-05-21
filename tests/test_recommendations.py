from backend.db.session import SessionLocal
from backend.services.recommendations import recommendation_service


def test_recommendations_are_ranked():
    with SessionLocal() as db:
        response = recommendation_service.rank(
            db,
            "u1",
            3,
            {"preferred_category": "laptop", "budget_max": 60000},
        )
        assert response.strategy == "hnb_live"
        assert response.request_id is not None
        assert len(response.items) == 3
        assert response.items[0].score >= response.items[1].score
