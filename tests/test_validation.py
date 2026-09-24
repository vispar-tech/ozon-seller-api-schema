"""Tests for the OpenAPI schema validator."""

from __future__ import annotations

from typing import Any

import pytest

from ozon_schema_fetcher.validation import validate_schema


def _valid_schema() -> dict[str, Any]:
    """Build a minimal valid OpenAPI 3 document."""
    return {
        "openapi": "3.0.0",
        "info": {"title": "x", "version": 2.1},
        "paths": {"/v1/seller/info": {}},
    }


def test_valid_schema_is_accepted() -> None:
    """Accept a minimal valid schema without raising."""
    validate_schema(_valid_schema())


@pytest.mark.parametrize("data", [[], "payload", None])
def test_non_dict_is_rejected(data: Any) -> None:
    """Reject payloads that are not JSON objects."""
    with pytest.raises(ValueError, match="Schema must be a JSON object"):
        validate_schema(data)


def test_missing_openapi_is_rejected() -> None:
    """Reject a document without the openapi version field."""
    schema = _valid_schema()
    del schema["openapi"]
    with pytest.raises(ValueError, match="Schema 'openapi'"):
        validate_schema(schema)


def test_empty_openapi_is_rejected() -> None:
    """Reject an empty openapi version."""
    schema = _valid_schema()
    schema["openapi"] = ""
    with pytest.raises(ValueError, match="Schema 'openapi'"):
        validate_schema(schema)


def test_non_string_openapi_is_rejected() -> None:
    """Reject a numeric openapi version."""
    schema = _valid_schema()
    schema["openapi"] = 123
    with pytest.raises(ValueError, match="Schema 'openapi'"):
        validate_schema(schema)


def test_openapi_v2_is_rejected() -> None:
    """Reject an OpenAPI 2 (swagger) document."""
    schema = _valid_schema()
    schema["openapi"] = "2.0"
    with pytest.raises(ValueError, match="Schema 'openapi'"):
        validate_schema(schema)


def test_missing_paths_is_rejected() -> None:
    """Reject a document without a paths object."""
    schema = _valid_schema()
    del schema["paths"]
    with pytest.raises(ValueError, match="Schema 'paths'"):
        validate_schema(schema)


def test_empty_paths_is_rejected() -> None:
    """Reject a document with an empty paths object."""
    schema = _valid_schema()
    schema["paths"] = {}
    with pytest.raises(ValueError, match="Schema 'paths'"):
        validate_schema(schema)


def test_non_dict_paths_is_rejected() -> None:
    """Reject a document whose paths is not an object."""
    schema = _valid_schema()
    schema["paths"] = "/v1/seller/info"
    with pytest.raises(ValueError, match="Schema 'paths'"):
        validate_schema(schema)


def test_missing_info_is_rejected() -> None:
    """Reject a document without an info object."""
    schema = _valid_schema()
    del schema["info"]
    with pytest.raises(ValueError, match="Schema 'info'"):
        validate_schema(schema)


def test_missing_info_title_is_rejected() -> None:
    """Reject an info object without a title."""
    schema = _valid_schema()
    schema["info"] = {"version": 2.1}
    with pytest.raises(ValueError, match="Schema 'info'"):
        validate_schema(schema)


def test_empty_info_title_is_rejected() -> None:
    """Reject an info object with an empty title."""
    schema = _valid_schema()
    schema["info"] = {"title": "", "version": 2.1}
    with pytest.raises(ValueError, match="Schema 'info'"):
        validate_schema(schema)


def test_missing_info_version_is_rejected() -> None:
    """Reject an info object without a version."""
    schema = _valid_schema()
    schema["info"] = {"title": "x"}
    with pytest.raises(ValueError, match="Schema 'info'"):
        validate_schema(schema)
