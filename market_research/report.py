"""Write results to Markdown, JSON and CSV."""
from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60] or "research"


def _quotes(rows: list[dict], show_sentiment: bool = False) -> str:
    if not rows:
        return "_None found._\n"
    lines = []
    for r in rows:
        meta = f"{r['source']}" + (f", ▲{r['score']}" if r.get("score") else "")
        if show_sentiment:
            meta += f", sentiment {r['sentiment']:+.2f}"
        q = r["quote"].replace("\n", " ")
        lines.append(f"- “{q}” — _{meta}_ [link]({r['url']})" if r.get("url") else f"- “{q}” — _{meta}_")
    return "\n".join(lines) + "\n"


def _themes(rows) -> str:
    return ", ".join(f"**{t}** ({n})" for t, n in rows) + "\n" if rows else "_Not enough data._\n"


def _sentiment_table(s: dict) -> str:
    out = ["| Source | Items | Score (−1…+1) | Label | 👍 % | 😐 % | 👎 % |", "|---|---|---|---|---|---|---|"]
    rows = [("**All**", s["overall"])] + list(s["by_source"].items())
    for name, v in rows:
        if not v.get("count"):
            continue
        out.append(f"| {name} | {v['count']} | {v['weighted_score']:+.2f} | {v['label']} | "
                   f"{v['positive_pct']} | {v['neutral_pct']} | {v['negative_pct']} |")
    return "\n".join(out) + "\n"


def to_markdown(result: dict, ai_summary: str | None = None) -> str:
    subject = result["subject"]
    when = datetime.now().strftime("%Y-%m-%d %H:%M")
    md = []
    if result["mode"] == "product":
        md.append(f"# Product sentiment: {subject}\n\n_Generated {when}_\n")
    else:
        md.append(f"# Problem Search: {subject}\n\n_Generated {when}_\n")

    if ai_summary:
        md.append("## AI analysis\n\n" + ai_summary + "\n")

    md.append("## Sources\n\n" + "\n".join(f"- **{k}**: {v}" for k, v in sorted(result["source_status"].items())) + "\n")

    if result["mode"] == "product":
        md.append("## Sentiment\n\n_Score is engagement-weighted VADER sentiment._\n\n" + _sentiment_table(result["sentiment"]))
        md.append("## What people praise (themes)\n\n" + _themes(result["praise_themes"]))
        md.append("## What people complain about (themes)\n\n" + _themes(result["complaint_themes"]))
        md.append("## Most positive posts\n\n" + _quotes(result["top_positive"], True))
        md.append("## Most negative posts\n\n" + _quotes(result["top_negative"], True))
        md.append("## Complaint quotes\n\n" + _quotes(result["complaints"]))
        md.append("## Wishes / improvement requests\n\n" + _quotes(result["wishes"]))
    else:
        s = result["demand_signals"]
        md.append(
            "## Demand signals\n\n"
            f"- Relevant posts analyzed: **{s['posts_analyzed']}**\n"
            f"- Posts containing complaints: **{s['posts_with_complaints']}**\n"
            f"- Posts wishing for a solution: **{s['posts_with_wishes']}**\n"
            f"- “Would pay / take my money” mentions: **{s['willingness_to_pay_mentions']}**\n"
            f"- Total engagement (upvotes/likes): **{s['total_engagement']}**\n"
        )
        md.append("## Pain-point themes\n\n" + _themes(result["pain_point_themes"]))
        md.append("## Wished-for solution themes\n\n" + _themes(result["wished_solution_themes"]))
        md.append("## Complaints\n\n" + _quotes(result["complaints"]))
        md.append("## What people wish existed\n\n" + _quotes(result["wishes"]))
        md.append("## Willingness to pay\n\n" + _quotes(result["willing_to_pay"]))
        md.append("## Solutions people already tried\n\n" + _quotes(result["tried_solutions"]))
        md.append("## Sentiment\n\n" + _sentiment_table(result["sentiment"]))
    return "\n".join(md)


def write(result: dict, out_dir: Path, ai_summary: str | None = None) -> Path:
    folder = out_dir / f"{result['mode']}-{slugify(result['subject'])}-{datetime.now():%Y%m%d-%H%M%S}"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "report.md").write_text(to_markdown(result, ai_summary), encoding="utf-8")

    data = {k: v for k, v in result.items() if k != "posts"}
    data["ai_summary"] = ai_summary
    data["posts"] = [p.to_dict() for p in result["posts"]]
    (folder / "data.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    with open(folder / "posts.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source", "kind", "score", "sentiment", "complaints", "wishes", "context", "title", "text", "url"])
        for p in result["posts"]:
            w.writerow([p.source, p.kind, p.score, round(p.sentiment or 0, 3),
                        " | ".join(p.matches.get("complaints", [])), " | ".join(p.matches.get("wishes", [])),
                        p.context, p.title, p.text, p.url])
    return folder
