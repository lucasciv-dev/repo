"""Small HTTP helper with retries, polite rate limiting and robots.txt checks."""
from __future__ import annotations

import logging
import time
import urllib.robotparser
from urllib.parse import urlparse

import requests

log = logging.getLogger(__name__)

USER_AGENT = "market-research-tool/0.1 (+personal product research)"


class Http:
    def __init__(self, min_interval: float = 1.0, timeout: float = 20.0, retries: int = 3):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.min_interval = min_interval
        self.timeout = timeout
        self.retries = retries
        self._last: dict[str, float] = {}
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}

    def _throttle(self, host: str) -> None:
        wait = self.min_interval - (time.monotonic() - self._last.get(host, 0.0))
        if wait > 0:
            time.sleep(wait)
        self._last[host] = time.monotonic()

    def allowed_by_robots(self, url: str) -> bool:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        if base not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                resp = self.session.get(base + "/robots.txt", timeout=self.timeout)
                rp.parse(resp.text.splitlines() if resp.ok else [])
                self._robots[base] = rp
            except requests.RequestException:
                self._robots[base] = None
        rp = self._robots[base]
        return True if rp is None else rp.can_fetch(USER_AGENT, url)

    def get(self, url: str, **kwargs) -> requests.Response:
        host = urlparse(url).netloc
        kwargs.setdefault("timeout", self.timeout)
        delay = 2.0
        for attempt in range(self.retries + 1):
            self._throttle(host)
            try:
                resp = self.session.get(url, **kwargs)
            except requests.RequestException:
                if attempt == self.retries:
                    raise
            else:
                if resp.status_code not in (429, 500, 502, 503, 504) or attempt == self.retries:
                    resp.raise_for_status()
                    return resp
                log.info("HTTP %s from %s, retrying in %.0fs", resp.status_code, host, delay)
            time.sleep(delay)
            delay *= 2
        raise RuntimeError("unreachable")

    def get_json(self, url: str, **kwargs):
        return self.get(url, **kwargs).json()

    def post(self, url: str, **kwargs) -> requests.Response:
        kwargs.setdefault("timeout", self.timeout)
        self._throttle(urlparse(url).netloc)
        resp = self.session.post(url, **kwargs)
        resp.raise_for_status()
        return resp
