def test_create_usage_event_success(client, seeded_data):
    tenant_id = seeded_data["tenant"].id

    response = client.post(
        "/usage",
        json={
            "tenant_id": tenant_id,
            "event_type": "api_call",
            "quantity": 1,
        },
        headers={"Idempotency-Key": "test-key-001"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["usage_event"]["quantity"] == 1
    assert data["quota"]["used"] == 1
    assert data["quota"]["remaining"] == 999


def test_duplicate_idempotency_key_returns_original(client, seeded_data):
    tenant_id = seeded_data["tenant"].id

    response1 = client.post(
        "/usage",
        json={"tenant_id": tenant_id, "event_type": "api_call", "quantity": 1},
        headers={"Idempotency-Key": "same-key-123"},
    )

    response2 = client.post(
        "/usage",
        json={"tenant_id": tenant_id, "event_type": "api_call", "quantity": 1},
        headers={"Idempotency-Key": "same-key-123"},
    )

    assert response1.status_code == 201
    assert response2.status_code == 201
    assert response1.json()["usage_event"]["id"] == response2.json()["usage_event"]["id"]
    assert response2.json()["quota"]["used"] == 1


def test_quota_at_boundary_allowed(client, seeded_data):
    tenant_id = seeded_data["tenant"].id

    response = client.post(
        "/usage",
        json={"tenant_id": tenant_id, "event_type": "api_call", "quantity": 1000},
        headers={"Idempotency-Key": "boundary-test"},
    )

    assert response.status_code == 201
    assert response.json()["quota"]["used"] == 1000
    assert response.json()["quota"]["remaining"] == 0


def test_quota_exceeded_returns_429(client, seeded_data):
    tenant_id = seeded_data["tenant"].id

    client.post(
        "/usage",
        json={"tenant_id": tenant_id, "event_type": "api_call", "quantity": 1000},
        headers={"Idempotency-Key": "fill-quota"},
    )

    response = client.post(
        "/usage",
        json={"tenant_id": tenant_id, "event_type": "api_call", "quantity": 1},
        headers={"Idempotency-Key": "over-quota"},
    )

    assert response.status_code == 429
    assert "Quota exceeded" in response.json()["detail"]

def test_cost_calculation_token_pricing(client, seeded_data, db_session):
    tenant_id = seeded_data["tenant"].id
    subscription = seeded_data["subscription"]
    subscription.plan_id = seeded_data["pro_plan"].id
    db_session.commit()

    post_response = client.post(
        "/usage",
        json={
            "tenant_id": tenant_id,
            "event_type": "tokens",
            "quantity": 3_000_000,
            "metadata": {
                "input_tokens": 1_000_000,
                "cached_input_tokens": 1_000_000,
                "output_tokens": 500_000,
                "reasoning_tokens": 500_000,
            },
        },
        headers={"Idempotency-Key": "cost-test"},
    )

    assert post_response.status_code == 201, f"POST failed: {post_response.json()}"

    response = client.get(f"/usage?tenant_id={tenant_id}")
    cost = response.json()["cost"]

    assert cost["tokens_cost_cents"] == 1950

def test_no_subscription_returns_404(client, db_session):
    from app.models.models import Tenant
    orphan = Tenant(name="Orphan Tenant")
    db_session.add(orphan)
    db_session.commit()

    response = client.post(
        "/usage",
        json={"tenant_id": orphan.id, "event_type": "api_call", "quantity": 1},
        headers={"Idempotency-Key": "orphan-test"},
    )

    assert response.status_code == 404


def test_missing_idempotency_key_returns_422(client, seeded_data):
    tenant_id = seeded_data["tenant"].id

    response = client.post(
        "/usage",
        json={"tenant_id": tenant_id, "event_type": "api_call", "quantity": 1},
    )

    assert response.status_code == 422


def test_invalid_event_type_returns_422(client, seeded_data):
    tenant_id = seeded_data["tenant"].id

    response = client.post(
        "/usage",
        json={"tenant_id": tenant_id, "event_type": "invalid_type", "quantity": 1},
        headers={"Idempotency-Key": "invalid-type-test"},
    )

    assert response.status_code == 422


def test_negative_quantity_returns_422(client, seeded_data):
    tenant_id = seeded_data["tenant"].id

    response = client.post(
        "/usage",
        json={"tenant_id": tenant_id, "event_type": "api_call", "quantity": -5},
        headers={"Idempotency-Key": "negative-test"},
    )

    assert response.status_code == 422