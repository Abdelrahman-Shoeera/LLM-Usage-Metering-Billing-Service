from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
import stripe

from app.database import get_db
from app.config import settings
from app.schemas.billing import CheckoutRequest, CheckoutResponse
from app.services.billing_service import (
    create_checkout_session,
    is_event_processed,
    mark_event_processed,
    handle_checkout_completed,
    handle_subscription_updated,
    handle_subscription_deleted,
)

router = APIRouter()


@router.post("/billing/checkout", response_model=CheckoutResponse)
def create_checkout(
    request: CheckoutRequest,
    db: Session = Depends(get_db),
):
    try:
        checkout_url = create_checkout_session(db, request.tenant_id, request.plan)
        return CheckoutResponse(checkout_url=checkout_url)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=502, detail=f"Stripe error: {str(e)}")


@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if is_event_processed(db, event["id"]):
        return {"status": "already_processed"}

    event_type = event["type"]
    event_data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        handle_checkout_completed(db, event_data)
    elif event_type == "customer.subscription.updated":
        handle_subscription_updated(db, event_data)
    elif event_type == "customer.subscription.deleted":
        handle_subscription_deleted(db, event_data)

    mark_event_processed(db, event["id"], event_type)

    return {"status": "processed"}