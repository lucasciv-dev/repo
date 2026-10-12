"""Site-restricted web search: Quora, Facebook, Instagram, Amazon, TikTok, Trustpilot, forums.

Facebook, Instagram, TikTok and Amazon require logins and forbid scraping in their
terms, so instead of scraping them directly we search them through a search API
(Brave Search or SerpApi) and collect the public snippets the search engine indexed.
Set BRAVE_API_KEY (https://api-dashboard.search.brave.com, free tier) or SERPAPI_KEY.

Optionally (`fetch_pages=True`) the full text of open forum/blog pages is downloaded,
but only for domains outside NO_FETCH and only when robots.txt allows it.
"""
from __future__ import annotations

import logging
import os
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from ..models import Post
from .base import Source

log = logging.getLogger(__name__)

# source name -> site: filter ("" = open web, aimed at forums / communities)
SITES = {
    "quora": "site:quora.com",
    "facebook": "site:facebook.com",
    "instagram": "site:instagram.com",
    "amazon": "site:amazon.com",
    "tiktok": "site:tiktok.com",
    "trustpilot": "site:trustpilot.com",
    "forums": "(forum OR community OR discussion OR thread) -site:reddit.com -site:amazon.com",
}

# Login-walled or scraping-prohibited: snippets only, never fetch the page.
NO_FETCH = ("facebook.com", "instagram.com", "amazon.", "tiktok.com", "quora.com", "reddit.com")


class WebSearchSource(Source):
    """One instance per site; `name` is the site key from SITES."""

    def __init__(self, http, site: str, fetch_pages: bool = False, max_queries: int = 3):
        super().__init__(http)
        self.name = site
        self.site_filter = SITES[site]
        self.fetch_pages = fetch_pages
        self.max_queries = max_queries

    def available(self) -> tuple[bool, str]:
        if os.getenv("BRAVE_API_KEY") or os.getenv("SERPAPI_KEY"):
            return True, ""
        return False, "set BRAVE_API_KEY or SERPAPI_KEY to search Quora/Facebook/Instagram/Amazon/forums"

    def _query(self, q: str, count: int) -> list[dict]:
        full = f"{q} {self.site_filter}"
        if os.getenv("BRAVE_API_KEY"):
            data = self.http.get_json(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": full, "count": min(20, count), "extra_snippets": "true"},
                headers={"X-Subscription-Token": os.environ["BRAVE_API_KEY"], "Accept": "application/json"},
            )
            return [
                {"title": r.get("title", ""), "url": r.get("url", ""),
                 "snippet": " ".join([r.get("description", "")] + r.get("extra_snippets", []))}
                for r in data.get("web", {}).get("results", [])
            ]
        data = self.http.get_json(
            "https://serpapi.com/search.json",
            params={"engine": "google", "q": full, "num": min(100, count), "api_key": os.environ["SERPAPI_KEY"]},
        )
        return [
            {"title": r.get("title", ""), "url": r.get("link", ""), "snippet": r.get("snippet", "")}
            for r in data.get("organic_results", [])
        ]

    def search(self, queries: list[str], limit: int) -> list[Post]:
        seen: set[str] = set()
        out: list[Post] = []
        for q in queries[: self.max_queries]:
            try:
                results = self._query(q, count=20)
            except Exception as exc:  # noqa: BLE001
                log.warning("%s web search failed for %r: %s", self.name, q, exc)
                continue
            for r in results:
                url = r["url"]
                if not url or url in seen:
                    continue
                seen.add(url)
                text = _clean(r["snippet"])
                if self.fetch_pages and not any(d in urlparse(url).netloc for d in NO_FETCH):
                    text = self._fetch(url) or text
                if not text:
                    continue
                out.append(Post(source=self.name, title=_clean(r["title"]), text=text, url=url,
                                context=urlparse(url).netloc, kind="snippet"))
        return out[:limit]

    def _fetch(self, url: str) -> str:
        try:
            if not self.http.allowed_by_robots(url):
                return ""
            resp = self.http.get(url)
        except Exception as exc:  # noqa: BLE001
            log.info("could not fetch %s: %s", url, exc)
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
            tag.decompose()
        paras = [p.get_text(" ", strip=True) for p in soup.find_all(["p", "li", "blockquote"])]
        return "\n".join(p for p in paras if len(p) > 40)[:20000]


def _clean(s: str) -> str:
    return BeautifulSoup(s or "", "html.parser").get_text(" ", strip=True)
