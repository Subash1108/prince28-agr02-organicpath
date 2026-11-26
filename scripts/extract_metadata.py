"""Fill documents.metadata with validated records for parsed documents.

Examples:
  uv run python scripts/extract_metadata.py --limit 5
  uv run python scripts/extract_metadata.py --retry-failed
  uv run python scripts/extract_metadata.py --schema
"""

import argparse
import asyncio
import sys
import time

from organicpath.config import get_settings
from organicpath.db.llm_calls import make_recorder
from organicpath.db.session import make_engine, make_sessionmaker
from organicpath.llm.doc_meta import DocMeta
from organicpath.llm.extract import run
from organicpath.llm.gateway import build_gateway
from organicpath.llm.prompts import latest, read_prompt


async def main_async(args: argparse.Namespace) -> int:
    settings = get_settings()
    version = latest(settings.prompts_dir, "extract")
    prompt = read_prompt(settings.prompts_dir, version)
    engine = make_engine(settings)
    sessionmaker = make_sessionmaker(engine)
    gateway = build_gateway(settings, make_recorder(sessionmaker))
    started = time.perf_counter()
    try:
        counts = await run(
            sessionmaker,
            gateway,
            DocMeta,
            prompt,
            version,
            limit=args.limit,
            rpm=args.rpm,
            chars=args.chars,
            retry_failed=args.retry_failed,
            native=args.schema,
        )
    finally:
        await engine.dispose()
    print(
        f"prompt={version} pending={counts['pending']} ok={counts['ok']} "
        f"repaired={counts['repaired']} failed={counts['failed']} "
        f"tokens_in={counts['tokens_in']} tokens_out={counts['tokens_out']} "
        f"cost=Rs {counts['micro_inr'] / 1_000_000:.4f} seconds={time.perf_counter() - started:.0f}"
    )
    if counts["stopped"]:
        print("Not finished. Wait a few minutes and run the same command again: it continues.")
    return 1 if counts["stopped"] else 0


def main() -> int:
    sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--limit", type=int, default=0, help="at most N documents")
    parser.add_argument("--rpm", type=float, default=12, help="documents per minute")
    parser.add_argument("--chars", type=int, default=6000, help="characters read per document")
    parser.add_argument("--retry-failed", action="store_true", help="also retry failed documents")
    parser.add_argument("--schema", action="store_true", help="send JSON schema to provider")
    args = parser.parse_args()
    if args.limit < 0 or args.chars <= 0 or args.rpm <= 0:
        parser.error("--limit must be nonnegative; --chars and --rpm must be positive")
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
