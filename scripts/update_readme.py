"""Refresh the schema info block in a README from the fetched schema JSON."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

BEGIN_MARKER = "<!-- SCHEMA-BEGIN -->"
END_MARKER = "<!-- SCHEMA-END -->"
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M UTC"
TABLE_HEADER = "| Версия | Paths | Обновлено |"
TABLE_DIVIDER = "| --- | --- | --- |"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list without the program name; ``None`` reads ``sys.argv``.

    Returns:
        The parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        prog="update_readme",
        description="Rewrite the schema block in a README from a schema JSON file.",
    )
    parser.add_argument(
        "schema_path",
        type=Path,
        help="path to the OpenAPI schema JSON (info.version + paths)",
    )
    parser.add_argument(
        "readme_path",
        type=Path,
        help="path to the README whose schema block is updated",
    )
    return parser.parse_args(argv)


def _render_block(version: str, path_count: int, updated: str) -> str:
    """Render the schema block, markers included.

    Args:
        version: Schema version from ``info.version``.
        path_count: Number of paths in the schema.
        updated: Human-readable update timestamp.

    Returns:
        The block text without surrounding blank lines.
    """
    return (
        f"{BEGIN_MARKER}\n"
        f"{TABLE_HEADER}\n"
        f"{TABLE_DIVIDER}\n"
        f"| {version} | {path_count} | {updated} |\n"
        f"{END_MARKER}"
    )


def _insert_block(text: str, block: str) -> str:
    """Insert the block after the first top-level heading, or at the top.

    Args:
        text: README content without a usable marker pair.
        block: Rendered block including markers.

    Returns:
        README content with the block inserted.
    """
    lines = text.splitlines(keepends=True)
    heading = next(
        (index for index, line in enumerate(lines) if line.startswith("# ")),
        None,
    )
    if heading is None:
        remainder = text.lstrip("\n")
        return f"{block}\n\n{remainder}" if remainder else f"{block}\n"
    head = "".join(lines[: heading + 1]).rstrip("\n")
    tail = "".join(lines[heading + 1 :]).lstrip("\n")
    gap = "\n\n" if tail else "\n"
    return f"{head}\n\n{block}{gap}{tail}"


def _update_text(text: str, block: str) -> str:
    """Replace the marked block in place, or insert it when markers are absent.

    Args:
        text: Current README content.
        block: Rendered block including markers.

    Returns:
        README content with the block applied.

    Raises:
        ValueError: Exactly one SCHEMA marker is present, or both are present
            in the wrong order (END before BEGIN).
    """
    begin = text.find(BEGIN_MARKER)
    end = text.find(END_MARKER)
    if begin != -1 and end > begin:
        stop = end + len(END_MARKER)
        return f"{text[:begin]}{block}{text[stop:]}"
    if begin == -1 and end == -1:
        return _insert_block(text, block)
    msg = "unbalanced or misordered SCHEMA markers in README"
    raise ValueError(msg)


def main(argv: list[str] | None = None) -> int:
    """Update the README schema block from the schema JSON.

    Args:
        argv: Argument list without the program name; ``None`` reads ``sys.argv``.

    Returns:
        Process exit code (``0`` on success).
    """
    args = _parse_args(argv)
    schema: Path = args.schema_path
    readme: Path = args.readme_path
    # parse_float/parse_int=str keeps literal number tokens (2.10 stays "2.10"
    # instead of float 2.1); only info.version and len(paths) are consumed.
    data: dict[str, Any] = json.loads(
        schema.read_text(encoding="utf-8"),
        parse_float=str,
        parse_int=str,
    )
    version = str(data["info"]["version"])
    path_count = len(data["paths"])
    updated = datetime.now(UTC).strftime(TIMESTAMP_FORMAT)
    block = _render_block(version, path_count, updated)
    text = readme.read_text(encoding="utf-8") if readme.exists() else ""
    new_text = _update_text(text, block)
    if new_text != text:
        readme.write_text(new_text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
