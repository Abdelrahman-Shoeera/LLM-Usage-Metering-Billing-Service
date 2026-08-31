from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UsageCreateRequest(BaseModel):
    tenant_id: str
    event_type: str = Field(pattern="^(api_call|tokens)$")
    quantity: int = Field(gt=0)
    metadata: Optional[dict] = None


class UsageEventResponse(BaseModel):
    id: str
    tenant_id: str
    event_type: str
    quantity: int
    created_at: datetime

    class Config:
        from_attributes = True


class QuotaInfo(BaseModel):
    used: int
    limit: int
    remaining: int


class UsageCreateResponse(BaseModel):
    usage_event: UsageEventResponse
    quota: QuotaInfo


class UsageGetResponse(BaseModel):
    tenant_id: str
    period: str
    api_calls: QuotaInfo
    tokens: QuotaInfo
    cost: dict