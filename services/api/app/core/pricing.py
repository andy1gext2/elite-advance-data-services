"""Cost estimation for the operator dashboard.

Text (Claude) cost is exact — computed from the input/output token counts stored
on each AiUsage row against per-model rates. Image/video are per-asset estimates
(providers bill per generation, not per token) and come from Settings so the
operator can tune them to real Gemini/Veo pricing.
"""
from __future__ import annotations

# Claude API list price, USD per 1,000,000 tokens (input, output). Source: the
# Anthropic pricing table. Keep in sync when rates change or models are added.
MODEL_RATES: dict[str, tuple[float, float]] = {
    "claude-opus-4-8": (5.00, 25.00),
    "claude-opus-4-7": (5.00, 25.00),
    "claude-opus-4-6": (5.00, 25.00),
    "claude-sonnet-5": (3.00, 15.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
}

# Fallback when a row's model isn't in the table (unknown/mock) — price it at the
# default Opus tier so estimates never understate cost.
_DEFAULT_RATE = (5.00, 25.00)


def text_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Exact USD cost of one Claude generation from its token counts."""
    in_rate, out_rate = MODEL_RATES.get(model, _DEFAULT_RATE)
    return (input_tokens / 1_000_000) * in_rate + (output_tokens / 1_000_000) * out_rate
