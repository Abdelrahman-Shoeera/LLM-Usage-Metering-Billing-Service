from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.generate import GenerateRequest, GenerateResponse
from app.services.generate_service import generate_response

router = APIRouter()


@router.post("/generate", response_model=GenerateResponse, status_code=201)
def generate(
    request: GenerateRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    text, metadata, status = generate_response(
        db=db,
        tenant_id=request.tenant_id,
        prompt=request.prompt,
        idempotency_key=idempotency_key,
    )

    if status == "no_subscription":
        raise HTTPException(
            status_code=404,
            detail="No active subscription found for this tenant.",
        )

    if status == "quota_exceeded":
        raise HTTPException(
            status_code=429,
            detail="Token quota exceeded. Upgrade your plan or wait until next billing period.",
        )

    return GenerateResponse(
        response=text,
        tokens_used=metadata,
    )