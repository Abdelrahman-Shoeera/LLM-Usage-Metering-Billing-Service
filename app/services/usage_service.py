from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from datetime import datetime, timezone

from app.models.models import UsageEvent, Subscription, Plan, Tenant


def get_current_usage(db: Session, tenant_id: str, event_type: str) -> int:
    now = datetime.now(timezone.utc)
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    result = db.query(func.coalesce(func.sum(UsageEvent.quantity), 0)).filter(
        UsageEvent.tenant_id == tenant_id,
        UsageEvent.event_type == event_type,
        UsageEvent.created_at >= first_of_month,
    ).scalar()

    return result


def get_tenant_subscription(db: Session, tenant_id: str):
    subscription = db.query(Subscription).filter(
        Subscription.tenant_id == tenant_id,
        Subscription.status == "active",
    ).first()

    return subscription


def record_usage(db: Session, tenant_id: str, event_type: str,
                 quantity: int, idempotency_key: str, metadata: dict = None):

    existing = db.query(UsageEvent).filter(
        UsageEvent.idempotency_key == idempotency_key,
    ).first()

    if existing:
        return existing, False

    subscription = get_tenant_subscription(db, tenant_id)
    if not subscription:
        return None, "no_subscription"

    plan = subscription.plan

    current_usage = get_current_usage(db, tenant_id, event_type)

    if event_type == "api_call":
        limit = plan.api_call_limit
    else:
        limit = plan.token_limit

    if current_usage + quantity > limit:
        return None, "quota_exceeded"

    new_event = UsageEvent(
        tenant_id=tenant_id,
        event_type=event_type,
        quantity=quantity,
        idempotency_key=idempotency_key,
        metadata_=metadata,
    )

    try:
        db.add(new_event)
        db.commit()
        db.refresh(new_event)
        return new_event, True
    except IntegrityError:
        db.rollback()
        existing = db.query(UsageEvent).filter(
            UsageEvent.idempotency_key == idempotency_key,
        ).first()
        return existing, False