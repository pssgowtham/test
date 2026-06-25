"""Cost estimation for Azure Document Intelligence and Azure OpenAI usage.

Rates come from settings (overridable via environment variables) so the model
can be tuned to a customer's actual contract pricing.
"""
from __future__ import annotations

from app.config import get_settings
from app.models import CostBreakdown


def estimate_cost(
    *, di_pages: int, prompt_tokens: int, completion_tokens: int
) -> CostBreakdown:
    s = get_settings()
    di_cost = di_pages * s.cost_di_per_page
    aoai_cost = (
        prompt_tokens / 1000.0 * s.cost_aoai_prompt_per_1k
        + completion_tokens / 1000.0 * s.cost_aoai_completion_per_1k
    )
    return CostBreakdown(
        di_pages=di_pages,
        di_cost_usd=round(di_cost, 6),
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        aoai_cost_usd=round(aoai_cost, 6),
        total_cost_usd=round(di_cost + aoai_cost, 6),
    )
