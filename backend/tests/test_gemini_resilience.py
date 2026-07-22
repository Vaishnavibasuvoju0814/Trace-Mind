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


def test_successful_request():
    with patch("app.agents._get_client") as get_client:
        get_client.return_value.models.generate_content.return_value = FakeResp("ok")
        result = call_llm("sys", "usr")
    assert result == "ok"


def test_retryable_then_success():
    calls = {"n": 0}

    def fake_generate(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise TimeoutError("timed out")
        return FakeResp("recovered")

    with patch("app.agents._get_client") as get_client:
        get_client.return_value.models.generate_content.side_effect = fake_generate
        result = call_llm("sys", "usr")

    assert result == "recovered"
    assert calls["n"] == 2


def test_retry_exhaustion():
    with patch("app.agents._get_client") as get_client:
        get_client.return_value.models.generate_content.side_effect = TimeoutError("boom")
        with pytest.raises(RuntimeError) as exc_info:
            call_llm("sys", "usr")

    assert "failed after" in str(exc_info.value)


def test_non_retryable_fails_fast():
    from google.genai.errors import ClientError

    with patch("app.agents._get_client") as get_client:
        get_client.return_value.models.generate_content.side_effect = ClientError(
            400, {"message": "bad"}
        )
        with pytest.raises(RuntimeError):
            call_llm("sys", "usr")

    assert get_client.return_value.models.generate_content.call_count == 1


def test_timeout_stops_long_hanging_call():
    with patch("app.agents._get_client") as get_client, \
         patch("app.agents.settings") as mock_settings:
        mock_settings.gemini_retry_attempts = 2
        mock_settings.gemini_request_timeout = 0.1
        mock_settings.gemini_backoff_base = 0.01
        mock_settings.gemini_backoff_max = 0.05
        get_client.return_value.models.generate_content.side_effect = lambda *a, **k: time.sleep(10)
        with pytest.raises(RuntimeError):
            call_llm("sys", "usr", max_tokens=1200)

    assert get_client.return_value.models.generate_content.call_count >= 1
def test_retry_backoff_intervals():
    sleep_calls = []

    def fake_sleep(delay):
        sleep_calls.append(delay)

    with patch("app.agents._get_client") as get_client, \
         patch("app.agents.time.sleep", side_effect=fake_sleep), \
         patch("app.agents.settings") as mock_settings:

        mock_settings.gemini_retry_attempts = 4
        mock_settings.gemini_request_timeout = 1
        mock_settings.gemini_backoff_base = 0.1
        mock_settings.gemini_backoff_max = 0.25

        get_client.return_value.models.generate_content.side_effect = TimeoutError("boom")

        with pytest.raises(RuntimeError):
            call_llm("sys", "usr")

    assert sleep_calls == [0.1, 0.2, 0.25]
def test_retry_backoff_sequence():
    call_order = []

    def fake_generate(*args, **kwargs):
        call_order.append("request")
        raise TimeoutError("boom")

    def fake_sleep(delay):
        call_order.append(f"sleep:{delay}")

    with patch("app.agents._get_client") as get_client, \
         patch("app.agents.time.sleep", side_effect=fake_sleep), \
         patch("app.agents.settings") as mock_settings:

        mock_settings.gemini_retry_attempts = 3
        mock_settings.gemini_request_timeout = 1
        mock_settings.gemini_backoff_base = 0.1
        mock_settings.gemini_backoff_max = 1.0

        get_client.return_value.models.generate_content.side_effect = fake_generate

        with pytest.raises(RuntimeError):
            call_llm("sys", "usr")

    assert call_order == [
        "request",
        "sleep:0.1",
        "request",
        "sleep:0.2",
        "request",
    ]