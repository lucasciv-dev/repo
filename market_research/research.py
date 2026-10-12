"""The two tools: product sentiment research and Problem Search."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from . import analysis
from .http import Http
from .models import Post
from .sources import build_sources

log = logging.getLogger(__name__)


def product_queries(product: str) -> list[str]:
    return [f"{product} review", f"{product} worth it", f"{product} problems", product]


def problem_queries(problem: str) -> list[str]:
    return [problem, f"{problem} annoying", f'{problem} "I wish"', f"{problem} help",
            f'{problem} "is there a"', f"best way {problem}"]


def collect(queries: list[str], sources: list[str] | None, limit: int, fetch_pages: bool) -> tuple[list[Post], dict]:
    """Run all sources in parallel. Returns (posts, status-per-source)."""
    http = Http()
    status: dict[str, str] = {}
    active = []
    for src in build_sources(sources, http, fetch_pages=fetch_pages):
        ok, reason = src.available()
        if ok:
            active.append(src)
        else:
            status[src.name] = f"skipped: {reason}"

    def run(src):
        try:
            return src.name, src.search(queries, limit), None
        except Exception as exc:  # noqa: BLE001 - one broken source must not kill the run
            return src.name, [], exc

    posts: list[Post] = []
    with ThreadPoolExecutor(max_workers=max(1, len(active))) as pool:
        for name, items, err in pool.map(run, active):
            if err:
                status[name] = f"error: {err}"
                log.warning("%s failed: %s", name, err)
            else:
                status[name] = f"{len(items)} items"
                posts.extend(items)
    return _dedupe(posts), status


def _dedupe(posts: list[Post]) -> list[Post]:
    seen: set[str] = set()
    out = []
    for p in posts:
        key = p.url or p.full_text[:200]
        if key in seen or not p.full_text.strip():
            continue
        seen.add(key)
        out.append(p)
    return out


def research_product(product: str, sources=None, limit: int = 200, fetch_pages: bool = False) -> dict:
    posts, status = collect(product_queries(product), sources, limit, fetch_pages)
    terms = analysis.query_terms(product)
    posts = [p for p in posts if analysis.is_relevant(p, terms)]
    analysis.score_posts(posts)
    neg = [s for p in posts for s in analysis.sentences(p.full_text) if analysis.sentiment(s) <= -0.3]
    pos = [s for p in posts for s in analysis.sentences(p.full_text) if analysis.sentiment(s) >= 0.3]
    return {
        "mode": "product",
        "subject": product,
        "source_status": status,
        "sentiment": analysis.sentiment_summary(posts),
        "praise_themes": analysis.themes(pos, terms),
        "complaint_themes": analysis.themes(neg, terms),
        "top_positive": analysis.extreme_posts(posts, positive=True),
        "top_negative": analysis.extreme_posts(posts, positive=False),
        "complaints": analysis.top_quotes(posts, "complaints"),
        "wishes": analysis.top_quotes(posts, "wishes"),
        "posts": posts,
    }


def problem_search(problem: str, sources=None, limit: int = 200, fetch_pages: bool = False) -> dict:
    posts, status = collect(problem_queries(problem), sources, limit, fetch_pages)
    terms = analysis.query_terms(problem)
    posts = [p for p in posts if analysis.is_relevant(p, terms)]
    analysis.score_posts(posts)
    complaint_sents = [s for p in posts for s in p.matches.get("complaints", [])]
    wish_sents = [s for p in posts for s in p.matches.get("wishes", [])]
    signals = {
        "posts_analyzed": len(posts),
        "posts_with_complaints": sum(1 for p in posts if "complaints" in p.matches),
        "posts_with_wishes": sum(1 for p in posts if "wishes" in p.matches),
        "willingness_to_pay_mentions": sum(len(p.matches.get("pay", [])) for p in posts),
        "total_engagement": sum(max(p.score, 0) for p in posts),
    }
    return {
        "mode": "problem",
        "subject": problem,
        "source_status": status,
        "demand_signals": signals,
        "sentiment": analysis.sentiment_summary(posts),
        "pain_point_themes": analysis.themes(complaint_sents, terms),
        "wished_solution_themes": analysis.themes(wish_sents, terms),
        "complaints": analysis.top_quotes(posts, "complaints", n=25),
        "wishes": analysis.top_quotes(posts, "wishes", n=25),
        "willing_to_pay": analysis.top_quotes(posts, "pay", n=10),
        "tried_solutions": analysis.top_quotes(posts, "tried", n=15),
        "posts": posts,
    }
