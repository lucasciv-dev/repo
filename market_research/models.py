"""Shared data types."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Post:
    """One piece of user-generated text from any source."""

    source: str  # e.g. "reddit", "hackernews", "youtube", "quora", "amazon"
    text: str
    url: str = ""
    title: str = ""
    author: str = ""
    score: int = 0  # upvotes / likes, used to weight results
    created_utc: float | None = None
    context: str = ""  # subreddit, video title, site name, ...
    kind: str = "post"  # "post", "comment", "review", "snippet"
    # Filled in by analysis
    sentiment: float | None = None
    matches: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def full_text(self) -> str:
        return f"{self.title}\n{self.text}".strip() if self.title else self.text
