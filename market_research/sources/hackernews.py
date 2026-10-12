"""Hacker News via the free Algolia search API (no key needed)."""
from __future__ import annotations

import logging
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from ..models import Post
from .base import Source

log = logging.getLogger(__name__)


class HackerNewsSource(Source):
    name = "hackernews"

    def search(self, queries: list[str], limit: int) -> list[Post]:
        seen: set[str] = set()
        out: list[Post] = []
        per_query = max(10, min(50, limit // max(1, len(queries)) + 5))
        for q in queries:
            url = (
                "https://hn.algolia.com/api/v1/search?query="
                f"{quote_plus(q)}&tags=(story,comment)&hitsPerPage={per_query}"
            )
            try:
                data = self.http.get_json(url)
            except Exception as exc:  # noqa: BLE001
                log.warning("hackernews search failed for %r: %s", q, exc)
                continue
            for h in data.get("hits", []):
                oid = h.get("objectID")
                if not oid or oid in seen:
                    continue
                seen.add(oid)
                html = h.get("comment_text") or h.get("story_text") or ""
                text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True) if html else ""
                title = h.get("title") or ""
                if not text and not title:
                    continue
                out.append(
                    Post(
                        source=self.name,
                        title=title,
                        text=text,
                        url=f"https://news.ycombinator.com/item?id={oid}",
                        author=h.get("author") or "",
                        score=int(h.get("points") or 0),
                        created_utc=h.get("created_at_i"),
                        context=h.get("story_title") or "",
                        kind="comment" if h.get("comment_text") else "post",
                    )
                )
        return out[:limit]
