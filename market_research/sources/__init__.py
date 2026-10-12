"""Data sources. `build_sources` returns every enabled source."""
from __future__ import annotations

from ..http import Http
from .base import Source
from .hackernews import HackerNewsSource
from .reddit import RedditSource
from .websearch import SITES, WebSearchSource
from .youtube import YouTubeSource

ALL_SOURCES = ["reddit", "youtube", "hackernews", *SITES]


def build_sources(names: list[str] | None, http: Http, fetch_pages: bool = False) -> list[Source]:
    names = names or ALL_SOURCES
    unknown = set(names) - set(ALL_SOURCES)
    if unknown:
        raise ValueError(f"unknown source(s): {', '.join(sorted(unknown))}. Choose from: {', '.join(ALL_SOURCES)}")
    out: list[Source] = []
    for n in names:
        if n == "reddit":
            out.append(RedditSource(http))
        elif n == "youtube":
            out.append(YouTubeSource(http))
        elif n == "hackernews":
            out.append(HackerNewsSource(http))
        else:
            out.append(WebSearchSource(http, n, fetch_pages=fetch_pages))
    return out
