# SPDX-FileCopyrightText: 2026 Siddhant Tiwari
# SPDX-License-Identifier: AGPL-3.0-only
"""Parser and request tests do not contact Ollama."""

import json
from unittest.mock import Mock

import pytest

from nlp_engine import NLPEngine


@pytest.fixture
def engine():
    instance = NLPEngine.__new__(NLPEngine)
    instance.model = "synthetic-test-model"
    instance.generate_endpoint = "http://localhost:11434/api/generate"
    return instance


@pytest.mark.parametrize("response", [
    '{"topics": ["Synthetic Topic"]}',
    '```json\n{"topics": ["Synthetic Topic"]}\n```',
    '["Synthetic Topic"]',
])
def test_supported_json_formats(engine, response):
    assert engine._parse_topics_json(response) == ["Synthetic Topic"]


def test_topic_and_word_limits(engine):
    raw = ["one two three four five six"] * 12
    assert engine._parse_topics_json(json.dumps({"topics": raw})) == ["one two three four five"] * 10


def test_invalid_json_does_not_log_response(engine, caplog):
    with pytest.raises(ValueError):
        engine._parse_topics_json("SYNTHETIC_PRIVATE_CONTENT_NOT_FOR_LOGS")
    assert "SYNTHETIC_PRIVATE_CONTENT_NOT_FOR_LOGS" not in caplog.text


def test_empty_transcript_does_not_send_request(engine, monkeypatch):
    request = Mock(side_effect=AssertionError("Network call is not allowed"))
    monkeypatch.setattr("nlp_engine.requests.post", request)
    assert engine.extract_topics("  ") == []
    request.assert_not_called()


def test_generation_request_and_retry(engine, monkeypatch):
    invalid = Mock()
    invalid.json.return_value = {"response": "not-json"}
    valid = Mock()
    valid.json.return_value = {"response": '{"topics": ["Synthetic Topic"]}'}
    request = Mock(side_effect=[invalid, valid])
    monkeypatch.setattr("nlp_engine.requests.post", request)
    assert engine.extract_topics("Synthetic lecture.", course_name="Synthetic Course") == ["Synthetic Topic"]
    assert request.call_count == 2
    payload = request.call_args.kwargs["json"]
    assert payload["stream"] is False
    assert payload["format"] == "json"
    assert "Synthetic Course" in payload["prompt"]
