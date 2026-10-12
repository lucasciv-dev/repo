from pathlib import Path

import pytest

from market_research import analysis, report, research
from market_research.models import Post
from market_research.sources.hackernews import HackerNewsSource
from market_research.sources.reddit import RedditSource


class FakeHttp:
    """Returns canned JSON keyed by a URL substring."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def get_json(self, url, **kwargs):
        self.calls.append(url)
        for key, value in self.routes.items():
            if key in url:
                return value
        raise RuntimeError(f"no route for {url}")


REDDIT_SEARCH = {"data": {"children": [{"kind": "t3", "data": {
    "id": "abc", "title": "Cleaning my retainer is so gross", "selftext": "It smells no matter what I do.",
    "permalink": "/r/Invisalign/comments/abc/x/", "author": "u1", "score": 120,
    "created_utc": 1700000000, "subreddit": "Invisalign"}}]}}

REDDIT_COMMENTS = [{}, {"data": {"children": [
    {"kind": "t1", "data": {"body": "I wish there was a little UV box that cleaned it overnight. I would pay $40 for that.",
                            "permalink": "/r/Invisalign/comments/abc/x/c1/", "author": "u2", "score": 50,
                            "replies": {"data": {"children": [
                                {"kind": "t1", "data": {"body": "I tried the tablets and they didn't work for me.",
                                                        "permalink": "/c2/", "author": "u3", "score": 5, "replies": ""}}]}}}},
    {"kind": "t1", "data": {"body": "[deleted]", "permalink": "/c3/", "score": 0}},
    {"kind": "more", "data": {}},
]}}]


def test_reddit_source_walks_comment_tree(monkeypatch):
    monkeypatch.delenv("REDDIT_CLIENT_ID", raising=False)
    http = FakeHttp({"/search.json": REDDIT_SEARCH, "/comments/abc.json": REDDIT_COMMENTS})
    posts = RedditSource(http).search(["cleaning retainers"], limit=50)
    assert [p.kind for p in posts] == ["post", "comment", "comment"]
    assert posts[0].context == "r/Invisalign" and posts[0].score == 120
    assert "UV box" in posts[1].text
    assert posts[2].text.startswith("I tried")


def test_hackernews_strips_html():
    http = FakeHttp({"hn.algolia.com": {"hits": [
        {"objectID": "1", "comment_text": "<p>Retainer cleaning is <i>annoying</i></p>", "author": "a",
         "points": None, "story_title": "Ask HN"}]}})
    posts = HackerNewsSource(http).search(["retainer"], limit=10)
    assert posts[0].text == "Retainer cleaning is annoying"


def test_extract_finds_complaints_wishes_and_pay():
    p = Post(source="reddit", text="Cleaning my retainer is so annoying. I wish there was a self-cleaning case. "
                                   "Honestly I would pay for that. I tried denture tablets.")
    m = analysis.extract(p)
    assert any("annoying" in s for s in m["complaints"])
    assert any("I wish" in s for s in m["wishes"])
    assert m["pay"] and m["tried"]


def test_relevance_filter_uses_stems_and_context():
    terms = analysis.query_terms("cleaning retainers")
    assert terms == ["cleaning", "retainers"]
    assert analysis.is_relevant(Post(source="x", text="how do you clean a retainer?"), terms)
    assert not analysis.is_relevant(Post(source="x", text="my cat is cute"), terms)


def test_sentiment_summary_weights_engagement():
    posts = [Post(source="a", text="I love this, amazing!", score=1000), Post(source="a", text="Terrible, awful.", score=0)]
    analysis.score_posts(posts)
    s = analysis.sentiment_summary(posts)
    assert s["overall"]["label"] == "positive"
    assert s["overall"]["positive_pct"] == 50.0


def test_problem_search_end_to_end(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("REDDIT_CLIENT_ID", raising=False)
    fake = FakeHttp({"/search.json": REDDIT_SEARCH, "/comments/abc.json": REDDIT_COMMENTS})
    monkeypatch.setattr(research, "Http", lambda: fake)
    result = research.problem_search("cleaning retainers", sources=["reddit"])
    assert result["demand_signals"]["posts_with_wishes"] >= 1
    assert result["demand_signals"]["willingness_to_pay_mentions"] >= 1
    assert any("UV box" in w["quote"] for w in result["wishes"])
    folder = report.write(result, tmp_path)
    md = (folder / "report.md").read_text()
    assert "# Problem Search: cleaning retainers" in md and "UV box" in md
    assert (folder / "data.json").exists() and (folder / "posts.csv").exists()


def test_unknown_source_rejected():
    with pytest.raises(ValueError):
        research.collect(["x"], ["myspace"], 10, False)
