"""Sentiment scoring, complaint / wish extraction and theme mining (no API key needed)."""
from __future__ import annotations

import math
import re
from collections import Counter

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from .models import Post

_vader = SentimentIntensityAnalyzer()

STOPWORDS = set("""
a about above after again against all am an and any are aren't as at be because been before being below
between both but by can can't cannot could couldn't did didn't do does doesn't doing don't down during each
few for from further had hadn't has hasn't have haven't having he her here hers herself him himself his how
i i'd i'll i'm i've if in into is isn't it it's its itself just let's like me more most my myself no nor not
now of off on once only or other ought our ours ourselves out over own same she should shouldn't so some
such than that that's the their theirs them themselves then there there's these they they're this those
through to too under until up very was wasn't we we're were weren't what when where which while who whom
why will with won't would wouldn't you you're your yours yourself yourselves also get got really one would
much even still use used using thing things way make made lot im dont doesnt cant ive youre thats got
amp https http www com gt lt etc yeah yes ok okay people anyone someone something actually pretty good
know think going want need go see say said well back first time new us
""".split())

COMPLAINT_PATTERNS = [
    r"\b(hate|hated|hates)\b", r"\bannoy(ing|ed|s)?\b", r"\bfrustrat(ing|ed|ion)\b", r"\bpain in the\b",
    r"\bso hard to\b", r"\b(hard|difficult|impossible) to\b", r"\bstruggl(e|ing|ed)\b", r"\bgross\b",
    r"\bdisgusting\b", r"\b(smells?|stinks?|smelly)\b", r"\bnightmare\b", r"\bsucks?\b", r"\bworst\b",
    r"\bwaste of (money|time)\b", r"\bbroke(n)? (after|within)\b", r"\b(doesn't|didn't|does not|did not|won't) work\b",
    r"\bstopped working\b", r"\bfell apart\b", r"\bcheap(ly)? made\b", r"\btired of\b", r"\bsick of\b",
    r"\bproblem (is|with)\b", r"\bissue (is|with)\b", r"\bthe worst part\b", r"\bdrives me (crazy|nuts)\b",
    r"\bugh+\b", r"\bnever (works|worked)\b", r"\bexpensive\b", r"\bdisappoint(ed|ing)\b",
    r"\bregret\b", r"\breturned it\b", r"\buncomfortable\b", r"\btakes forever\b", r"\bmess(y)?\b",
]

WISH_PATTERNS = [
    r"\bi wish\b", r"\bwish (there|they|someone|it)\b", r"\bif only\b", r"\bsomeone (should|needs to) (make|invent|build|create)\b",
    r"\bwhy (isn't|is there no|doesn't|don't|hasn't|can't) (there|anyone|someone|they|it)\b",
    r"\bis there (a|any|some) (product|tool|way|thing|device|gadget|app|brand)\b",
    r"\b(does|do) (anyone|anybody) (know|have|recommend)\b", r"\blooking for (a|an|some) (way|product|solution|tool|thing|device)\b",
    r"\bwould (love|pay|kill for|buy)\b", r"\bshut up and take my money\b", r"\bneed(s)? (a|an) (better|easier|simple|good)\b",
    r"\bthere (has|needs) to be a (better|easier)\b", r"\bit would be (nice|great|amazing|awesome) if\b",
    r"\b(any|got) (recommendations|suggestions|tips)\b", r"\bhow do (you|i|people) (even )?(clean|fix|stop|keep|get rid)\b",
    r"\bbetter way to\b", r"\beasier way to\b", r"\bhack for\b",
]

PAY_PATTERNS = [r"\bwould (pay|buy)\b", r"\bshut up and take my money\b", r"\bi'?d pay\b", r"\btake my money\b",
                r"\bworth every penny\b", r"\bwould spend\b"]

TRIED_PATTERNS = [r"\b(i|we) (tried|bought|ordered|use|used|switched to)\b", r"\bi've (tried|been using|used)\b",
                  r"\bworks (great|well|perfectly)\b", r"\b(recommend|swear by)\b"]

_compile = lambda ps: [re.compile(p, re.I) for p in ps]  # noqa: E731
COMPLAINT_RE, WISH_RE, PAY_RE, TRIED_RE = map(_compile, (COMPLAINT_PATTERNS, WISH_PATTERNS, PAY_PATTERNS, TRIED_PATTERNS))

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_WORD = re.compile(r"[a-z][a-z'\-]+")


def sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_SPLIT.split(text or "") if len(s.strip()) > 12]


def sentiment(text: str) -> float:
    return _vader.polarity_scores(text or "")["compound"]


def label(compound: float) -> str:
    return "positive" if compound >= 0.05 else "negative" if compound <= -0.05 else "neutral"


def weight(post: Post) -> float:
    return 1.0 + math.log1p(max(post.score, 0))


def query_terms(query: str) -> list[str]:
    return [w for w in _WORD.findall(query.lower()) if w not in STOPWORDS and len(w) > 2]


