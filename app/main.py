from fastapi import FastAPI
from app.database import engine, Base
from app.models.models import Tenant, Plan, Subscription, UsageEvent
from app.routes.usage import router as usage_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Usage Metering & Billing Engine",
    description="Meter usage, enforce quotas, calculate costs, sync with Stripe.",
    version="1.0.0",
)


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "metering-billing"}


app.include_router(usage_router)