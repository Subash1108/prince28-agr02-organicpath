"""Parse every downloaded file into pages in Postgres. Safe to run again: it only does what is new.

uv run python scripts/parse_corpus.py                 parse what is not parsed yet
uv run python scripts/parse_corpus.py --limit 20      only the first 20 new files
uv run python scripts/parse_corpus.py --retry-failed  try the files in parse_failures again
uv run python scripts/parse_corpus.py --refresh-html --path data/raw/example/page.html
  uv run python scripts/parse_corpus.py --retry-failed --ocr eng   read scans with Tesseract
"""

import argparse
import asyncio
import json
import sys
import time
from collections import Counter
from pathlib import Path

from organicpath.config import get_settings
from organicpath.db.session import make_engine, make_sessionmaker
from organicpath.ingest.parse import ParsedDoc, ParseError, parse_file, parse_pdf_ocr
from organicpath.ingest.store import (
    document_id,
    failed_paths,
    parsed_ids,
    save_document,
    save_failure,
)

MANIFEST = Path("data/manifest.jsonl")
HTML_SUFFIXES = {".html", ".htm"}


def load_records() -> list[dict]:
    """The newest manifest line per URL, for files that are really on disk."""
    latest: dict[str, dict] = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        latest[record["url"]] = record
    return [r for r in latest.values() if r["status"] == "downloaded" and Path(r["path"]).is_file()]


def select_records(records: list[dict], paths: list[str], refresh_html: bool) -> list[dict]:
    """Limit selected manifest records; HTML refresh mode can never include other types."""
    if refresh_html and not paths:
        return [r for r in records if Path(r["path"]).suffix.lower() in HTML_SUFFIXES]
    if refresh_html:
        non_html = [path for path in paths if Path(path).suffix.lower() not in HTML_SUFFIXES]
        if non_html:
            raise ValueError("--refresh-html accepts only .html/.htm paths: " + ", ".join(non_html))

    if not paths:
        return records
    requested = set(paths)
    selected = [record for record in records if record["path"] in requested]
    missing = requested - {record["path"] for record in selected}
    if missing:
        raise ValueError("not downloaded or not present: " + ", ".join(sorted(missing)))
    return selected


def parse_one(path: Path, ocr_language: str) -> ParsedDoc:
    """Parse normally; if the PDF is a scan and --ocr was given, read it with Tesseract."""
    try:
        return parse_file(path)
    except ParseError as error:
        if error.reason != "no_text_layer" or not ocr_language:
            raise
        return parse_pdf_ocr(path, ocr_language)


async def run(args: argparse.Namespace) -> int:
    try:
        records = select_records(load_records(), args.paths, args.refresh_html)
    except ValueError as error:
        print(error)
        return 1
    engine = make_engine(get_settings())
    counts: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    pages = 0
    started = time.perf_counter()
    async with make_sessionmaker(engine)() as session:
        done, failed = await parsed_ids(session), await failed_paths(session)
        todo = []
        scheduled: set[str] = set()
        for record in records:
            external_id = document_id(record["sha256"])
            is_html = Path(record["path"]).suffix.lower() in HTML_SUFFIXES
            if external_id in scheduled:
                continue
            if external_id in done and args.refresh_html and is_html:
                todo.append(record)
                scheduled.add(external_id)
                counts["refresh_queued"] += 1
            elif external_id in done:
                counts["already_parsed"] += 1
            elif record["path"] in failed and not args.retry_failed:
                counts["failed_before"] += 1
            else:
                done.add(external_id)  # two URLs, same bytes: parse once
                scheduled.add(external_id)
                todo.append(record)
        for number, record in enumerate(todo[: args.limit or None], start=1):
            try:
                parsed = await asyncio.to_thread(parse_one, Path(record["path"]), args.ocr)
                await save_document(session, record, parsed)
                counts["parsed"] += 1
                pages += len(parsed.pages)
            except ParseError as error:
                await session.rollback()
                await save_failure(session, record, error)
                counts["failed"] += 1
                reasons[error.reason] += 1
                print(f"failed  {error.reason:<16} {record['path']}", flush=True)
            if number % 50 == 0:
                print(f"... {number} of {len(todo)} files", flush=True)
    await engine.dispose()
    took = time.perf_counter() - started
    summary = " ".join(f"{name}={count}" for name, count in sorted(counts.items()))
    print(f"files={len(records)} {summary} pages={pages} seconds={took:.1f}")
    if reasons:
        print("failure reasons: " + ", ".join(f"{r}={n}" for r, n in reasons.most_common()))
    return 0


def main() -> int:
    sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--limit", type=int, default=0, help="parse at most N new files")
    parser.add_argument("--retry-failed", action="store_true", help="retry files that failed")
    parser.add_argument(
        "--refresh-html", action="store_true", help="reparse existing HTML and replace its pages"
    )
    parser.add_argument(
        "--path",
        dest="paths",
        action="append",
        default=[],
        help="restrict work to this manifest path",
    )
    parser.add_argument("--ocr", default="", metavar="LANG", help="OCR scanned PDFs, e.g. eng")
    args = parser.parse_args()
    if not MANIFEST.exists():
        print("data/manifest.jsonl not found: collect your corpus first (Day 6)")
        return 1
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
