# Build Log

An honest record of where AI assistance helped, where it got things wrong, and where I pushed back or corrected the approach.

## AI usage

I used Claude throughout this project as a tutor rather than a code generator. The workflow was: I'd ask for line-by-line explanations of each concept before writing anything, then push back on decisions that felt off or that I didn't fully understand.

## Where AI was wrong or over-engineered, and what I changed

### Walrus operator in the /usage route
Claude initially wrote the response-building block using Python's walrus operator (`if event_type := request.event_type:`), even though `event_type` was already guaranteed to be truthy by our Pydantic schema. I asked why and Claude admitted it was unnecessary. Replaced with a plain assignment.

### Outdated Gemini model name
Claude specified `gemini-2.0-flash` in the LLM integration. That model was retired by Google — the actual API returned "no longer available, use gemini-3.6-flash." I updated the code to use the current model.

### Missing tests volume mount
The first version of `docker-compose.yml` only mounted `./app:/code/app`, not the tests folder. Meant every test edit required a full rebuild. Added `./tests:/code/tests` for hot-reload.

### Cost test had insufficient quota
The cost calculation test tried to record 3,000,000 tokens against a tenant on the Free plan (100,000 limit). It failed with 429 instead of the expected cost calculation. Claude and I debugged together — I added a subscription upgrade to Pro at the start of the test so it had enough quota to actually record the event.

### Overly complex example initially proposed
Claude first proposed a big file with the entire models module, entire routes module etc. I pushed back and asked for a strict line-by-line explanation of each file before creating it. That workflow stuck for the rest of the build.

## Where I extended beyond what AI suggested

### Real LLM integration
The capstone brief says AI usage "can be simulated." Instead I integrated Google Gemini for real, added dual counting (each `/generate` request counts against both `api_call` and `tokens` quotas), and made the token counts from actual Gemini responses. This wasn't in the brief — I did it to make the project genuinely useful and demo-worthy.

### Early quota checks before the LLM call
I noticed the first version of the generate endpoint would call Gemini FIRST and then check the quota — wasting a real API call if the tenant was over their limit. Asked Claude to add early quota checks before the Gemini call. Now unauthorized requests are rejected before spending Google's free-tier quota.

### Committed in feature-sized batches, not per-file
Claude initially suggested committing after each file. I preferred fewer, more meaningful commits at natural breakpoints (skeleton → models → core logic → Stripe → LLM → tests → docs). Cleaner git history for recruiters.

## What I understand deeply vs. superficially

**Deeply understood:**
- Idempotency (why we need it, how the UNIQUE constraint enforces it at the database level, the race-condition case)
- Layered architecture (routes → services → models) and why it matters for swappability
- Money math as integer cents, per-category pricing
- Stripe webhook signature verification and the forgery attack it prevents
- Pytest fixtures (yield pattern, dependency injection via `app.dependency_overrides`)
- Foreign keys and one-to-many relationships

**Still hazy:**
- Alembic migrations (we used `create_all()` for simplicity — I'd need to learn migrations for a production system)
- Concurrency deeper than the race-condition example — I understand the specific case but not the full picture of async/await internals

## What I'd do differently on the next project

- Add proper migrations from day one instead of `create_all()`
- Add structured logging (JSON logs) so a reviewer could `grep` for a request through the whole system
- Write the tests alongside the code, not at the end
- Add integration tests for the Stripe webhook path (not just curl testing)