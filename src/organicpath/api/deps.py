"""Dependencies: endpoints ask for these instead of building them."""

import asyncio
import json
import secrets
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from organicpath.config import Settings
from organicpath.db.ingest_jobs import IngestRepository
from organicpath.db.llm_calls import UsageRepository
from organicpath.db.repository import DocumentRepository
from organicpath.llm.gateway import LLMGateway
from organicpath.workers.queue import Queue


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """One session per request, closed automatically afterwards."""
    async with request.app.state.sessionmaker() as session:
        yield session


async def get_repo(session: Annotated[AsyncSession, Depends(get_session)]) -> DocumentRepository:
    return DocumentRepository(session)


async def check_db(request: Request) -> bool:
    """Can we run SELECT 1 within 2 seconds?"""
    try:
        async with request.app.state.engine.connect() as conn:
            await asyncio.wait_for(conn.execute(text("SELECT 1")), timeout=2)
        return True
    except Exception:
        return False


def get_gateway(request: Request) -> LLMGateway:
    return request.app.state.gateway


async def get_ingest_repo(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> IngestRepository:
    return IngestRepository(session)


async def get_queue(request: Request) -> Queue:
    """Connect to Redis on first use so other API routes work while Redis is down."""
    state = request.app.state
    if getattr(state, "queue", None) is None:
        try:
            state.queue = await Queue.connect(state.settings.redis_url)
        except Exception as exc:
            raise HTTPException(
                status_code=503, detail="The job queue (Redis) cannot be reached."
            ) from exc
    return state.queue


def get_manifest(request: Request) -> list[dict]:
    """Read the newest manifest line for each URL."""
    path = request.app.state.settings.manifest_file
    if not path.is_file():
        return []
    latest: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
            url = record.get("url")
            if isinstance(url, str):
                latest[url] = record
        except (json.JSONDecodeError, AttributeError):
            continue
    return list(latest.values())


def require_admin(request: Request, x_admin_token: Annotated[str, Header()] = "") -> None:
    """Only a holder of ADMIN_TOKEN may start work that spends model calls."""
    settings: Settings = request.app.state.settings
    if not settings.admin_token:
        if settings.app_env == "local":
            return
        raise HTTPException(status_code=403, detail="Set ADMIN_TOKEN to allow ingestion here.")
    if not secrets.compare_digest(x_admin_token, settings.admin_token):
        raise HTTPException(status_code=401, detail="Missing or wrong X-Admin-Token header.")


async def get_usage_repo(session: Annotated[AsyncSession, Depends(get_session)]) -> UsageRepository:
    return UsageRepository(session)


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
RepoDep = Annotated[DocumentRepository, Depends(get_repo)]
DbCheckDep = Annotated[bool, Depends(check_db)]
GatewayDep = Annotated[LLMGateway, Depends(get_gateway)]
UsageDep = Annotated[UsageRepository, Depends(get_usage_repo)]
IngestRepoDep = Annotated[IngestRepository, Depends(get_ingest_repo)]
QueueDep = Annotated[Queue, Depends(get_queue)]
ManifestDep = Annotated[list[dict], Depends(get_manifest)]
