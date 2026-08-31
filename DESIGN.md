# LLM Billing Engine — Design Doc

## Problem

Every SaaS must answer: how much has this customer used, what do they owe, and have they hit their limit? This service answers all three with correctness guarantees — no double-counting, no missed limits, no wrong math.

## Data Model

Five tables. All IDs are UUIDs. All timestamps are UTC.

### tenants
| Column     | Type      | Notes                    |
|------------|-----------|--------------------------|
| id         | UUID (PK) | Unguessable identifier   |
| name       | TEXT      | Human-readable label     |
| created_at | TIMESTAMP | Default: now()           |

### plans
| Column         | Type      | Notes                         |
|----------------|-----------|-------------------------------|
| id             | UUID (PK) |                               |
| name           | TEXT      | "free" or "pro" (UNIQUE)      |
| api_call_limit | INTEGER   | Monthly API call allowance    |
| token_limit    | INTEGER   | Monthly token allowance       |

Seed data:
- Free: 1,000 API calls, 100,000 tokens
- Pro: 50,000 API calls, 5,000,000 tokens

### subscriptions
| Column                 | Type      | Notes                              |
|------------------------|-----------|------------------------------------|
| id                     | UUID (PK) |                                    |
| tenant_id              | UUID (FK) | → tenants.id                       |
| plan_id                | UUID (FK) | → plans.id                         |
| status                 | TEXT      | active / canceled / past_due       |
| stripe_subscription_id | TEXT      | Nullable, UNIQUE                   |
| stripe_customer_id     | TEXT      | Nullable                           |
| current_period_start   | TIMESTAMP | Billing cycle start                |
| current_period_end     | TIMESTAMP | Billing cycle end                  |

### usage_events
| Column          | Type      | Notes                                   |
|-----------------|-----------|-----------------------------------------|
| id              | UUID (PK) |                                         |
| tenant_id       | UUID (FK) | → tenants.id                            |
| event_type      | TEXT      | "api_call" or "tokens"                  |
| quantity        | INTEGER   | 1 for API calls, token count for tokens |
| idempotency_key | TEXT      | UNIQUE — prevents duplicates            |
| created_at      | TIMESTAMP |                                         |
| metadata        | JSONB     | Optional context (model, breakdown)     |

### processed_webhook_events
| Column           | Type      | Notes                          |
|------------------|-----------|--------------------------------|
| id               | UUID (PK) |                                |
| stripe_event_id  | TEXT      | UNIQUE — prevents duplicate processing |
| event_type       | TEXT      | e.g. "checkout.session.completed" |
| processed_at     | TIMESTAMP |                                |

## API Surface

### POST /usage — Record a billable event
- Header: `Idempotency-Key: <uuid>`
- Body: `{ tenant_id, event_type, quantity, metadata? }`
- Logic: check idempotency → check quota → insert event → return 201
- Duplicate key → return original event (200)
- Over quota → 429 with clear message
- No subscription → 404

### GET /usage?tenant_id=X — Read current usage
- Returns: used / limit / remaining per usage type + cost breakdown in cents
- Aggregates usage_events for current billing period (month-to-date)

### POST /generate — Real LLM call with automatic metering
- Body: `{ tenant_id, prompt }`
- Header: `Idempotency-Key: <uuid>`
- Logic: check quotas → call Gemini → record api_call + tokens events
- Returns: AI response + actual token counts from Gemini

### POST /billing/checkout — Start Stripe Checkout
- Body: `{ tenant_id, plan: "pro" }`
- Returns: `{ checkout_url }` (Stripe Checkout Session URL)

### POST /webhooks/stripe — Receive Stripe events
- Verify signature → 400 if forged
- Deduplicate by event ID → ignore replays
- Handle: checkout.session.completed, customer.subscription.updated, customer.subscription.deleted
- Return 200 after processing

## Idempotency Strategy

Two-layer protection:

1. **Application check** — before inserting, query for the idempotency key. If found, return the original event. Fast path for most duplicates.
2. **Database constraint** — UNIQUE(idempotency_key) on usage_events. If two identical requests race past the application check simultaneously, the database itself rejects the second INSERT with IntegrityError.

The race condition is real: two identical requests arriving in the same millisecond can both pass the application check before either has inserted. The database is the last line of defense.

## Cost Calculation Rules

All money as integer cents. Never floats.

Token pricing (per 1M tokens):
- Input tokens: 300 cents ($3.00)
- Cached input tokens: 150 cents ($1.50) — 50% discount
- Output tokens: 1500 cents ($15.00)
- Reasoning tokens: 1500 cents ($15.00) — billed as output per real-world convention

API call pricing: 1 cent per call.

Categories priced separately, then summed. Total tokens cannot be multiplied by one blended rate — that produces wrong numbers.

## Layer Architecture

Routes (HTTP) → validate input, translate service results to HTTP responses
Services (logic) → metering, quotas, cost, Stripe operations, LLM calls
Data (models) → SQLAlchemy models and queries

Each layer only depends on the one below. Swap the web framework without touching business logic. Swap the database without touching services.

## Explicit Non-Goals

- No real payments (Stripe test mode only)
- No user authentication (tenant_id passed directly)
- No invoicing, proration, or overage billing (stretch goals)
- No frontend UI
- No production migrations (create_all() used for simplicity)