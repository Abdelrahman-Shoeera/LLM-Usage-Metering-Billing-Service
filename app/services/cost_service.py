PRICING_PER_MILLION = {
    "input_tokens": 300,
    "cached_input_tokens": 150,
    "output_tokens": 1500,
    "reasoning_tokens": 1500,
}

API_CALL_COST_CENTS = 1


def calculate_token_cost(metadata: dict) -> int:
    if not metadata:
        return 0

    total_cents = 0

    for token_type, price_per_million in PRICING_PER_MILLION.items():
        count = metadata.get(token_type, 0)
        cost = (count * price_per_million) // 1_000_000
        total_cents += cost

    return total_cents


def calculate_api_call_cost(count: int) -> int:
    return count * API_CALL_COST_CENTS