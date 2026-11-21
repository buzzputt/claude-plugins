---
name: sift-the-web
description: Refine questions into targeted searches, value trustworthy sources, skip blocklisted domains, and return answers with source-quality notes.
---

# sift-the-web

Web search is full of affiliate listicles, content farms, and AI filler, and users don't always know the keywords that dodge them. This skill searches smarter than the user's raw wording and says honestly how solid the answer is.

Run only when the user types `/sift-the-web`. Everything after the command is the question.

## 1. Read the blocklist

Read `blocklist.txt` (next to this file) before searching. Each non-comment line is an entry to skip (format below). Drop matching results. For plain domains, also add `-site:domain` to queries if the search tool supports it and the list is short. Wildcards can't go in queries, so filter those from results instead.

## 2. Rewrite the question

Don't search the user's text as-is. Work out what they actually want, then run 3-5 searches from different angles:

- **Plain:** the question, cleaned up and specific.
- **Insider wording:** how an expert or real user would say it, not marketing words ("laptop thermal throttling fix", not "top 10 laptop cooling tips").
- **Primary source:** official docs, manufacturer pages, papers, government sites, original reporting, changelogs, issue trackers.
- **Real people:** forums, Reddit, Stack Exchange, GitHub issues, Hacker News, specialist communities.

Avoid "best X of 2026" phrasing unless the user wants a roundup; it summons the pages we're dodging.

Don't ask clarifying questions. Pick the most reasonable reading. If the question was truly ambiguous, mention your reading in a clause inside the answer so the user can correct you.

## 3. Judge the results

Discard or discount pages that are likely repackaged, unchecked, or written to sell:

- Affiliate listicles and "best of" roundups with no described testing
- Padded generic prose ("In today's fast-paced world...")
- No author, date, or sources, or sources that only link back to the same site
- Near-identical pages across domains (scraped or spun content)
- Claims with no data, method, or firsthand detail

Prefer firsthand detail, named people or institutions, original data, and links to primary material. If sources disagree, say so. Cross-check key claims against a second independent source.

Track junk domains worth warning about: repeat offenders or clearly bad ones, not every mediocre page.

## 4. Answer

Answer first, then just enough backing. Length tracks the question. No preamble, search recap, or closing summary. Paraphrase sources; quote only when exact wording matters, briefly, once per source.

Build the reply from these parts, in this order. Skip any marked "if any" or "if thin" that has nothing to say:

1. **The answer.** Direct, with no label. If it depends, say on what and answer each branch that matters.
2. **Best evidence.** 2-5 sources with direct links to the exact page, comment, or section, and a few words on why each is strong.
3. **Coverage note** (if thin). If results were mostly junk, or a kind of source you needed (primary docs, owner reports, papers) never turned up, say which and how that limits the answer. Still give your best answer; a confident answer built on slop is exactly what the user wants to escape.
4. **Sites to watch out for** (if any). The label `Sites to watch out for:` on its own line at the very bottom of the reply, then one copy-ready code block holding every junk domain you want skipped in future, in the blocklist format below. The label goes above the block, not inside it. Inside the block: only the entries, with no reasons or commentary. Leave out domains already in `blocklist.txt` or matched by a wildcard there.

Don't edit `blocklist.txt` yourself and don't ask whether to add the sites. The user pastes the block into the file when they want it. Future runs read the file in step 1.

## Blocklist format

One entry per line, nothing else on the line. No notes, reasons, or trailing comments. Blank lines and lines starting with `#` are ignored (keep those to the file header).

- **Plain domain (default):** lowercase, no `https://`, no `www.`, no paths. `example.com` blocks the site and all its subdomains, never its parent (`cloud.example.com` blocks `x.cloud.example.com`, not `example.com`).
- **Wildcard (final resort):** `*` matches any run of characters in the hostname. Use only when plain domains can't cover it, such as a family of lookalike sites (`bestof*reviews.com`). Keep a fixed part on both sides so it can't hit real sites; never `*.com` or a bare `*`.
- **Suggesting:** put plain domains in the sites-to-avoid block. Suggest a wildcard only when several lookalike domains share a clear pattern.
- **Matching:** a blocked entry is always skipped, with no exceptions. If nothing else turns up, the coverage note says so.

```
example.com
contentfarm.net
bestof*reviews.com
```

## Example

**User:** `/sift-the-web why does my sourdough come out gummy`

**Reading:** dense, wet crumb even after baking.
**Searches:** "sourdough gummy crumb underproofed vs overproofed", "sourdough gummy crumb King Arthur OR Serious Eats", "sourdough gummy reddit r/Sourdough fix"

**Reply:**
Gummy sourdough is almost always underfermentation or slicing too soon. Fix the bulk ferment first (dough should be airy and jiggly, not just risen by the clock), then cool the loaf at least an hour before cutting. An oven that's too cool is the third usual suspect.

**Best evidence**
- [Serious Eats sourdough troubleshooting](link): tested, with photos of each failure
- [r/Sourdough thread](link): bakers posting their own crumb shots and what fixed it

Sites to watch out for:
```
bakingtipsdaily.example
```
