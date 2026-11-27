"""The downloader, tested without the internet: httpx.MockTransport plays the website."""

import asyncio
import csv
import json
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pytest

import scripts.fetch as fetch_script
from organicpath.ingest import fetch
from organicpath.ingest.fetch import Source, fetch_all

SITE = "https://docs.example.org"


def make_sources(count: int) -> list[Source]:
    licence = "CC BY 4.0"
    return [Source(f"{SITE}/guide/page-{i}.html", "Example Docs", licence) for i in range(count)]


class FakeSite:
    """A tiny website. `plan` lists the status codes a path answers with before it says 200."""

    def __init__(self, robots: str | int = 404, plan: dict[str, list[int]] | None = None) -> None:
        self.robots = robots
        self.plan = plan or {}
        self.error_headers: dict[str, str] = {}
        self.hits: list[str] = []
        self.busy = 0
        self.max_busy = 0
        self.slept: list[float] = []

    async def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/robots.txt":
            if isinstance(self.robots, int):
                return httpx.Response(self.robots)
            return httpx.Response(200, text=self.robots)
        self.hits.append(path)
        self.busy += 1
        self.max_busy = max(self.max_busy, self.busy)
        await asyncio.sleep(0.005)  # let other downloads start, like a real network would
        self.busy -= 1
        queue = self.plan.get(path)
        status = queue.pop(0) if queue else 200
        if status != 200:
            return httpx.Response(status, headers=self.error_headers)
        return httpx.Response(200, html=f"<h1>{path}</h1>")

    async def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)  # record the wait instead of really waiting

    async def run(self, sources: list[Source], root: Path, **options) -> dict[str, int]:
        transport = httpx.MockTransport(self.handler)
        per_host_delay = options.pop("per_host_delay", 0)
        async with httpx.AsyncClient(transport=transport, follow_redirects=True) as client:
            return await fetch_all(
                sources,
                root=root,
                client=client,
                sleep=self.sleep,
                per_host_delay=per_host_delay,
                **options,
            )


def manifest(root: Path) -> list[dict]:
    lines = (root / "data" / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines]


def raw_files(root: Path) -> list[Path]:
    return [p for p in (root / "data" / "raw").rglob("*") if p.is_file()]


async def test_downloads_files_and_records_where_they_came_from(tmp_path):
    counts = await FakeSite().run(make_sources(3), tmp_path)
    assert counts == {"downloaded": 3, "skipped": 0, "blocked": 0, "failed": 0}
    record = manifest(tmp_path)[0]
    assert record["status"] == "downloaded" and record["licence"] == "CC BY 4.0"
    saved = tmp_path / record["path"]
    assert saved.parent == tmp_path / "data" / "raw" / "example-docs"
    assert saved.suffix == ".html" and saved.stat().st_size == record["bytes"]
    assert len(record["sha256"]) == 64


async def test_second_run_downloads_nothing(tmp_path):
    site = FakeSite()
    await site.run(make_sources(5), tmp_path)
    counts = await site.run(make_sources(5), tmp_path)
    assert counts["skipped"] == 5 and counts["downloaded"] == 0
    assert len(site.hits) == 5  # still five requests in total: nothing was fetched twice


async def test_resume_fetches_only_what_is_missing(tmp_path):
    site = FakeSite()
    await site.run(make_sources(3), tmp_path)  # the run that was "killed" after 3 files
    counts = await site.run(make_sources(8), tmp_path)
    assert counts == {"downloaded": 5, "skipped": 3, "blocked": 0, "failed": 0}
    assert len(site.hits) == 8 and len(set(site.hits)) == 8


async def test_deleted_file_is_downloaded_again(tmp_path):
    site = FakeSite()
    await site.run(make_sources(2), tmp_path)
    raw_files(tmp_path)[0].unlink()
    counts = await site.run(make_sources(2), tmp_path)
    assert counts["downloaded"] == 1 and counts["skipped"] == 1


async def test_retries_a_503_and_then_succeeds(tmp_path):
    site = FakeSite(plan={"/guide/page-0.html": [503, 503]})
    counts = await site.run(make_sources(1), tmp_path)
    assert counts["downloaded"] == 1
    assert manifest(tmp_path)[0]["attempts"] == 3
    assert len(site.slept) == 2  # it waited between the attempts


async def test_obeys_retry_after_on_429(tmp_path):
    site = FakeSite(plan={"/guide/page-0.html": [429]})
    site.error_headers = {"Retry-After": "7"}
    counts = await site.run(make_sources(1), tmp_path)
    assert counts["downloaded"] == 1
    assert site.slept and site.slept[0] >= 7


async def test_gives_up_after_max_attempts_and_leaves_no_file(tmp_path):
    site = FakeSite(plan={"/guide/page-0.html": [500] * 10})
    counts = await site.run(make_sources(1), tmp_path, max_attempts=3)
    assert counts["failed"] == 1 and len(site.hits) == 3
    record = manifest(tmp_path)[0]
    assert record["status"] == "failed" and record["http_status"] == 500
    assert raw_files(tmp_path) == []


