"""Command-line entrypoint for the OpenObserve MCP package."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .config import DEFAULT_CONFIG_TEMPLATE, default_config_path
from .server import main as serve_main


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="openobserve-mcp", description="OpenObserve Community stdio MCP server")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("serve", help="Run the stdio MCP server")
    subparsers.add_parser("config-path", help="Print the default user config path")

    init_parser = subparsers.add_parser("init-config", help="Create a sample user config file")
    init_parser.add_argument("--force", action="store_true", help="Overwrite the file if it already exists")
    init_parser.add_argument("--path", help="Write the config to a custom path instead of the default XDG path")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command in {None, "serve"}:
        return serve_main()
    if args.command == "config-path":
        print(default_config_path())
        return 0
    if args.command == "init-config":
        target_path = Path(args.path).expanduser() if args.path else default_config_path()
        _write_example_config(target_path, force=args.force)
        print(target_path)
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


def _write_example_config(path: Path, *, force: bool) -> None:
    if path.exists() and not force:
        raise SystemExit(f"Config file already exists: {path}. Use --force to overwrite it.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(DEFAULT_CONFIG_TEMPLATE, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
