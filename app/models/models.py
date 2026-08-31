import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.database import Base


def generate_uuid():
    return str(uuid.uuid4())


def utc_now():
    return datetime.now(timezone.utc)


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    subscriptions = relationship("Subscription", back_populates="tenant")
    usage_events = relationship("UsageEvent", back_populates="tenant")


class Plan(Base):
    __tablename__ = "plans"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False, unique=True)
    api_call_limit = Column(Integer, nullable=False)
    token_limit = Column(Integer, nullable=False)

    subscriptions = relationship("Subscription", back_populates="plan")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    plan_id = Column(String, ForeignKey("plans.id"), nullable=False)
    status = Column(String, nullable=False, default="active")
    stripe_subscription_id = Column(String, nullable=True, unique=True)
    stripe_customer_id = Column(String, nullable=True)
    current_period_start = Column(DateTime, default=utc_now)
    current_period_end = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    tenant = relationship("Tenant", back_populates="subscriptions")
    plan = relationship("Plan", back_populates="subscriptions")


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    event_type = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    idempotency_key = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, default=utc_now)
    metadata_ = Column("metadata", JSON, nullable=True)

    tenant = relationship("Tenant", back_populates="usage_events")


class ProcessedWebhookEvent(Base):
    __tablename__ = "processed_webhook_events"

    id = Column(String, primary_key=True, default=generate_uuid)
    stripe_event_id = Column(String, nullable=False, unique=True)
    event_type = Column(String, nullable=False)
    processed_at = Column(DateTime, default=utc_now)