import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from google.genai.errors import ClientError

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


@pytest.mark.parametrize(
    "name,side_effect,expected_result,expected_exception,expected_calls,error_contains",
    [
        (
            "retry_then_success",
            [
                TimeoutError("timed out"),
                FakeResp("recovered"),
            ],
            "recovered",
            None,
            2,
            None,
        ),
        (
            "retry_exhaustion",
            TimeoutError("boom"),
            None,
            RuntimeError,
            None,
            "failed after",
        ),
        (
            "non_retryable_error",
            ClientError(400, {"message": "bad"}),
            None,
            RuntimeError,
            1,
            None,
        ),
    ],
)
def test_retry_behaviour(
    name,
    side_effect,
    expected_result,
    expected_exception,
    expected_calls,
    error_contains,
):
    with patch("app.agents._get_client") as get_client:
        get_client.return_value.models.generate_content.side_effect = side_effect

        if expected_exception:
            with pytest.raises(expected_exception) as exc_info:
                call_llm("sys", "usr")

            if error_contains:
                assert error_contains in str(exc_info.value)
        else:
            result = call_llm("sys", "usr")
            assert result == expected_result

        if expected_calls is not None:
            assert (
                get_client.return_value.models.generate_content.call_count
                == expected_calls
            )


def test_timeout_stops_long_hanging_call():
    with patch("app.agents._get_client") as get_client, patch(
        "app.agents.settings"
    ) as mock_settings:
        mock_settings.gemini_retry_attempts = 2
        mock_settings.gemini_request_timeout = 0.1
        mock_settings.gemini_backoff_base = 0.01
        mock_settings.gemini_backoff_max = 0.05

        get_client.return_value.models.generate_content.side_effect = (
            lambda *a, **k: time.sleep(10)
        )

        with pytest.raises(RuntimeError):
            call_llm("sys", "usr", max_tokens=1200)

    assert get_client.return_value.models.generate_content.call_count >= 1