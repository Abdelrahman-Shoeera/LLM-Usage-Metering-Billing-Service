# LLM Billing Engine

A production-grade backend service that meters LLM usage, enforces subscription quotas, calculates costs with real AI token pricing rules, and syncs subscription state with Stripe via signature-verified webhooks.

Built with FastAPI, PostgreSQL, SQLAlchemy, Stripe, and Google Gemini.

## What it does

Every SaaS product needs to answer three questions: how much has this customer used, how much do they owe, and have they hit their limit? This service answers all three with correctness guarantees — no double-counting under retries, no missed quota boundaries, no wrong money math.

Real-world features:

- **Idempotent metering** — same request retried never creates duplicate charges, enforced at the database level via a UNIQUE constraint
- **Quota enforcement** — plan limits checked before every billable action, with honest HTTP status codes (429 for exceeded, 402 for unpaid)
- **AI-aware cost calculation** — cached input tokens billed at 50%, reasoning tokens billed as output, categories priced separately
- **Stripe integration** — Checkout sessions for upgrades, signature-verified webhooks with duplicate-event deduplication
- **Real LLM integration** — `/generate` endpoint calls Gemini and records actual token usage with dual counting (API calls + tokens)

## Architecture

Each layer only talks to the one below it. The database can be swapped without touching business logic.

## Tech stack

- **FastAPI** + **Uvicorn** — async web framework
- **PostgreSQL 16** — persistent storage
- **SQLAlchemy 2.0** — ORM with idempotent inserts
- **Pydantic 2** — request/response validation
- **Stripe** — payment integration (test mode only)
- **Google Gemini** — real LLM integration
- **Docker Compose** — containerized dev environment
- **pytest** — 9-scenario test suite

## Setup

Prerequisites: Docker Desktop, a Stripe test account, a Gemini API key.

1. Clone and configure:

```bash
    git clone <this-repo>
    cd llm-billing-engine
    cp .env.example .env
    # Edit .env with your Stripe test keys and Gemini API key
```

2. Run the app:

```bash
    docker compose up --build
```

3. Seed demo data:

```bash
    docker compose exec app python -m app.seed
```

    Copy the tenant ID that gets printed.

4. Verify:

```bash
    curl http://localhost:8000/health
```

## API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET  | /health | Health check |
| POST | /usage | Record a billable event (idempotent) |
| GET  | /usage?tenant_id=X | Read usage + limits + cost |
| POST | /generate | Call Gemini, record token usage automatically |
| POST | /billing/checkout | Create a Stripe Checkout session |
| POST | /webhooks/stripe | Receive Stripe webhook events (signature-verified) |

Interactive API docs auto-generated at `http://localhost:8000/docs`.

## Testing

```bash
docker compose exec db createdb -U postgres test_billing
docker compose exec app pytest -v
```

Nine scenarios covering:

- Duplicate idempotency key → single event recorded
- Quota at exact boundary allowed, over the boundary returns 429
- Token pricing math with pinned expected values
- Missing subscription → 404
- Invalid input → 422 (missing key, bad event type, negative quantity)

## Design decisions

- **UUIDs over integer IDs** — unguessable, prevents enumeration attacks
- **Money as integer cents, never floats** — floating point can't represent money precisely
- **UNIQUE constraint on idempotency_key** — database-level guarantee against double-counting
- **Plans stored in the database, not code constants** — pricing can change without a code deploy
- **Two-layer idempotency (app check + DB constraint)** — catches 99.9% of duplicates fast, DB catches the race conditions
- **Separate token categories priced separately** — cached input at 50%, reasoning billed as output

## Limitations (honest)

- No user authentication (tenant_id passed directly in requests)
- No invoicing, proration, or overage billing (stretch goals)
- No frontend UI — all interaction via curl or the auto-generated docs
- `create_all()` used instead of Alembic migrations (simpler for a capstone)

## What I learned

- How to design idempotency guarantees that survive network retries
- Why money math needs integer cents and per-category pricing
- Real-world Stripe webhook patterns: signature verification and event deduplication
- How to design HTTP responses that are honest about failure modes (429 vs 402 vs 404 vs 422)
- Building a layered architecture where the web framework can be swapped without touching business logic