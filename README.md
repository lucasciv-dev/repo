# Market Research Tools for E-commerce

Two tools for finding and checking products:

| Tool | What it answers | Command |
|---|---|---|
| **Product Sentiment** | "What do real users think of *X*?" | `python -m market_research product "posture corrector"` |
| **Problem Search** | "What are people complaining about, and what do they wish existed?" | `python -m market_research problem "cleaning retainers"` |

Both tools gather posts, comments, reviews and snippets from **Reddit, YouTube, Hacker News, Quora,
Facebook, Instagram, Amazon, TikTok, Trustpilot and general forums**. They then:

- score sentiment (engagement-weighted, so a comment with 2,000 upvotes counts more than one with 0)
- pull out **complaint** sentences ("so annoying", "gross", "broke after a week" …)
- pull out **wish** sentences ("I wish there was…", "someone should invent…", "is there a product that…")
- flag **willingness to pay** ("I would pay…", "shut up and take my money")
- record **solutions people already tried**
- find the most common pain-point and praise themes
- (optional, `--ai`) have Claude write a full report covering pain points, product ideas, buyer personas,
  ad hooks in the customers' own words, and red flags for a seller

Every quote links back to its source.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env      # then add whichever API keys you have
```

| Source | Needs | Cost |
|---|---|---|
| Reddit | `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` (a "script" app at reddit.com/prefs/apps). Without them it tries Reddit's public JSON, which is heavily rate-limited. | Free |
| Hacker News | nothing | Free |
| YouTube comments | `YOUTUBE_API_KEY` | Free quota |
| Quora, Facebook, Instagram, Amazon, TikTok, Trustpilot, forums | `BRAVE_API_KEY` **or** `SERPAPI_KEY` | Brave has a free tier |
| AI report (`--ai`) | `ANTHROPIC_API_KEY` | Pay per use |

### Why Facebook, Instagram and Amazon go through a search API

Facebook, Instagram, TikTok and Amazon block scrapers, require a login, and forbid scraping in their
terms of service. Scraping them directly gets accounts and IPs banned and breaks every few weeks.
Instead, the tool searches those sites with `site:` queries through Brave or SerpApi and collects the
public text the search engine indexed (post captions, review excerpts, Quora answers). It is legal,
stable, and usually enough to spot themes. For open forums and blogs, `--fetch-pages` downloads the
full page text, but only when the site's robots.txt allows it.

## Usage

```bash
# Product sentiment
python -m market_research product "retainer cleaning tablets"
python -m market_research product "led face mask" --ai

# Problem Search
python -m market_research problem "cleaning retainers" --ai
python -m market_research problem "dog hair on couch" --sources reddit,youtube,quora --fetch-pages

# Options
--sources reddit,youtube,hackernews,quora,facebook,instagram,amazon,tiktok,trustpilot,forums
--limit 200          # max items per source
--fetch-pages        # full text for open forum pages found via web search
--ai                 # Claude-written analysis on top of the stats
--out reports        # output folder
```

Each run creates `reports/<mode>-<topic>-<timestamp>/` containing:

- `report.md`: the readable report
- `posts.csv`: every item with sentiment and the complaint/wish sentences found (opens in Excel or Sheets)
- `data.json`: everything, for further analysis

## Using it by asking Claude

This repo ships two Claude Code skills (`.claude/skills/`), so in a Claude Code session in this repo
you can just ask:

- *"Find user sentiment on the Theragun mini"*
- *"Problem search: people struggling to clean their retainers"*

Claude runs the tool, fills gaps with its own web search when a source has no key, and writes the
final analysis.

## Tests

```bash
pip install pytest && python -m pytest
```
