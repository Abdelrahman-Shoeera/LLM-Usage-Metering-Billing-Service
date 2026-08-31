import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models.models import Tenant, Plan, Subscription


TEST_DATABASE_URL = "postgresql://postgres:postgres@db:5432/test_billing"


@pytest.fixture(scope="function")
def db_session():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def seeded_data(db_session):
    free_plan = Plan(name="free", api_call_limit=1000, token_limit=100_000)
    pro_plan = Plan(name="pro", api_call_limit=50_000, token_limit=5_000_000)
    db_session.add(free_plan)
    db_session.add(pro_plan)

    tenant = Tenant(name="Test Tenant")
    db_session.add(tenant)
    db_session.flush()

    subscription = Subscription(
        tenant_id=tenant.id,
        plan_id=free_plan.id,
        status="active",
    )
    db_session.add(subscription)
    db_session.commit()

    return {
        "tenant": tenant,
        "free_plan": free_plan,
        "pro_plan": pro_plan,
        "subscription": subscription,
    }