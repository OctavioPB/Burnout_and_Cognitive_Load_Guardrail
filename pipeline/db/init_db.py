"""Database initialisation: create the `features` schema and all ORM tables.

Run once on first deploy or after `docker compose up` when Postgres is fresh:
    python -m pipeline.db.init_db
"""

from __future__ import annotations

import asyncio
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from pipeline.models import Base


def _get_engine(database_url: str | None = None) -> AsyncEngine:
    url = database_url or os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://guardrail:guardrail_dev@localhost:5432/burnout_guardrail",
    )
    return create_async_engine(url, echo=False)


async def init_db(engine: AsyncEngine | None = None) -> None:
    """Create `features` schema and all tables declared in pipeline.models."""
    eng = engine or _get_engine()
    async with eng.begin() as conn:
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS features"))
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(init_db())
