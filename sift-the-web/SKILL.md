---
name: sift-the-web
description: Search the web smarter and say how solid the answer is. Skips junk sites and blocklisted domains. Trigger only with /sift-the-web, followed by the question.
disable-model-invocation: true
---

# sift-the-web

Web search is full of affiliate lists, content farms and AI filler. Search better than the user's own wording, and say how solid the answer is.

Run only when the user types `/sift-the-web`. Everything after it is the question. Never start on your own.

## 1. Read the blocklist

Read `blocklist.txt` (next to this file) before searching. Each non-comment line is a site to skip (format below). Drop matching results. If the search tool allows it and the list is short, add `-site:domain` for plain domains. Filter wildcards from the results, since they can't go in queries.

## 2. Rewrite the question

Don't search the user's text as is. Work out what they want, then run 3 to 5 searches from different angles:

- **Plain:** the question, made clear and specific.
- **Insider words:** how an expert or real user would say it ("laptop thermal throttling fix", not "top 10 laptop cooling tips").
- **Original source:** official docs, maker pages, papers, government sites, first-hand reporting, changelogs, issue trackers.
- **Real people:** forums, Reddit, Stack Exchange, GitHub issues, Hacker News, niche communities.

Avoid "best X of 2026" wording unless they want a roundup. It brings up the pages we're dodging.

Don't ask clarifying questions. Pick the most likely meaning, and if it was truly unclear, say which one in a few words inside the answer.

## 3. Judge the results

Skip or downgrade pages that look copied, unchecked or written to sell:

- Affiliate lists and "best of" roundups with no described testing
- Padded, generic writing ("In today's fast-paced world...")
- No author, date or sources, or sources that only link back to the same site
- Near-identical pages on different sites (scraped or spun)
- Claims with no data, method or first-hand detail

Prefer first-hand detail, named people or institutions, original data, and links to original material. If sources disagree, say so. Check key claims against a second, independent source. Note junk domains worth a warning: repeat offenders or clearly bad ones, not every mediocre page.

## 4. Answer

Answer first, then only as much backing as needed. Match length to the question. No intro, search recap or closing summary. Use your own words; quote only when exact wording matters, briefly, once per source.

Build the reply in this order. Skip any part marked "if any" or "if thin" that has nothing to say:

1. **The answer.** Direct, with no label. If it depends, say on what, and answer each case that matters.
2. **Best evidence.** 2 to 5 sources, each with a direct link to the exact page, comment or section, and a few words on why it's strong.
3. **Coverage note** (if thin). If most results were junk, or a kind of source you needed (original docs, owner reports, papers) never showed up, say which, and how that limits the answer. Still give your best answer.
4. **Sites to watch out for** (if any). Put the label `Sites to watch out for:` on its own line at the very bottom, then one copyable code block with every junk domain to skip in future, in the blocklist format below. The label goes above the block. Inside it, only entries, with no reasons or comments. Leave out domains already in `blocklist.txt` or covered by a wildcard there.

Don't edit `blocklist.txt` and don't ask whether to add the sites. The user pastes the block in if they want it.

## Blocklist format

One entry per line, nothing else on it. Blank lines and lines starting with `#` are ignored (use those only for the file header).

- **Plain domain (the default):** lowercase, no `https://`, no `www.`, no paths. `example.com` blocks the site and all its subdomains, never its parent (`cloud.example.com` blocks `x.cloud.example.com`, not `example.com`).
- **Wildcard (last resort):** `*` matches any run of characters in the hostname. Use it only when plain domains can't cover it, such as a family of lookalike sites (`bestof*reviews.com`). Keep fixed text on both sides so it can't hit real sites. Never `*.com` or a bare `*`.
- **Suggesting:** use plain domains. Suggest a wildcard only when several lookalike domains share a clear pattern.
- **Matching:** a blocked entry is always skipped. If nothing else turns up, say so in the coverage note.

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
Gummy sourdough is almost always underfermentation or cutting too soon. Fix the first rise (the dough should be airy and jiggly, not just risen by the clock), then let the loaf cool for at least an hour before slicing. An oven that's too cool is the third usual cause.

**Best evidence**
- [Serious Eats sourdough troubleshooting](link): tested, with photos of each failure
- [r/Sourdough thread](link): bakers posting their own crumb shots and what fixed it

Sites to watch out for:
```
bakingtipsdaily.example
```
