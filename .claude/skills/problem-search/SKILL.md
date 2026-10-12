---
name: problem-search
description: "Problem Search" - find complaints people have about a specific everyday problem and the solutions they wish existed, across Reddit, YouTube, Quora, Facebook, Instagram, Amazon, TikTok and forums, to spot product opportunities. Use when the user says "problem search", or asks what people complain about / struggle with / wish existed for some problem.
---

# Problem Search

The user does e-commerce/dropshipping and wants product ideas that come from real pain points.
Example: people on Reddit complain that retainers are hard to clean and wish there were an easy solution.

1. Run the collector from the repo root (it reads API keys from `.env`):
   ```bash
   python -m market_research problem "<problem in plain words>" --fetch-pages
   ```
   Add `--ai` if `ANTHROPIC_API_KEY` is set. Phrase the problem the way people would write it
   (e.g. "cleaning retainers", not "retainer hygiene market"). Try 1–2 variant phrasings if the first run finds little.
2. Read the generated `report.md` (demand signals, pain-point themes, complaints, wishes,
   willingness to pay, tried solutions). Go into `data.json` for more detail when needed.
3. **Fill the gaps** with WebSearch/WebFetch for any source that was skipped or thin. Useful queries:
   `<problem> "I wish" site:reddit.com`, `<problem> "is there a product"`, `<problem> annoying`,
   `<problem> site:quora.com`, `<problem> hack`. Only use public pages.
4. Write the final answer for the user:
   - **How painful and widespread** the problem is (use the demand signals and engagement numbers)
   - **Pain points, ranked**, with verbatim quotes and links
   - **What people wish existed**, with quotes and links
   - **What they've already tried** and why it falls short (this is your competition)
   - **Willingness to pay** evidence
   - **3–6 product ideas** a seller could source, each tied to the pain points it solves; suggest AliExpress/Alibaba search terms
   - **5 marketing hooks** in the customers' own words
5. Never invent quotes. If the evidence is thin, say so.
