import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ip_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    country: Mapped[str | None] = mapped_column(String(64), nullable=True)
    asn: Mapped[str | None] = mapped_column(String(128), nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence_source: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    reported_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    ingested_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())


class GeoCache(Base):
    __tablename__ = "geo_cache"

    ip_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    country: Mapped[str | None] = mapped_column(String(64), nullable=True)
    asn: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_checked_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())


class ApiQuotaUsage(Base):
    """Persisted call counter guarding AbuseIPDB's /blacklist endpoint, which
    is capped at 5 requests/day on the free tier — confirmed live (a 429
    with "Daily rate limit of 5 requests exceeded for this endpoint").
    Persisted (not in-memory) so the guard survives process restarts.
    """

    __tablename__ = "api_quota_usage"

    date: Mapped[str] = mapped_column(String(10), primary_key=True)  # YYYY-MM-DD (UTC)
    blacklist_calls: Mapped[int] = mapped_column(Integer, default=0)
    check_calls: Mapped[int] = mapped_column(Integer, default=0)
