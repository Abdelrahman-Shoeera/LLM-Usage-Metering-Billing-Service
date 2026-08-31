import stripe
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.models.models import Subscription, Plan, Tenant, ProcessedWebhookEvent

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_checkout_session(db: Session, tenant_id: str, plan_name: str) -> str:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise ValueError("Tenant not found")

    plan = db.query(Plan).filter(Plan.name == plan_name).first()
    if not plan:
        raise ValueError(f"Plan '{plan_name}' not found")

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="subscription",
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": f"{plan_name.title()} Plan",
                },
                "unit_amount": 2999,
                "recurring": {
                    "interval": "month",
                },
            },
            "quantity": 1,
        }],
        metadata={
            "tenant_id": tenant_id,
            "plan_name": plan_name,
        },
        success_url="http://localhost:8000/health?checkout=success",
        cancel_url="http://localhost:8000/health?checkout=canceled",
    )

    return session.url


def is_event_processed(db: Session, stripe_event_id: str) -> bool:
    existing = db.query(ProcessedWebhookEvent).filter(
        ProcessedWebhookEvent.stripe_event_id == stripe_event_id,
    ).first()
    return existing is not None


def mark_event_processed(db: Session, stripe_event_id: str, event_type: str):
    record = ProcessedWebhookEvent(
        stripe_event_id=stripe_event_id,
        event_type=event_type,
    )
    try:
        db.add(record)
        db.commit()
    except IntegrityError:
        db.rollback()


def handle_checkout_completed(db: Session, event_data: dict):
    tenant_id = event_data["metadata"]["tenant_id"]
    plan_name = event_data["metadata"]["plan_name"]
    stripe_customer_id = event_data.get("customer")
    stripe_subscription_id = event_data.get("subscription")

    plan = db.query(Plan).filter(Plan.name == plan_name).first()
    if not plan:
        return

    subscription = db.query(Subscription).filter(
        Subscription.tenant_id == tenant_id,
        Subscription.status == "active",
    ).first()

    if subscription:
        subscription.plan_id = plan.id
        subscription.stripe_customer_id = stripe_customer_id
        subscription.stripe_subscription_id = stripe_subscription_id
    else:
        subscription = Subscription(
            tenant_id=tenant_id,
            plan_id=plan.id,
            status="active",
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
        )
        db.add(subscription)

    db.commit()


def handle_subscription_updated(db: Session, event_data: dict):
    stripe_sub_id = event_data["id"]
    new_status = event_data["status"]

    subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == stripe_sub_id,
    ).first()

    if subscription:
        subscription.status = new_status
        db.commit()


def handle_subscription_deleted(db: Session, event_data: dict):
    stripe_sub_id = event_data["id"]

    subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == stripe_sub_id,
    ).first()

    if subscription:
        subscription.status = "canceled"
        db.commit()