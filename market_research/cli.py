"""Command line entry point.

    python -m market_research product "retainer cleaner tablets"
    python -m market_research problem "cleaning retainers" --ai
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from . import analysis, report
from .research import problem_search, research_product
from .sources import ALL_SOURCES


def _load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="market-research", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="mode", required=True)
    for name, help_ in (("product", "User sentiment about a product"),
                        ("problem", "Problem Search: complaints + wished-for solutions")):
        p = sub.add_parser(name, help=help_)
        p.add_argument("query", help="product name or problem description")
        p.add_argument("--sources", help=f"comma-separated subset of: {','.join(ALL_SOURCES)}")
        p.add_argument("--limit", type=int, default=200, help="max items per source (default 200)")
        p.add_argument("--fetch-pages", action="store_true",
                       help="download full text of open forum pages found by web search (respects robots.txt)")
        p.add_argument("--ai", action="store_true", help="add a Claude-written analysis (needs ANTHROPIC_API_KEY)")
        p.add_argument("--out", default="reports", help="output directory (default: reports/)")
        p.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    _load_dotenv()
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s %(message)s")
    sources = [s.strip() for s in args.sources.split(",")] if args.sources else None

    run = research_product if args.mode == "product" else problem_search
    try:
        result = run(args.query, sources=sources, limit=args.limit, fetch_pages=args.fetch_pages)
    except ValueError as exc:
        parser.error(str(exc))

    for name, st in sorted(result["source_status"].items()):
        print(f"  {name:<11} {st}", file=sys.stderr)

    ai_summary = None
    if args.ai and result["posts"]:
        from .llm import synthesize
        ranked = sorted(result["posts"], key=analysis.weight, reverse=True)
        try:
            ai_summary = synthesize(args.mode, args.query, ranked)
        except Exception as exc:  # noqa: BLE001 - still write the non-AI report
            print(f"AI summary failed: {exc}", file=sys.stderr)

    folder = report.write(result, Path(args.out), ai_summary)
    print(f"\n{len(result['posts'])} relevant items. Report: {folder / 'report.md'}")
    return 0 if result["posts"] else 1


if __name__ == "__main__":
    sys.exit(main())