async def test_404_is_not_retried(tmp_path):
    site = FakeSite(plan={"/guide/page-0.html": [404]})
    counts = await site.run(make_sources(1), tmp_path)
    assert counts["failed"] == 1 and len(site.hits) == 1 and site.slept == []


async def test_a_failed_file_is_tried_again_on_the_next_run(tmp_path):
    site = FakeSite(plan={"/guide/page-0.html": [404]})
    await site.run(make_sources(1), tmp_path)
    counts = await site.run(make_sources(1), tmp_path)
    assert counts["downloaded"] == 1


async def test_robots_disallow_means_never_requested(tmp_path):
    site = FakeSite(robots="User-agent: *\nDisallow: /guide/\n")
    counts = await site.run(make_sources(3), tmp_path)
    assert counts["blocked"] == 3 and site.hits == []


async def test_robots_longest_match_wins(tmp_path):
    site = FakeSite(robots="User-agent: *\nDisallow: /guide/\nAllow: /guide/page-1\n")
    counts = await site.run(make_sources(3), tmp_path)
    assert counts["blocked"] == 2 and site.hits == ["/guide/page-1.html"]


async def test_robots_server_error_blocks_the_whole_site(tmp_path):
    counts = await FakeSite(robots=503).run(make_sources(2), tmp_path)
    assert counts["blocked"] == 2


async def test_html_fallback_at_robots_url_blocks_the_whole_site(tmp_path):
    requests: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, html="<html>site home</html>")
        return httpx.Response(200, html="<html>document</html>")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        counts = await fetch_all(make_sources(2), root=tmp_path, client=client)

    assert counts["blocked"] == 2
    assert requests == ["/robots.txt"]


async def test_host_delay_includes_gap_between_robots_and_first_download(tmp_path):
    requests: list[tuple[str, float]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.url.path, asyncio.get_running_loop().time()))
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\n")
        return httpx.Response(200, html="<html>document</html>")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        counts = await fetch_all(make_sources(1), root=tmp_path, client=client, per_host_delay=0.05)

    assert counts["downloaded"] == 1
    assert [path for path, _ in requests] == ["/robots.txt", "/guide/page-0.html"]
    assert requests[1][1] - requests[0][1] >= 0.045


@pytest.mark.parametrize(
    "robots_response",
    [
        httpx.Response(200, text="User-agent: *\nDisallow: /sitemap.xml\n"),
        httpx.Response(200, html="<html>fallback page</html>"),
    ],
)
async def test_sitemap_door_checks_and_validates_robots_before_requesting_sitemap(
    tmp_path, robots_response
):
    requests: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        if request.url.path == "/robots.txt":
            return robots_response
        return httpx.Response(
            200,
            content=b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>',
            headers={"Content-Type": "application/xml"},
        )

    async def no_sleep(seconds: float) -> None:
        return None

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(PermissionError):
            await fetch_script.sitemap_urls(
                client,
                f"{SITE}/sitemap.xml",
                robots=fetch.Robots(client),
                gate=fetch.HostGate(0, no_sleep),
            )

    assert requests == ["/robots.txt"]


async def test_sitemap_index_recurses_after_robots_check(tmp_path):
    requests: list[str] = []
    sitemap_index = (
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"<sitemap><loc>{SITE}/child.xml</loc></sitemap></sitemapindex>"
    )
    child_sitemap = (
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"<url><loc>{SITE}/guide/doc.pdf</loc></url></urlset>"
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\n")
        if request.url.path == "/sitemap.xml":
            return httpx.Response(200, text=sitemap_index)
        return httpx.Response(200, text=child_sitemap)

    async def no_sleep(seconds: float) -> None:
        return None

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        pages = await fetch_script.sitemap_urls(
            client,
            f"{SITE}/sitemap.xml",
            robots=fetch.Robots(client),
            gate=fetch.HostGate(0, no_sleep),
        )

    assert pages == [f"{SITE}/guide/doc.pdf"]
    assert requests == ["/robots.txt", "/sitemap.xml", "/child.xml"]


async def test_never_more_than_max_concurrency_at_once(tmp_path):
    site = FakeSite()
    await site.run(make_sources(20), tmp_path, max_concurrency=4)
    assert 1 < site.max_busy <= 4


async def test_broken_connection_leaves_no_half_file(tmp_path):
    async def body():
        yield b"<h1>first half"
        raise httpx.ReadError("connection lost")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, content=body(), headers={"Content-Type": "text/html"})

    async def no_sleep(seconds: float) -> None:
        return None

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        counts = await fetch_all(
            make_sources(1), root=tmp_path, client=client, sleep=no_sleep, max_attempts=2
        )
    assert counts["failed"] == 1
    assert manifest(tmp_path)[0]["error"] == "ReadError"
    assert raw_files(tmp_path) == []  # no final file and no .part file


def test_backoff_grows_but_stays_inside_its_limits():
    for attempt in range(12):
        ceiling = min(60.0, 2.0**attempt)
        assert all(0 <= fetch.backoff_delay(attempt) <= ceiling for _ in range(50))


