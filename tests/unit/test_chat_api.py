"""Tests for /v1/chat and /v1/usage using the fake model."""

import json

from organicpath.llm.gateway import LLMError


def events(body: str) -> list[tuple[str, dict]]:
    out = []
    for block in body.strip().split("\n\n"):
        name = ""
        for line in block.splitlines():
            if line.startswith("event:"):
                name = line[6:].strip()
            elif line.startswith("data:"):
                out.append((name, json.loads(line[5:])))
    return out


def test_chat_without_streaming_returns_json(client, llm):
    llm.script = ["Use curly braces in the path."]
    response = client.post(
        "/v1/chat", json={"message": "How do I declare a path parameter?", "stream": False}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Use curly braces in the path."
    assert body["provider"] == "fake" and body["tokens_out"] == 6 and "cost_inr" in body


def test_chat_streams_pieces_and_ends_with_done(client, llm):
    llm.script = ["Use curly braces in the path."]
    response = client.post("/v1/chat", json={"message": "How do I declare a path parameter?"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    received = events(response.text)
    answer = "".join(data["delta"] for name, data in received if name == "")
    assert answer.strip() == "Use curly braces in the path."
    assert received[-1][0] == "done" and received[-1][1]["model"] == "fake-1"


def test_model_gets_system_prompt_from_file(client):
    prompt = client.app.state.system_prompt
    assert "not sure" in prompt
    assert "at least three years of organic management" in prompt
    assert "section 3.1.3(ii), printed page 22" in prompt


def test_empty_message_is_422(client):
    response = client.post("/v1/chat", json={"message": ""})
    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"


def test_unavailable_model_returns_503(client, llm):
    llm.script = [LLMError("HTTP 401: invalid API key", retryable=False)]
    response = client.post("/v1/chat", json={"message": "hello"})
    assert response.status_code == 503
    assert "No model could answer" in response.json()["detail"]


def test_midstream_failure_is_error_event(client, llm):
    llm.script = [("partial", LLMError("HTTP 503: overloaded", retryable=True))]
    response = client.post("/v1/chat", json={"message": "hello"})
    assert response.status_code == 200
    assert events(response.text)[-1][0] == "error"


def test_usage_reports_tokens_and_cost(client):
    response = client.get("/v1/usage")
    assert response.status_code == 200
    body = response.json()
    assert body["days"][0]["tokens_in"] == 300 and body["total_cost_inr"] == 0.0642
    assert body["calls"] == 3
