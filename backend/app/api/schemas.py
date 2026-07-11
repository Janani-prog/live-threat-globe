import datetime

from pydantic import BaseModel, ConfigDict


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ip_hash: str
    lat: float | None
    lon: float | None
    country: str | None
    asn: str | None
    category: str | None
    source: str | None
    confidence_source: float | None
    risk_score: float | None
    reported_at: datetime.datetime | None
    ingested_at: datetime.datetime


class CountBucket(BaseModel):
    key: str
    count: int


class StatsSummary(BaseModel):
    total_events: int
    top_countries: list[CountBucket]
    top_asns: list[CountBucket]
    category_breakdown: list[CountBucket]
    cloudflare_top_origin_countries: list[dict] | None = None


class TimeseriesPoint(BaseModel):
    bucket: datetime.datetime
    count: int


class TimeseriesOut(BaseModel):
    points: list[TimeseriesPoint]
