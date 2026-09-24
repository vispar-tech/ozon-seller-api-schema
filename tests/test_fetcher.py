"""Tests for the stealth-browser schema fetcher."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import Mock, patch

import pytest
from playwright.sync_api import Error, Page

from ozon_schema_fetcher.fetcher import (
    DEFAULT_TIMEOUT_MS,
    RETRY_DELAY_MS,
    SCHEMA_URL,
    _goto_schema,
    fetch_schema,
)

SCHEMA_PAYLOAD: dict[str, Any] = {
    "openapi": "3.0.0",
    "info": {"title": "x", "version": 2.1},
    "paths": {"/v1/seller/info": {}},
}
TEST_TIMEOUT_MS = 30_000
EXHAUSTED_TIMEOUT_MS = 1
LAST_ERROR_TIMEOUT_MS = 50
RETRY_ATTEMPTS = 2


def test_goto_schema_returns_parsed_json_on_first_attempt() -> None:
    """Return the decoded body when the first response parses as JSON."""
    page: Mock = Mock(spec=Page)
    response: Mock = Mock()
    response.json.return_value = SCHEMA_PAYLOAD
    page.goto.return_value = response

    result = _goto_schema(cast(Page, page), SCHEMA_URL, TEST_TIMEOUT_MS)

    assert result == SCHEMA_PAYLOAD
    page.goto.assert_called_once()


def test_goto_schema_retries_after_navigation_error() -> None:
    """Retry when navigation fails, then return the next successful body."""
    page: Mock = Mock(spec=Page)
    response: Mock = Mock()
    response.json.return_value = SCHEMA_PAYLOAD
    page.goto.side_effect = [Error("net::ERR_CONNECTION_REFUSED"), response]

    result = _goto_schema(cast(Page, page), SCHEMA_URL, TEST_TIMEOUT_MS)

    assert result == SCHEMA_PAYLOAD
    assert page.goto.call_count == RETRY_ATTEMPTS
    page.wait_for_timeout.assert_called_once()


def test_goto_schema_retries_when_response_is_none() -> None:
    """Retry when navigation yields no response (same-document), then succeed."""
    page: Mock = Mock(spec=Page)
    response: Mock = Mock()
    response.json.return_value = SCHEMA_PAYLOAD
    page.goto.side_effect = [None, response]

    result = _goto_schema(cast(Page, page), SCHEMA_URL, TEST_TIMEOUT_MS)

    assert result == SCHEMA_PAYLOAD
    assert page.goto.call_count == RETRY_ATTEMPTS


def test_goto_schema_retries_when_body_is_unavailable() -> None:
    """Retry when response.json() raises playwright.Error, then succeed."""
    page: Mock = Mock(spec=Page)
    broken: Mock = Mock()
    broken.json.side_effect = Error("Response body is not available")
    response: Mock = Mock()
    response.json.return_value = SCHEMA_PAYLOAD
    page.goto.side_effect = [broken, response]

    result = _goto_schema(cast(Page, page), SCHEMA_URL, TEST_TIMEOUT_MS)

    assert result == SCHEMA_PAYLOAD
    assert page.goto.call_count == RETRY_ATTEMPTS


def test_goto_schema_retry_sleep_is_clamped() -> None:
    """Clamp the retry sleep above zero and at most RETRY_DELAY_MS."""
    page: Mock = Mock(spec=Page)
    response: Mock = Mock()
    response.json.return_value = SCHEMA_PAYLOAD
    page.goto.side_effect = [Error("net::ERR_TIMED_OUT"), response]

    _goto_schema(cast(Page, page), SCHEMA_URL, TEST_TIMEOUT_MS)

    page.wait_for_timeout.assert_called_once()
    sleep_ms = page.wait_for_timeout.call_args.args[0]
    assert 0 < sleep_ms <= RETRY_DELAY_MS


def test_goto_schema_retries_when_body_is_not_json() -> None:
    """Retry when the challenge body does not parse, then return JSON."""
    page: Mock = Mock(spec=Page)
    challenge: Mock = Mock()
    challenge.json.side_effect = ValueError("Expecting value")
    response: Mock = Mock()
    response.json.return_value = SCHEMA_PAYLOAD
    page.goto.side_effect = [challenge, response]

    result = _goto_schema(cast(Page, page), SCHEMA_URL, TEST_TIMEOUT_MS)

    assert result == SCHEMA_PAYLOAD
    assert page.goto.call_count == RETRY_ATTEMPTS


def test_goto_schema_raises_timeout_when_budget_exhausted() -> None:
    """Raise the custom TimeoutError once the deadline passes."""
    page: Mock = Mock(spec=Page)
    page.goto.side_effect = Error("net::ERR_TIMED_OUT")

    with pytest.raises(
        TimeoutError,
        match="Qrator challenge not passed within 1 ms",
    ):
        _goto_schema(cast(Page, page), SCHEMA_URL, EXHAUSTED_TIMEOUT_MS)


def test_goto_schema_raises_timeout_when_body_never_parses() -> None:
    """Raise the TimeoutError when bodies never decode as JSON in time."""
    page: Mock = Mock(spec=Page)
    challenge: Mock = Mock()
    challenge.json.side_effect = ValueError("Expecting value")
    page.goto.return_value = challenge

    with pytest.raises(
        TimeoutError,
        match="Qrator challenge not passed within 1 ms",
    ):
        _goto_schema(cast(Page, page), SCHEMA_URL, EXHAUSTED_TIMEOUT_MS)


def test_goto_schema_timeout_reports_last_error() -> None:
    """Append the most recent navigation error to the timeout message."""
    page: Mock = Mock(spec=Page)
    page.goto.side_effect = Error("net::ERR_CONNECTION_REFUSED")

    with pytest.raises(
        TimeoutError,
        match=r"\(last error: net::ERR_CONNECTION_REFUSED\)",
    ):
        _goto_schema(cast(Page, page), SCHEMA_URL, LAST_ERROR_TIMEOUT_MS)


def test_fetch_schema_returns_parsed_schema() -> None:
    """Return the goto result and run a headless browser by default."""
    with (
        patch("ozon_schema_fetcher.fetcher.Camoufox") as camoufox_mock,
        patch(
            "ozon_schema_fetcher.fetcher._goto_schema",
            return_value=SCHEMA_PAYLOAD,
        ) as goto_mock,
    ):
        result = fetch_schema()

    browser = camoufox_mock.return_value.__enter__.return_value
    assert result == SCHEMA_PAYLOAD
    camoufox_mock.assert_called_once_with(headless=True)
    browser.new_page.assert_called_once_with()
    goto_mock.assert_called_once_with(
        browser.new_page.return_value,
        SCHEMA_URL,
        DEFAULT_TIMEOUT_MS,
    )


def test_fetch_schema_headed_runs_visible_browser() -> None:
    """Run a visible browser window when headed=True."""
    with (
        patch("ozon_schema_fetcher.fetcher.Camoufox") as camoufox_mock,
        patch("ozon_schema_fetcher.fetcher._goto_schema", return_value=SCHEMA_PAYLOAD),
    ):
        fetch_schema(headed=True)

    camoufox_mock.assert_called_once_with(headless=False)
