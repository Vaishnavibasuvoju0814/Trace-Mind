import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents import call_llm


class FakeResp:
    def __init__(self, text):
        self.text = text


@pytest.fixture
def mock_client():
    with patch("app.agents._get_client") as get_client:
        yield get_client


@pytest.fixture
def mock_settings():
    with patch("app.agents.settings") as settings:
        yield settings


def test_successful_request(mock_client):
    mock_client.return_value.models.generate_content.return_value = FakeResp("ok")

    result = call_llm("sys", "usr")

    assert result == "ok"


def test_retryable_then_success(mock_client):
    calls = {"n": 0}

    def fake_generate(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise TimeoutError("timed out")
        return FakeResp("recovered")

    mock_client.return_value.models.generate_content.side_effect = fake_generate

    result = call_llm("sys", "usr")

    assert result == "recovered"
    assert calls["n"] == 2


def test_retry_exhaustion(mock_client):
    mock_client.return_value.models.generate_content.side_effect = TimeoutError("boom")

    with pytest.raises(RuntimeError) as exc_info:
        call_llm("sys", "usr")

    assert "failed after" in str(exc_info.value)


def test_non_retryable_fails_fast(mock_client):
    from google.genai.errors import ClientError

    mock_client.return_value.models.generate_content.side_effect = ClientError(
        400, {"message": "bad"}
    )

    with pytest.raises(RuntimeError):
        call_llm("sys", "usr")

    assert mock_client.return_value.models.generate_content.call_count == 1


def test_timeout_stops_long_hanging_call(mock_client, mock_settings):
    mock_settings.gemini_retry_attempts = 2
    mock_settings.gemini_request_timeout = 0.1
    mock_settings.gemini_backoff_base = 0.01
    mock_settings.gemini_backoff_max = 0.05

    mock_client.return_value.models.generate_content.side_effect = (
        lambda *a, **k: time.sleep(10)
    )

    with pytest.raises(RuntimeError):
        call_llm("sys", "usr", max_tokens=1200)

    assert mock_client.return_value.models.generate_content.call_count >= 1