from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database import get_db
from app.schemas.usage import (
    UsageCreateRequest,
    UsageCreateResponse,
    UsageEventResponse,
    UsageGetResponse,
    QuotaInfo,
)
from app.services.usage_service import (
    record_usage,
    get_current_usage,
    get_tenant_subscription,
    get_usage_costs,
)

router = APIRouter()


@router.post("/usage", response_model=UsageCreateResponse, status_code=201)
def create_usage_event(
    request: UsageCreateRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    event, status = record_usage(
        db=db,
        tenant_id=request.tenant_id,
        event_type=request.event_type,
        quantity=request.quantity,
        idempotency_key=idempotency_key,
        metadata=request.metadata,
    )

    if status == "no_subscription":
        raise HTTPException(
            status_code=404,
            detail="No active subscription found for this tenant.",
        )

    if status == "quota_exceeded":
        raise HTTPException(
            status_code=429,
            detail=f"Quota exceeded for {request.event_type}. Upgrade your plan or wait until next billing period.",
        )

    event_type = request.event_type
    subscription = get_tenant_subscription(db, request.tenant_id)
    plan = subscription.plan
    current_usage = get_current_usage(db, request.tenant_id, event_type)

    if event_type == "api_call":
        limit = plan.api_call_limit
    else:
        limit = plan.token_limit

    return UsageCreateResponse(
        usage_event=UsageEventResponse.model_validate(event),
        quota=QuotaInfo(
            used=current_usage,
            limit=limit,
            remaining=limit - current_usage,
        ),
    )


@router.get("/usage", response_model=UsageGetResponse)
def get_usage(
    tenant_id: str,
    db: Session = Depends(get_db),
):
    subscription = get_tenant_subscription(db, tenant_id)
    if not subscription:
        raise HTTPException(
            status_code=404,
            detail="No active subscription found for this tenant.",
        )

    plan = subscription.plan

    api_call_usage = get_current_usage(db, tenant_id, "api_call")
    token_usage = get_current_usage(db, tenant_id, "tokens")

    return UsageGetResponse(
        tenant_id=tenant_id,
        period=datetime.now(timezone.utc).strftime("%Y-%m"),
        api_calls=QuotaInfo(
            used=api_call_usage,
            limit=plan.api_call_limit,
            remaining=plan.api_call_limit - api_call_usage,
        ),
        tokens=QuotaInfo(
            used=token_usage,
            limit=plan.token_limit,
            remaining=plan.token_limit - token_usage,
        ),
        cost=get_usage_costs(db, tenant_id),  
    )