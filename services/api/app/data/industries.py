"""Curated industry list for the onboarding combobox + trend caching.

The combobox lets owners pick a canonical industry (best UX + lets industry trends
be generated once and cached/shared across every tenant in that industry) while
still typing their own for niche businesses. `normalize()` maps free text onto a
canonical slug when it recognizes it, else returns a clean slug of the raw text so
even a bespoke industry gets a stable (if uncached-elsewhere) key."""
from __future__ import annotations

import re

# (slug, label, emoji). slug is the canonical cache key.
INDUSTRIES: list[dict] = [
    {"slug": "restaurant", "label": "Restaurant", "emoji": "🍽️"},
    {"slug": "cafe", "label": "Coffee shop / Cafe", "emoji": "☕"},
    {"slug": "bakery", "label": "Bakery", "emoji": "🥐"},
    {"slug": "bar", "label": "Bar / Brewery", "emoji": "🍺"},
    {"slug": "food_truck", "label": "Food truck", "emoji": "🚚"},
    {"slug": "retail", "label": "Retail / Boutique", "emoji": "🛍️"},
    {"slug": "ecommerce", "label": "E-commerce", "emoji": "📦"},
    {"slug": "salon", "label": "Hair salon", "emoji": "💇"},
    {"slug": "barbershop", "label": "Barbershop", "emoji": "💈"},
    {"slug": "spa", "label": "Spa / Massage", "emoji": "💆"},
    {"slug": "nails", "label": "Nail salon", "emoji": "💅"},
    {"slug": "beauty", "label": "Beauty / Cosmetics", "emoji": "💄"},
    {"slug": "fitness", "label": "Gym / Fitness studio", "emoji": "🏋️"},
    {"slug": "yoga", "label": "Yoga / Pilates", "emoji": "🧘"},
    {"slug": "dental", "label": "Dental practice", "emoji": "🦷"},
    {"slug": "medical", "label": "Medical / Clinic", "emoji": "🩺"},
    {"slug": "chiropractic", "label": "Chiropractic", "emoji": "🦴"},
    {"slug": "veterinary", "label": "Veterinary", "emoji": "🐾"},
    {"slug": "real_estate", "label": "Real estate", "emoji": "🏡"},
    {"slug": "mortgage", "label": "Mortgage / Lending", "emoji": "🏦"},
    {"slug": "insurance", "label": "Insurance", "emoji": "🛡️"},
    {"slug": "accounting", "label": "Accounting / Bookkeeping", "emoji": "🧮"},
    {"slug": "legal", "label": "Law firm / Legal", "emoji": "⚖️"},
    {"slug": "financial_advisor", "label": "Financial advisor", "emoji": "📈"},
    {"slug": "auto_repair", "label": "Auto repair", "emoji": "🔧"},
    {"slug": "auto_dealer", "label": "Auto dealership", "emoji": "🚗"},
    {"slug": "cleaning", "label": "Cleaning service", "emoji": "🧽"},
    {"slug": "landscaping", "label": "Landscaping / Lawn care", "emoji": "🌱"},
    {"slug": "plumbing", "label": "Plumbing", "emoji": "🚰"},
    {"slug": "electrical", "label": "Electrical", "emoji": "💡"},
    {"slug": "hvac", "label": "HVAC", "emoji": "❄️"},
    {"slug": "roofing", "label": "Roofing", "emoji": "🏠"},
    {"slug": "construction", "label": "Construction / Contractor", "emoji": "🏗️"},
    {"slug": "pest_control", "label": "Pest control", "emoji": "🐜"},
    {"slug": "photography", "label": "Photography", "emoji": "📷"},
    {"slug": "event_planning", "label": "Event planning", "emoji": "🎉"},
    {"slug": "florist", "label": "Florist", "emoji": "💐"},
    {"slug": "pet_grooming", "label": "Pet grooming / Boarding", "emoji": "🐕"},
    {"slug": "childcare", "label": "Childcare / Daycare", "emoji": "🧸"},
    {"slug": "education", "label": "Education / Tutoring", "emoji": "📚"},
    {"slug": "nonprofit", "label": "Nonprofit", "emoji": "🤝"},
    {"slug": "consulting", "label": "Consulting / Coaching", "emoji": "💼"},
    {"slug": "marketing_agency", "label": "Marketing agency", "emoji": "📣"},
    {"slug": "technology", "label": "Software / Technology", "emoji": "💻"},
    {"slug": "hotel", "label": "Hotel / Hospitality", "emoji": "🏨"},
    {"slug": "travel", "label": "Travel / Tourism", "emoji": "✈️"},
    {"slug": "apparel", "label": "Apparel / Fashion", "emoji": "👗"},
    {"slug": "jewelry", "label": "Jewelry", "emoji": "💍"},
    {"slug": "home_decor", "label": "Home decor / Furniture", "emoji": "🛋️"},
    {"slug": "tattoo", "label": "Tattoo / Piercing", "emoji": "🖋️"},
]

# label (lowercased) and slug both resolve to the canonical slug.
_LOOKUP: dict[str, str] = {}
for _i in INDUSTRIES:
    _LOOKUP[_i["slug"]] = _i["slug"]
    _LOOKUP[_i["label"].lower()] = _i["slug"]

# A few common phrasings owners type that map onto a canonical slug.
_ALIASES: dict[str, str] = {
    "coffee": "cafe", "coffee shop": "cafe", "cafe": "cafe", "café": "cafe",
    "restaurants": "restaurant", "eatery": "restaurant", "diner": "restaurant",
    "food service": "restaurant", "hair": "salon", "hairdresser": "salon",
    "gym": "fitness", "personal trainer": "fitness", "crossfit": "fitness",
    "realtor": "real_estate", "real estate agent": "real_estate",
    "lawyer": "legal", "attorney": "legal", "law": "legal",
    "cpa": "accounting", "bookkeeping": "accounting", "tax": "accounting",
    "dentist": "dental", "doctor": "medical", "clinic": "medical",
    "vet": "veterinary", "auto": "auto_repair", "mechanic": "auto_repair",
    "lawn care": "landscaping", "landscaper": "landscaping",
    "hvac / heating": "hvac", "heating": "hvac", "ac": "hvac",
    "contractor": "construction", "builder": "construction",
    "photographer": "photography", "software": "technology", "saas": "technology",
    "it": "technology", "tech": "technology", "boutique": "retail",
    "store": "retail", "shop": "retail", "online store": "ecommerce",
}


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_")
    return s or "general"


def normalize(industry: str | None) -> str:
    """Map free text to a canonical slug when recognized, else a clean slug of the
    raw text (so bespoke industries still get a stable cache key)."""
    if not industry or not industry.strip():
        return "general"
    key = re.sub(r"\s+", " ", industry.strip().lower())
    if key in _LOOKUP:
        return _LOOKUP[key]
    if key in _ALIASES:
        return _ALIASES[key]
    return _slugify(industry)


def display_name(slug: str, fallback: str | None = None) -> str:
    """Human label for a slug (for prompts + the dashboard heading)."""
    for i in INDUSTRIES:
        if i["slug"] == slug:
            return i["label"]
    return (fallback or slug.replace("_", " ")).strip().title()
