"""Optional AI synthesis with Claude (set ANTHROPIC_API_KEY, use --ai)."""
from __future__ import annotations

import json

from .models import Post

MODEL = "claude-opus-5-5"

PRODUCT_PROMPT = """You are a market researcher helping an e-commerce / dropshipping seller decide whether
to sell a product and how to market it. Below are {n} real user posts, comments, reviews and search
snippets about "{subject}", collected from {sources}. Each has a source, engagement score and URL.

Write a concise Markdown report with these sections:
1. **Verdict** – overall user sentiment in 2–3 sentences, and whether it looks like a good product to sell.
2. **What people love** – top praised attributes, each with 1–2 short verbatim quotes and the source URL.
3. **Top complaints** – the most common/most upvoted problems (quality, sizing, shipping, price, durability …), with quotes + URLs.
4. **Unmet needs / improvement ideas** – what a better version of this product would fix.
5. **Who buys it** – buyer personas and use cases you can infer.
6. **Marketing angles** – 5 ad hooks / headlines written in the customers' own language.
7. **Red flags for a seller** – return risks, safety/regulatory issues, saturation signals.

Only use what is in the data; say so when evidence is thin. Quote exactly, don't invent quotes.

DATA (JSON lines):
{data}"""

PROBLEM_PROMPT = """You are a product-opportunity researcher helping an e-commerce / dropshipping seller
find products that solve real problems. Below are {n} real user posts and comments about the problem
"{subject}", collected from {sources}. Each has a source, engagement score and URL.

Write a concise Markdown report with these sections:
1. **Summary** – how painful and widespread this problem looks, in 2–3 sentences.
2. **Pain points, ranked** – distinct complaints ordered by frequency × engagement, each with 1–2 verbatim quotes + URL.
3. **What people wish existed** – the solutions people explicitly ask or wish for, with quotes + URL.
4. **What they've already tried** – existing products/hacks mentioned and why they fall short (or work).
5. **Willingness to pay** – any evidence people would pay, and price expectations.
6. **Product ideas** – 3–6 concrete product concepts a seller could source, each tied to the pain points it solves.
7. **Marketing hooks** – 5 headlines in the customers' own words.

Only use what is in the data; say so when evidence is thin. Quote exactly, don't invent quotes.

DATA (JSON lines):
{data}"""


def _serialize(posts: list[Post], max_posts: int, max_chars: int) -> str:
    rows = []
    for p in posts[:max_posts]:
        rows.append(json.dumps({
            "source": p.source, "kind": p.kind, "score": p.score, "context": p.context[:120],
            "url": p.url, "text": p.full_text[:max_chars],
        }, ensure_ascii=False))
    return "\n".join(rows)


def synthesize(mode: str, subject: str, posts: list[Post], max_posts: int = 300, max_chars: int = 1200) -> str:
    import anthropic  # imported lazily so the tool works without the SDK

    template = PRODUCT_PROMPT if mode == "product" else PROBLEM_PROMPT
    prompt = template.format(
        n=min(len(posts), max_posts), subject=subject,
        sources=", ".join(sorted({p.source for p in posts})),
        data=_serialize(posts, max_posts, max_chars),
    )
    client = anthropic.Anthropic()
    with client.beta.messages.stream(
        model=MODEL,
        max_tokens=64000,
        thinking={"type": "adaptive"},
        output_config={"effort": "medium"},
        # Re-run on a fallback model if a safety classifier declines the request.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        message = stream.get_final_message()
    if message.stop_reason == "refusal":
        return "_AI summary unavailable: the request was declined._"
    return "\n".join(b.text for b in message.content if b.type == "text").strip()
