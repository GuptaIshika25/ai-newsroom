"""Entrypoint: python -m src.main [--dry-run] [--date YYYY-MM-DD]"""

import argparse
from src.orchestrator import run


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Newsroom — daily AI audio brief")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip all LLM calls and email; reuse existing DB state and mp3.",
    )
    parser.add_argument(
        "--date",
        metavar="YYYY-MM-DD",
        default=None,
        help="Run for a specific date instead of today.",
    )
    args = parser.parse_args()
    run(run_date=args.date, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
