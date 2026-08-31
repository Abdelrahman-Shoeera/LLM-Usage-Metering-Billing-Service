import google.generativeai as genai
from sqlalchemy.orm import Session

from app.config import settings
from app.services.usage_service import (
    record_usage,
    get_current_usage,
    get_tenant_subscription,
)


genai.configure(api_key=settings.GEMINI_API_KEY)


def generate_response(db: Session, tenant_id: str, prompt: str, idempotency_key: str):
    subscription = get_tenant_subscription(db, tenant_id)
    if not subscription:
        return None, None, "no_subscription"

    plan = subscription.plan

    api_call_usage = get_current_usage(db, tenant_id, "api_call")
    if api_call_usage >= plan.api_call_limit:
        return None, None, "quota_exceeded"

    token_usage = get_current_usage(db, tenant_id, "tokens")
    if token_usage >= plan.token_limit:
        return None, None, "quota_exceeded"

    model = genai.GenerativeModel("gemini-3.6-flash")

    response = model.generate_content(prompt)

    usage_metadata = response.usage_metadata
    input_tokens = usage_metadata.prompt_token_count
    output_tokens = usage_metadata.candidates_token_count
    total_tokens = usage_metadata.total_token_count

    metadata = {
        "input_tokens": input_tokens,
        "cached_input_tokens": 0,
        "output_tokens": output_tokens,
        "reasoning_tokens": 0,
        "model": "gemini-3.6-flash",
        "prompt": prompt[:100],
    }

    event, status = record_usage(
        db=db,
        tenant_id=tenant_id,
        event_type="api_call",
        quantity=1,
        idempotency_key=idempotency_key + "-call",
        metadata=metadata,
    )

    if status == "quota_exceeded":
        return None, None, "quota_exceeded"

    event, status = record_usage(
        db=db,
        tenant_id=tenant_id,
        event_type="tokens",
        quantity=total_tokens,
        idempotency_key=idempotency_key + "-tokens",
        metadata=metadata,
    )

    if status == "quota_exceeded":
        return None, None, "quota_exceeded"

    return response.text, metadata, True