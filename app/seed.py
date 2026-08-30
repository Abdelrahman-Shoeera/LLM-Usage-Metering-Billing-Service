from app.database import SessionLocal
from app.models.models import Tenant, Plan, Subscription


def seed():
    db = SessionLocal()

    try:
        existing_plans = db.query(Plan).count()
        if existing_plans > 0:
            print("Plans already exist, skipping seed.")
            return

        free_plan = Plan(
            name="free",
            api_call_limit=1000,
            token_limit=100_000,
        )
        pro_plan = Plan(
            name="pro",
            api_call_limit=50_000,
            token_limit=5_000_000,
        )
        db.add(free_plan)
        db.add(pro_plan)

        tenant = Tenant(name="Acme Corp")
        db.add(tenant)

        db.flush()

        subscription = Subscription(
            tenant_id=tenant.id,
            plan_id=free_plan.id,
            status="active",
        )
        db.add(subscription)

        db.commit()

        print(f"Seeded successfully!")
        print(f"  Tenant: {tenant.name} (ID: {tenant.id})")
        print(f"  Plan: {free_plan.name} (limit: {free_plan.api_call_limit} calls, {free_plan.token_limit} tokens)")
        print(f"  Subscription: {subscription.id} (status: {subscription.status})")

    except Exception as e:
        db.rollback()
        print(f"Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()