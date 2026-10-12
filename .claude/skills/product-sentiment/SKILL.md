---
name: product-sentiment
description: Research real user sentiment about a specific product across Reddit, YouTube, Quora, Facebook, Instagram, Amazon reviews, TikTok, Trustpilot and forums. Use when the user asks to "find user information / sentiment / reviews / what people think" about a product, or whether a product is worth selling.
---

# Product Sentiment Research

The user sells through e-commerce/dropshipping and wants to know what real buyers think of a product.

1. Run the collector from the repo root (it reads API keys from `.env`):
   ```bash
   python -m market_research product "<product name>" --fetch-pages
   ```
   Add `--ai` if `ANTHROPIC_API_KEY` is set. The command prints which sources ran or were skipped, and
   where it wrote `report.md`, `posts.csv` and `data.json`.
2. Read the generated `report.md`. If you need more detail, read the most relevant rows of `data.json`.
3. **Fill the gaps.** For each source marked `skipped` or `error`, or one that returned few items,
   use WebSearch/WebFetch for that site yourself, e.g. `"<product>" review site:reddit.com`,
   `site:quora.com`, `site:amazon.com "<product>" customer reviews`, `site:trustpilot.com`,
   `"<product>" problems forum`. Only use public pages. Don't log in to anything or get around login walls.
4. Write the final answer for the user:
   - **Verdict**: overall sentiment (with the score and how many items it is based on), and whether it looks sellable
   - **What people love** and **top complaints**, each with short verbatim quotes and source links
   - **Unmet needs**: what a better version would fix (these are differentiation angles)
   - **Buyer personas**, **5 ad hooks** written in the customers' own words, and **red flags** (returns, safety, saturation)
   - Which sources were and weren't covered
5. Never invent quotes. If the evidence is thin, say so.