def _stem(w: str) -> str:
    return re.sub(r"(ers|ing|ed|es|s|er)$", "", w) if len(w) > 4 else w


def is_relevant(post: Post, terms: list[str], min_hits: int | None = None) -> bool:
    """Keep posts that mention enough of the query terms (in text, title or thread context)."""
    if not terms:
        return True
    hay = {_stem(w) for w in _WORD.findall(f"{post.full_text} {post.context}".lower())}
    hits = sum(1 for t in terms if _stem(t) in hay)
    need = min_hits if min_hits is not None else (1 if len(terms) <= 2 else math.ceil(len(terms) / 2))
    return hits >= need


def _match(res, text: str) -> bool:
    return any(r.search(text) for r in res)


def extract(post: Post) -> dict[str, list[str]]:
    """Sentences in the post that are complaints, wishes, willingness-to-pay or tried-solutions."""
    out: dict[str, list[str]] = {"complaints": [], "wishes": [], "pay": [], "tried": []}
    for s in sentences(post.full_text):
        if _match(COMPLAINT_RE, s) or (sentiment(s) <= -0.4):
            out["complaints"].append(s)
        if _match(WISH_RE, s):
            out["wishes"].append(s)
        if _match(PAY_RE, s):
            out["pay"].append(s)
        if _match(TRIED_RE, s):
            out["tried"].append(s)
    return {k: v for k, v in out.items() if v}


def themes(texts: list[str], exclude: list[str], top: int = 15) -> list[tuple[str, int]]:
    """Most common words and two-word phrases, excluding stopwords and the query itself."""
    excl = set(exclude) | {_stem(e) for e in exclude}
    counts: Counter[str] = Counter()
    for t in texts:
        words = [w for w in _WORD.findall(t.lower()) if w not in STOPWORDS and w not in excl and _stem(w) not in excl]
        seen = set(words) | {f"{a} {b}" for a, b in zip(words, words[1:])}
        counts.update(seen)  # document frequency, so one long rant can't dominate
    # Prefer phrases: drop a single word if a phrase containing it is almost as common.
    ranked = [(k, v) for k, v in counts.most_common(top * 4) if v >= 2]
    phrases = [k for k, _ in ranked if " " in k]
    result = []
    for k, v in ranked:
        if " " not in k and any(k in p.split() and counts[p] >= 0.6 * v for p in phrases):
            continue
        result.append((k, v))
    return result[:top]


def score_posts(posts: list[Post]) -> None:
    for p in posts:
        p.sentiment = sentiment(p.full_text)
        p.matches = extract(p)


def sentiment_summary(posts: list[Post]) -> dict:
    """Overall and per-source sentiment, engagement-weighted."""
    def summarize(group: list[Post]) -> dict:
        if not group:
            return {"count": 0}
        tw = sum(weight(p) for p in group)
        avg = sum((p.sentiment or 0) * weight(p) for p in group) / tw
        labels = Counter(label(p.sentiment or 0) for p in group)
        n = len(group)
        return {
            "count": n,
            "weighted_score": round(avg, 3),
            "label": label(avg),
            "positive_pct": round(100 * labels["positive"] / n, 1),
            "neutral_pct": round(100 * labels["neutral"] / n, 1),
            "negative_pct": round(100 * labels["negative"] / n, 1),
        }

    by_source: dict[str, list[Post]] = {}
    for p in posts:
        by_source.setdefault(p.source, []).append(p)
    return {"overall": summarize(posts), "by_source": {k: summarize(v) for k, v in sorted(by_source.items())}}


def top_quotes(posts: list[Post], key: str, n: int = 15) -> list[dict]:
    """Best sentences of a given kind ('complaints', 'wishes', ...) ranked by engagement."""
    rows = []
    seen: set[str] = set()
    for p in sorted(posts, key=weight, reverse=True):
        for s in p.matches.get(key, []):
            norm = s.lower()[:120]
            if norm in seen:
                continue
            seen.add(norm)
            rows.append({"quote": s[:400], "source": p.source, "score": p.score, "url": p.url, "context": p.context})
    return rows[:n]


def extreme_posts(posts: list[Post], positive: bool, n: int = 10) -> list[dict]:
    pool = [p for p in posts if p.sentiment is not None and ((p.sentiment >= 0.3) if positive else (p.sentiment <= -0.3))]
    pool.sort(key=lambda p: (weight(p) * abs(p.sentiment or 0)), reverse=True)
    return [{"quote": _excerpt(p), "source": p.source, "score": p.score, "sentiment": round(p.sentiment or 0, 2),
             "url": p.url, "context": p.context} for p in pool[:n]]


def _excerpt(p: Post, limit: int = 400) -> str:
    t = re.sub(r"\s+", " ", p.full_text).strip()
    return t if len(t) <= limit else t[:limit].rsplit(" ", 1)[0] + "…"
