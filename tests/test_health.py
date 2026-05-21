from tests.conftest import make_client


def test_health():
    with make_client() as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
