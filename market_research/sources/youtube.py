"""YouTube comments via the YouTube Data API v3 (needs YOUTUBE_API_KEY, free quota)."""
from __future__ import annotations

import logging
import os
from datetime import datetime

from ..models import Post
from .base import Source

log = logging.getLogger(__name__)
API = "https://www.googleapis.com/youtube/v3"


class YouTubeSource(Source):
    name = "youtube"

    def __init__(self, http, videos_per_query: int = 5, comments_per_video: int = 50):
        super().__init__(http)
        self.videos_per_query = videos_per_query
        self.comments_per_video = comments_per_video

    def available(self) -> tuple[bool, str]:
        if os.getenv("YOUTUBE_API_KEY"):
            return True, ""
        return False, "set YOUTUBE_API_KEY to enable YouTube comments"

    def search(self, queries: list[str], limit: int) -> list[Post]:
        key = os.environ["YOUTUBE_API_KEY"]
        videos: dict[str, str] = {}
        for q in queries:
            try:
                data = self.http.get_json(
                    f"{API}/search",
                    params={"part": "snippet", "q": q, "type": "video",
                            "maxResults": self.videos_per_query, "key": key},
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("youtube search failed for %r: %s", q, exc)
                continue
            for item in data.get("items", []):
                vid = item.get("id", {}).get("videoId")
                if vid:
                    videos.setdefault(vid, item.get("snippet", {}).get("title", ""))

        out: list[Post] = []
        for vid, title in videos.items():
            try:
                data = self.http.get_json(
                    f"{API}/commentThreads",
                    params={"part": "snippet", "videoId": vid, "maxResults": min(100, self.comments_per_video),
                            "order": "relevance", "textFormat": "plainText", "key": key},
                )
            except Exception as exc:  # noqa: BLE001 - comments disabled etc.
                log.info("youtube comments unavailable for %s: %s", vid, exc)
                continue
            for item in data.get("items", []):
                s = item["snippet"]["topLevelComment"]["snippet"]
                ts = s.get("publishedAt")
                out.append(
                    Post(
                        source=self.name,
                        text=s.get("textDisplay", ""),
                        url=f"https://www.youtube.com/watch?v={vid}&lc={item['id']}",
                        author=s.get("authorDisplayName", ""),
                        score=int(s.get("likeCount", 0)),
                        created_utc=datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp() if ts else None,
                        context=title,
                        kind="comment",
                    )
                )
        return out[:limit]
