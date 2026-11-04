import os

os.environ.setdefault("SECRET_KEY", "chave-de-teste-chave-de-teste-chave-de-teste")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db, make_engine
from app.main import app
from app.seed import DEMO_PASSWORD, seed


@pytest.fixture()
def Session():
    engine = make_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with maker() as s:
        seed(s)
    yield maker
    engine.dispose()


@pytest.fixture()
def client(Session):
    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def auth(client):
    """auth("ana") -> headers Authorization para o usuário seed."""
    def _auth(first_name: str):
        r = client.post("/auth/login", json={"email": f"{first_name}@nexuscorp.com",
                                             "password": DEMO_PASSWORD})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}
    return _auth
