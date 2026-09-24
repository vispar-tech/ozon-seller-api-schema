"""Command-line entry point: fetch, validate, and store the schema."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ozon_schema_fetcher.fetcher import DEFAULT_TIMEOUT_MS, SCHEMA_URL, fetch_schema
from ozon_schema_fetcher.validation import validate_schema

DEFAULT_OUT = Path("schemas/ozon-seller-api-openapi.json")
JSON_INDENT = 2


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list without the program name; ``None`` reads ``sys.argv``.

    Returns:
        The parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        prog="ozon-schema-fetcher",
        description="Download the Ozon Seller API OpenAPI schema via Camoufox.",
    )
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"output JSON path (default: {DEFAULT_OUT})",
    )
    parser.add_argument(
        "--url",
        default=SCHEMA_URL,
        help="schema URL to fetch (default: %(default)s)",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=DEFAULT_TIMEOUT_MS,
        help="overall navigation budget in ms (default: %(default)s)",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="run the browser with a visible window (debugging)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Fetch the schema, validate it, and write it to disk.

    Args:
        argv: Argument list without the program name; ``None`` reads ``sys.argv``.

    Returns:
        Process exit code (``0`` on success).
    """
    args = _parse_args(argv)
    data = fetch_schema(url=args.url, timeout_ms=args.timeout_ms, headed=args.headed)
    validate_schema(data)
    out: Path = args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        data,
        ensure_ascii=False,
        indent=JSON_INDENT,
        sort_keys=True,
    )
    # Atomic replace: a kill mid-write cannot clobber the committed schema.
    tmp = out.with_suffix(out.suffix + ".tmp")
    try:
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(out)
    finally:
        tmp.unlink(missing_ok=True)
    print(f"OK: {len(data['paths'])} paths -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
