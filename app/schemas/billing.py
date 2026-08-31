from pydantic import BaseModel


class CheckoutRequest(BaseModel):
    tenant_id: str
    plan: str = "pro"


class CheckoutResponse(BaseModel):
    checkout_url: str