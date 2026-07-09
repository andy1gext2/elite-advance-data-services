"""Analytics & insights schemas."""
from __future__ import annotations

from pydantic import BaseModel


class DashboardKpis(BaseModel):
    total_content: int
    published_posts: int
    pending_schedules: int
    total_reviews: int
    average_rating: float
    response_rate: float
    needs_attention: int
    ai_generations_total: int
    ai_generations_this_month: int


class WeekPoint(BaseModel):
    week: str
    count: int


class Timeseries(BaseModel):
    content_per_week: list[WeekPoint]
    reviews_per_week: list[WeekPoint]


class Trends(BaseModel):
    content_this_month: int
    content_last_month: int
    reviews_this_month: int
    reviews_last_month: int


class DashboardOut(BaseModel):
    kpis: DashboardKpis
    content_by_status: dict[str, int]
    content_by_channel: dict[str, int]
    sentiment: dict[str, int]
    timeseries: Timeseries
    trends: Trends
    recommendations: list[str]


class InsightsOut(BaseModel):
    summary: str
    recommendations: list[str]
