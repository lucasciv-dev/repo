"""Source interface."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..http import Http
from ..models import Post


class Source(ABC):
    name: str = "base"

    def __init__(self, http: Http):
        self.http = http

    def available(self) -> tuple[bool, str]:
        """Return (usable, reason). Override when credentials are required."""
        return True, ""

    @abstractmethod
    def search(self, queries: list[str], limit: int) -> list[Post]:
        """Run every query variant and return up to `limit` posts."""