def test_retry_after_understands_seconds_and_dates():
    assert fetch.retry_after_seconds("120") == 120.0
    assert fetch.retry_after_seconds("Wed, 21 Oct 2015 07:28:00 GMT") == 0.0  # in the past
    assert fetch.retry_after_seconds("soon") is None
    assert fetch.retry_after_seconds(None) is None


def test_file_names_are_stable_and_safe():
    url = "https://example.org/files/Annual Report (2024): Final?.PDF"
    stem = fetch.file_stem(url)
    assert stem == fetch.file_stem(url)  # same URL, same name, every run
    assert stem != fetch.file_stem(url + "x")
    assert all(ch.isalnum() or ch == "-" for ch in stem)
    assert fetch.pick_ext("https://example.org/a/b.PDF", "text/html") == ".pdf"
    assert fetch.pick_ext("https://example.org/view.aspx?id=7", "application/pdf") == ".pdf"
    assert fetch.pick_ext("https://example.org/thing", "weird/type") == ".bin"


def test_read_sources_skips_notes_and_duplicates(tmp_path):
    path = tmp_path / "sources.csv"
    path.write_text(
        "# my notes\n"
        "url,source,licence,title\n"
        "https://example.org/a.pdf,example,CC BY 4.0,Report A\n"
        "\n"
        "https://example.org/a.pdf,example,CC BY 4.0,Report A again\n"
        'https://example.org/b.pdf,example,"Public, cite the page",\n',
        encoding="utf-8",
    )
    sources = fetch.read_sources(path)
    assert [s.url for s in sources] == ["https://example.org/a.pdf", "https://example.org/b.pdf"]
    assert sources[1].licence == "Public, cite the page"


def test_a_source_without_a_licence_is_refused(tmp_path):
    path = tmp_path / "sources.csv"
    path.write_text("url,source,licence,title\nhttps://example.org/a.pdf,example,,\n")
    with pytest.raises(ValueError, match="licence"):
        fetch.read_sources(path)


def test_a_source_without_a_hostname_is_refused(tmp_path):
    path = tmp_path / "sources.csv"
    path.write_text(
        "url,source,licence,title\nhttps:///missing-host.pdf,example,CC BY 4.0,Report\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="not an http"):
        fetch.read_sources(path)


@pytest.mark.parametrize(
    "licence",
    [
        "download permission pending",
        "reuse terms unverified",
        "permission could not be verified",
        "permission verification required",
        "download permission not confirmed",
        "licence terms unknown",
        "licence review pending",
        "terms must be verified before use",
    ],
)
def test_a_source_with_unverified_permissions_is_refused(tmp_path, licence):
    path = tmp_path / "sources.csv"
    path.write_text(
        f'url,source,licence,title\nhttps://example.org/a.pdf,example,"{licence}",Report\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unverified"):
        fetch.read_sources(path)


def test_project_source_rows_are_complete_and_keep_pgs_blocked():
    project_root = Path(__file__).resolve().parents[2]
    sources_path = project_root / "data" / "sources.csv"
    with sources_path.open(encoding="utf-8-sig", newline="") as handle:
        lines = (line for line in handle if line.strip() and not line.lstrip().startswith("#"))
        rows = list(csv.DictReader(lines))

    assert len(rows) == 30
    assert all(row["url"] and row["source"] and row["licence"] and row["title"] for row in rows)
    assert len({row["url"] for row in rows}) == 30
    for row in rows:
        parts = urlsplit(row["url"])
        assert parts.scheme in {"http", "https"} and parts.hostname
        if row["source"] == "apeda":
            assert parts.hostname == "apeda.gov.in" or parts.hostname.endswith(".apeda.gov.in")
            assert not fetch.permission_is_pending(row["licence"])
        else:
            assert row["source"] == "pgs_india"
            assert parts.hostname == "pgsindia-ncof.gov.in"
            assert fetch.permission_is_pending(row["licence"])

    with pytest.raises(ValueError, match="unverified"):
        fetch.read_sources(sources_path)

    manifest_path = project_root / "data" / "manifest.jsonl"
    if manifest_path.exists():
        assert "Revised_PGS_India_Guidlines.pdf" not in manifest_path.read_text(encoding="utf-8")
    pgs_raw = project_root / "data" / "raw" / "pgs-india"
    assert not pgs_raw.exists()


def test_other_fetch_doors_refuse_unverified_licences_before_network_or_registration(
    monkeypatch, tmp_path
):
    def unexpected_request(*args, **kwargs):
        pytest.fail("a pending source must be rejected before external or local collection")

    monkeypatch.setattr(fetch_script, "git", unexpected_request)
    assert fetch_script.cmd_repo(type("Args", (), {"licence": "permission pending"})()) == 1

    monkeypatch.setattr(fetch_script.httpx, "AsyncClient", unexpected_request)
    assert fetch_script.cmd_sitemap(type("Args", (), {"licence": "reuse unverified"})()) == 1

    manual_args = type(
        "Args",
        (),
        {
            "licence": "permission pending",
            "folder": tmp_path,
        },
    )()
    assert fetch_script.cmd_manual(manual_args) == 1
