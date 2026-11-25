"""Command line: python -m epr {fetch,verify,build,all}."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="epr", description=__doc__)
    parser.add_argument("command", choices=["fetch", "verify", "build", "all"])
    args = parser.parse_args(argv)

    if args.command in ("fetch", "all"):
        from .fetch import fetch_all
        fetch_all()

    if args.command in ("verify", "build", "all"):
        from .fetch import verify_manifest
        problems = verify_manifest()
        if problems:
            print("raw snapshot does not match manifest:", *problems, sep="\n  ", file=sys.stderr)
            return 2

    if args.command in ("build", "all"):
        from .build import build
        return build()
    return 0


if __name__ == "__main__":
    sys.exit(main())
