import pytest

from scripts.parse_corpus import select_records

RECORDS = [
    {"path": "data/raw/example/page.html"},
    {"path": "data/raw/example/report.pdf"},
]


def test_refresh_html_without_paths_selects_only_html():
    assert select_records(RECORDS, [], refresh_html=True) == [RECORDS[0]]


def test_path_limited_html_refresh_rejects_non_html_paths_before_processing():
    with pytest.raises(ValueError, match="only .html/.htm paths"):
        select_records(RECORDS, [RECORDS[1]["path"]], refresh_html=True)


def test_path_limited_html_refresh_selects_only_the_requested_record():
    assert select_records(RECORDS, [RECORDS[0]["path"]], refresh_html=True) == [RECORDS[0]]


def test_path_limit_reports_paths_that_are_not_in_the_manifest():
    with pytest.raises(ValueError, match="not downloaded or not present"):
        select_records(RECORDS, ["data/raw/other/not-downloaded.html"], refresh_html=False)
