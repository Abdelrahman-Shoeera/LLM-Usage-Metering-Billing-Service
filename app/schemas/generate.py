from pydantic import BaseModel
from typing import Optional


class GenerateRequest(BaseModel):
    tenant_id: str
    prompt: str


class GenerateResponse(BaseModel):
    response: str
    tokens_used: dict