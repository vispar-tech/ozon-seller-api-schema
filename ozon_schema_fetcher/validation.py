"""Validate the downloaded Ozon Seller API OpenAPI schema."""

from __future__ import annotations

from typing import Any


def validate_schema(data: Any) -> None:
    """Check that ``data`` looks like a usable OpenAPI 3 document.

    Args:
        data: Decoded JSON payload returned by the fetcher.

    Raises:
        ValueError: If the payload is not an OpenAPI 3.x object with a
            non-empty ``paths`` mapping, an ``info`` block with truthy
            ``title`` and ``version``.
    """
    if not isinstance(data, dict):
        msg = "Schema must be a JSON object"
        raise ValueError(msg)
    openapi = data.get("openapi")
    if not isinstance(openapi, str) or not openapi.startswith("3."):
        msg = "Schema 'openapi' must be a non-empty version string starting with '3.'"
        raise ValueError(msg)
    paths = data.get("paths")
    if not isinstance(paths, dict) or not paths:
        msg = "Schema 'paths' must be a non-empty object"
        raise ValueError(msg)
    info = data.get("info")
    if not isinstance(info, dict) or not info.get("title") or not info.get("version"):
        msg = "Schema 'info' must be an object with truthy 'title' and 'version'"
        raise ValueError(msg)
