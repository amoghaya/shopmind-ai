from fastapi.testclient import TestClient

from backend.db.base import Base
from backend.db.session import SessionLocal, engine
from backend.main import app
from backend.services.ecommerce_seed import seed_mock_shop


def pytest_configure():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_mock_shop(db)


def make_client() -> TestClient:
    return TestClient(app)
