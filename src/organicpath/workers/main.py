"""Worker process: `uv run arq organicpath.workers.main.WorkerSettings`."""

import asyncio
import logging

from arq.worker import Worker

from organicpath.config import Settings, get_settings
from organicpath.db.ingest_jobs import IngestRepository
from organicpath.db.llm_calls import make_recorder
from organicpath.db.session import make_engine, make_sessionmaker
from organicpath.ingest.fetch import make_client
from organicpath.llm.doc_meta import DocMeta
from organicpath.llm.gateway import build_gateway
from organicpath.llm.prompts import latest, read_prompt
from organicpath.logging_setup import setup_logging
from organicpath.workers.ingest import Pace, ingest_document
from organicpath.workers.queue import Queue, redis_settings

logger = logging.getLogger("organicpath.worker")


async def startup(ctx: dict) -> None:
    settings: Settings = ctx["settings"]
    if not ctx.get("embedded"):
        setup_logging(settings.log_level)
        logging.getLogger("arq").handlers.clear()
    logging.getLogger("httpx").setLevel(logging.WARNING)
    engine = make_engine(settings)
    ctx["engine"], ctx["sessionmaker"] = engine, make_sessionmaker(engine)
    ctx["gateway"] = build_gateway(settings, make_recorder(ctx["sessionmaker"]))
    ctx["http"] = make_client(2)
    ctx["pace"] = Pace(settings.ingest_rpm)
    ctx["extract"] = None
    if ctx["gateway"].providers:
        try:
            version = latest(settings.prompts_dir, "extract")
        except FileNotFoundError:
            logger.warning("no prompts/extract_v*.md: documents are parsed, not extracted")
        else:
            prompt = read_prompt(settings.prompts_dir, version)
            ctx["extract"] = {
                "schema": DocMeta,
                "prompt": prompt,
                "version": version,
                "chars": 6000,
            }
    async with ctx["sessionmaker"]() as session:
        lost = await Queue(ctx["redis"]).put(await IngestRepository(session).open_item_ids())
    logger.info("worker ready, %s unfinished item(s) put back in the queue", lost)


async def shutdown(ctx: dict) -> None:
    await ctx["http"].aclose()
    await ctx["engine"].dispose()


def worker_options(settings: Settings, *, embedded: bool = False) -> dict:
    return {
        "functions": [ingest_document],
        "on_startup": startup,
        "on_shutdown": shutdown,
        "redis_settings": redis_settings(settings.redis_url),
        "ctx": {"settings": settings, "embedded": embedded},
        "max_jobs": settings.ingest_concurrency,
        "job_timeout": settings.ingest_job_timeout,
        "max_tries": settings.ingest_max_tries,
        "keep_result": 0,
        "poll_delay": 1.0,
    }


async def run_embedded(settings: Settings) -> None:
    """Run a worker in the API process on hosts without a separate worker service."""
    worker = Worker(**worker_options(settings, embedded=True), handle_signals=False)
    try:
        await worker.async_run()
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("the embedded worker stopped: is REDIS_URL right?")
    finally:
        await worker.close()


WorkerSettings = worker_options(get_settings())
