"""Tests for the README schema-block updater (scripts/update_readme.py)."""

from __future__ import annotations

import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "update_readme.py"
README_NAME = "README.md"
SCHEMA_NAME = "schema.json"
BEGIN_MARKER = "<!-- SCHEMA-BEGIN -->"
END_MARKER = "<!-- SCHEMA-END -->"
README_TITLE = "# ozon-seller-api-schema"
SCHEMA_VERSION = "3.0.1"
FIXTURE_PATH_COUNT = 7
STALE_VERSION = "9.9"
STALE_PATH_COUNT = 1
STALE_TIMESTAMP = "2020-01-01 12:00 UTC"
EXIT_OK = 0
EXPECTED_VERSION = "2.10"
FLOAT_VERSION_PATH_COUNT = 1
FLOAT_VERSION_SCHEMA = (
    '{"openapi": "3.0.0", "info": {"version": 2.10}, "paths": {"/v1/a": {}}}'
)
OLD_BLOCK = (
    f"{BEGIN_MARKER}\n"
    "| Версия | Paths | Обновлено |\n"
    "| --- | --- | --- |\n"
    f"| {STALE_VERSION} | {STALE_PATH_COUNT} | {STALE_TIMESTAMP} |\n"
    f"{END_MARKER}"
)


def _load_script() -> Any:
    """Load scripts/update_readme.py as a module via importlib.

    Returns:
        The executed script module.
    """
    spec = importlib.util.spec_from_file_location("update_readme", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_update(tmp_path: Path, readme_text: str) -> int:
    """Write the fixtures, run the updater, and return its exit code.

    Args:
        tmp_path: Pytest-provided temporary directory.
        readme_text: Initial README content.

    Returns:
        The script exit code.
    """
    schema = tmp_path / SCHEMA_NAME
    readme = tmp_path / README_NAME
    paths: dict[str, dict[str, str]] = {
        f"/v1/fixture/{index}": {} for index in range(FIXTURE_PATH_COUNT)
    }
    payload = {"openapi": "3.0.0", "info": {"version": SCHEMA_VERSION}, "paths": paths}
    schema.write_text(json.dumps(payload), encoding="utf-8")
    readme.write_text(readme_text, encoding="utf-8")
    return _load_script().main([str(schema), str(readme)])


def test_update_readme_replaces_existing_block(tmp_path: Path) -> None:
    """Rewrite the marked block with fresh values from the schema."""
    original = f"{README_TITLE}\n\nIntro.\n\n{OLD_BLOCK}\n\nFooter.\n"

    exit_code = _run_update(tmp_path, original)

    updated = (tmp_path / README_NAME).read_text(encoding="utf-8")
    assert exit_code == EXIT_OK
    assert STALE_TIMESTAMP not in updated
    assert f"| {SCHEMA_VERSION} | {FIXTURE_PATH_COUNT} |" in updated


def test_update_readme_inserts_block_when_markers_absent(tmp_path: Path) -> None:
    """Insert the block after the first heading when no markers exist."""
    original = f"{README_TITLE}\n\nIntro text.\n"

    exit_code = _run_update(tmp_path, original)

    updated = (tmp_path / README_NAME).read_text(encoding="utf-8")
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    assert exit_code == EXIT_OK
    assert updated.index(BEGIN_MARKER) > updated.index(README_TITLE)
    assert updated.index(END_MARKER) > updated.index(BEGIN_MARKER)
    assert f"| {SCHEMA_VERSION} | {FIXTURE_PATH_COUNT} |" in updated
    assert today in updated
    assert "Intro text." in updated


def test_update_readme_leaves_rest_untouched(tmp_path: Path) -> None:
    """Keep every byte outside the markers byte-identical."""
    original = f"{README_TITLE}\n\nIntro.\n\n{OLD_BLOCK}\n\nFooter.\n"
    prefix = original[: original.index(BEGIN_MARKER)]
    suffix = original[original.index(END_MARKER) + len(END_MARKER) :]

    exit_code = _run_update(tmp_path, original)

    updated = (tmp_path / README_NAME).read_text(encoding="utf-8")
    assert exit_code == EXIT_OK
    assert updated.startswith(prefix)
    assert updated.endswith(suffix)


def test_update_readme_rejects_unbalanced_markers(tmp_path: Path) -> None:
    """Raise ValueError when exactly one SCHEMA marker is present."""
    for broken_marker in (BEGIN_MARKER, END_MARKER):
        original = f"{README_TITLE}\n\n{broken_marker}\n\nIntro.\n"

        with pytest.raises(ValueError, match="unbalanced or misordered SCHEMA markers"):
            _run_update(tmp_path, original)


def test_update_readme_rejects_misordered_markers(tmp_path: Path) -> None:
    """Raise ValueError when both markers exist but END precedes BEGIN."""
    original = f"{README_TITLE}\n\n{END_MARKER}\n\n{BEGIN_MARKER}\n\nIntro.\n"

    with pytest.raises(ValueError, match="unbalanced or misordered SCHEMA markers"):
        _run_update(tmp_path, original)


def test_update_readme_preserves_literal_float_version(tmp_path: Path) -> None:
    """Keep the literal version token (2.10) instead of float 2.1."""
    schema = tmp_path / SCHEMA_NAME
    readme = tmp_path / README_NAME
    schema.write_text(FLOAT_VERSION_SCHEMA, encoding="utf-8")
    readme.write_text(f"{README_TITLE}\n", encoding="utf-8")

    exit_code = _load_script().main([str(schema), str(readme)])

    updated = readme.read_text(encoding="utf-8")
    assert exit_code == EXIT_OK
    assert f"| {EXPECTED_VERSION} | {FLOAT_VERSION_PATH_COUNT} |" in updated
