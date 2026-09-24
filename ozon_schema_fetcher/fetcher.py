"""Fetch the Ozon Seller API OpenAPI schema through a stealth browser."""

from __future__ import annotations

import time
from typing import Any

from camoufox.sync_api import Camoufox
from playwright.sync_api import Error, Page

SCHEMA_URL = "https://docs.ozon.ru/api/seller/swagger.json"
DEFAULT_TIMEOUT_MS = 120_000
RETRY_DELAY_MS = 2_000

_SECONDS_PER_MILLISECOND = 1_000


def _goto_schema(page: Page, url: str, timeout_ms: int) -> dict[str, Any]:
    """Navigate to ``url`` until a parseable JSON body survives Qrator.

    docs.ozon.ru sits behind Qrator anti-bot protection: a plain HTTP client
    (or a browser that has not solved the JS challenge yet) gets a 307 redirect
    back to the challenge page instead of the document. The content type alone
    is unreliable in both directions (challenge HTML served as application/json,
    real JSON served as text/plain), so the body is sniffed by attempting to
    decode it: only a payload that parses as JSON counts as a hit. Navigation
    errors (``net::ERR_*``, TLS failures, Playwright's own timeout, all
    subclasses of ``playwright.Error``) and undecodable bodies are retried
    until the deadline passes.

    Args:
        page: Playwright page used for navigation.
        url: Target URL of the OpenAPI schema.
        timeout_ms: Overall budget for all attempts combined.

    Returns:
        The schema decoded from the JSON response body.

    Raises:
        TimeoutError: No parseable JSON body arrived within ``timeout_ms``;
            the message includes the last encountered error, if any.
    """
    deadline = time.monotonic() + timeout_ms / _SECONDS_PER_MILLISECOND
    last_error: Exception | None = None
    while True:
        remaining_ms = (deadline - time.monotonic()) * _SECONDS_PER_MILLISECOND
        if remaining_ms <= 0:
            msg = (
                f"Qrator challenge not passed within {timeout_ms} ms: "
                f"no JSON response from {url}"
            )
            if last_error is not None:
                msg = f"{msg} (last error: {last_error})"
            raise TimeoutError(msg)
        try:
            response = page.goto(
                url, wait_until="domcontentloaded", timeout=remaining_ms
            )
        except Error as exc:
            # Back off on failure so an outage does not hammer the network.
            last_error = exc
            response = None
        if response is not None:
            try:
                # Body sniff: challenge HTML (or any non-JSON body) fails here.
                return response.json()
            except (ValueError, Error) as exc:
                # Not JSON, or body unavailable (e.g. redirect): retry.
                last_error = exc
        # Recompute the budget: goto may have consumed most of it.
        remaining_ms = (deadline - time.monotonic()) * _SECONDS_PER_MILLISECOND
        if remaining_ms > 0:
            page.wait_for_timeout(min(RETRY_DELAY_MS, remaining_ms))


def fetch_schema(
    url: str = SCHEMA_URL,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    headed: bool = False,
) -> dict[str, Any]:
    """Download and parse the OpenAPI schema with a stealth Firefox.

    Uses Camoufox (stealth Playwright Firefox) so the Qrator JS challenge on
    docs.ozon.ru is solved in a real browser session; a plain HTTP request
    would loop on 307 redirects.

    Args:
        url: Schema URL to fetch.
        timeout_ms: Overall navigation budget in milliseconds.
        headed: Run with a visible browser window (debugging aid).

    Returns:
        The schema decoded from JSON.
    """
    with Camoufox(headless=not headed) as browser:
        page = browser.new_page()
        return _goto_schema(page, url, timeout_ms)
