"""Reddit: posts + top comments.

Uses the official OAuth API (app-only) when REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET
are set (create a free "script" app at https://www.reddit.com/prefs/apps).
Falls back to the public .json endpoints, which Reddit throttles heavily.
"""
from __future__ import annotations

import logging
import os
from urllib.parse import quote_plus

from ..models import Post
from .base import Source

log = logging.getLogger(__name__)


class RedditSource(Source):
    name = "reddit"

    def __init__(self, http, comments_per_post: int = 30, posts_with_comments: int = 10):
        super().__init__(http)
        self.comments_per_post = comments_per_post
        self.posts_with_comments = posts_with_comments
        self._token: str | None = None

    def _base(self) -> tuple[str, dict, str]:
        cid, secret = os.getenv("REDDIT_CLIENT_ID"), os.getenv("REDDIT_CLIENT_SECRET")
        if cid and secret:
            if self._token is None:
                resp = self.http.post(
                    "https://www.reddit.com/api/v1/access_token",
                    auth=(cid, secret),
                    data={"grant_type": "client_credentials"},
                )
                self._token = resp.json()["access_token"]
            return "https://oauth.reddit.com", {"Authorization": f"bearer {self._token}"}, ""
        return "https://www.reddit.com", {}, ".json"

    def search(self, queries: list[str], limit: int) -> list[Post]:
        base, headers, ext = self._base()
        posts: dict[str, Post] = {}
        ids: list[tuple[str, str]] = []
        per_query = max(10, min(100, limit // max(1, len(queries)) + 5))
        for q in queries:
            url = f"{base}/search{ext}?q={quote_plus(q)}&sort=relevance&t=all&limit={per_query}&raw_json=1"
            try:
                data = self.http.get_json(url, headers=headers)
            except Exception as exc:  # noqa: BLE001 - keep other queries going
                log.warning("reddit search failed for %r: %s", q, exc)
                continue
            for child in data.get("data", {}).get("children", []):
                d = child.get("data", {})
                pid = d.get("id")
                if not pid or pid in posts:
                    continue
                posts[pid] = Post(
                    source=self.name,
                    title=d.get("title", ""),
                    text=d.get("selftext", ""),
                    url="https://www.reddit.com" + d.get("permalink", ""),
                    author=d.get("author", ""),
                    score=int(d.get("score", 0)),
                    created_utc=d.get("created_utc"),
                    context="r/" + d.get("subreddit", ""),
                    kind="post",
                )
                ids.append((pid, d.get("subreddit", "")))

        results = list(posts.values())
        # Comments are where most of the real opinions live.
        ranked = sorted(ids, key=lambda x: -posts[x[0]].score)[: self.posts_with_comments]
        for pid, sub in ranked:
            url = f"{base}/comments/{pid}{ext}?limit={self.comments_per_post}&sort=top&raw_json=1"
            try:
                data = self.http.get_json(url, headers=headers)
            except Exception as exc:  # noqa: BLE001
                log.warning("reddit comments failed for %s: %s", pid, exc)
                continue
            if isinstance(data, list) and len(data) > 1:
                parent = posts[pid]
                for c in _walk_comments(data[1])[: self.comments_per_post]:
                    results.append(
                        Post(
                            source=self.name,
                            text=c.get("body", ""),
                            url="https://www.reddit.com" + c.get("permalink", ""),
                            author=c.get("author", ""),
                            score=int(c.get("score", 0)),
                            created_utc=c.get("created_utc"),
                            context=f"r/{sub} · {parent.title[:80]}",
                            kind="comment",
                        )
                    )
        return results[:limit] if limit else results


def _walk_comments(listing: dict) -> list[dict]:
    out: list[dict] = []
    stack = list(reversed(listing.get("data", {}).get("children", [])))
    while stack:
        node = stack.pop()
        if node.get("kind") != "t1":
            continue
        d = node.get("data", {})
        if d.get("body") and d.get("body") not in ("[deleted]", "[removed]"):
            out.append(d)
        replies = d.get("replies")
        if isinstance(replies, dict):
            stack.extend(reversed(replies.get("data", {}).get("children", [])))
    return out
