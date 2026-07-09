"""Retrieval for RAG: pull a business's brand/profile context before generation.

The AI never relies on memory across requests — every generation call is grounded
in the tenant's current profile fetched from Postgres here. As more brand tables
land (products, approved hashtags, custom prompts), extend this builder.
"""
from __future__ import annotations

from app.models.business import Business


def build_business_context(business: Business) -> dict:
    """A flat, JSON-serializable snapshot of the business for prompt grounding."""
    return {
        "name": business.name,
        "industry": business.industry,
        "website": business.website,
        "description": business.description,
        "target_audience": business.target_audience,
        "brand_voice": business.brand_voice,
        "tone": business.tone,
        "goals": business.goals,
    }
