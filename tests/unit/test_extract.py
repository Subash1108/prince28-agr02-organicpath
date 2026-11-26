"""Structured extraction and validation using a fake model."""

from pathlib import Path
from typing import Literal

import pytest
from pydantic import BaseModel, Field, ValidationError

from organicpath.llm.doc_meta import DocMeta
from organicpath.llm.extract import extract, parse_json
from organicpath.llm.gateway import FakeLLM, LLMGateway
from organicpath.llm.prompts import latest, read_prompt


class Notice(BaseModel):
    kind: Literal["circular", "guideline"]
    year: int = Field(ge=1950, le=2027)


GOOD = '{"kind": "circular", "year": 2024}'


async def ask(gateway, **options):
    return await extract(
        gateway, Notice, "Fill the record.", "extract_v1", "Fee circular", "New fees.", **options
    )


def test_parse_json_handles_fences_and_chatter_and_rejects_invalid_json():
    assert parse_json('Sure:\n```json\n{"kind":"circular"}\n```') == {"kind": "circular"}
    for reply in ("I cannot do that.", "[1, 2, 3]", '{"kind": }'):
        with pytest.raises(ValueError):
            parse_json(reply)


async def test_valid_reply_is_accepted_and_schema_is_in_messages():
    llm = FakeLLM(script=[GOOD])
    out = await ask(LLMGateway([llm]))
    assert out.record == Notice(kind="circular", year=2024)
    assert out.attempts == 1 and out.errors == []
    system, user = llm.seen[0]["messages"]
    assert '"year"' in system["content"]
    assert user["content"] == "Title: Fee circular\n<document>\nNew fees.\n</document>"


async def test_rejected_reply_is_repaired_with_reason_and_tokens_accumulate():
    llm = FakeLLM(script=['{"kind":"circular","year":3024}', GOOD])
    out = await ask(LLMGateway([llm]))
    assert out.record.year == 2024 and out.attempts == 2
    assert "less than or equal to 2027" in out.errors[0] and out.tokens_in == 24
    rejected, repair = llm.seen[1]["messages"][-2:]
    assert rejected["role"] == "assistant" and "3024" in rejected["content"]
    assert "rejected" in repair["content"] and "2027" in repair["content"]


async def test_three_bad_replies_leave_no_record():
    llm = FakeLLM(script=["I cannot do that.", '{"kind":"poem","year":2024}', "{}"])
    out = await ask(LLMGateway([llm]))
    assert out.record is None and out.attempts == 3 and llm.calls == 3
    assert "no JSON object" in out.errors[0] and "kind" in out.errors[1]
    assert "Field required" in out.errors[2]


async def test_native_schema_is_forwarded_when_requested():
    llm = FakeLLM(script=[GOOD, GOOD])
    await ask(LLMGateway([llm]))
    await ask(LLMGateway([llm]), native_schema=True)
    assert "response_format" not in llm.seen[0]
    spec = llm.seen[1]["response_format"]["json_schema"]
    assert spec["name"] == "Notice" and "year" in spec["schema"]["properties"]


def test_doc_meta_is_strict_and_prompt_describes_every_field():
    good = {
        "doc_kind": "guideline",
        "year": 2022,
        "language": "en",
        "summary": "Guidance on organic certification requirements for farmer groups.",
        "topics": [" NPOP ", "npop", "Conversion"],
        "standard": ["NPOP"],
    }
    assert DocMeta.model_validate(good).topics == ["npop", "conversion"]
    for change in ({"year": 3024}, {"doc_kind": "poem"}, {"surprise": 1}, {"topics": []}):
        with pytest.raises(ValidationError):
            DocMeta.model_validate({**good, **change})
    prompt = read_prompt(Path("prompts"), latest(Path("prompts"), "extract"))
    missing = [name for name in DocMeta.model_fields if name not in prompt]
    assert not missing, f"extract prompt does not mention: {missing}"
