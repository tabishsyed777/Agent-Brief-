from __future__ import annotations

import argparse
from pathlib import Path

from .agent import run, write_result


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a cited research brief from supplied sources.")
    parser.add_argument("question")
    parser.add_argument("--source", action="append", required=True, help="HTTP(S) source URL; may be repeated")
    parser.add_argument("--out", type=Path, required=True, help="New directory for brief.md and run.json")
    args = parser.parse_args()
    try:
        result = run(args.question, args.source)
        write_result(args.out, result)
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

