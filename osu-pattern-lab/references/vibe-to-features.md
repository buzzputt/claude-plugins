# Vibe words to feature targets

A target is a dict of feature ranges for `scripts/search.py`. All numbers are starting points: calibrate with `library.py stats` (p10/median/p90), since "chill" differs between a 3★-heavy and a 7★-heavy library. For orientation, a real 6-diff set (2.2-7.1★) had motif p10/median/p90 of: density 0.67/1.33/2.67, `ds_mean` 0.71/1.57/2.75, `speed_pxms` 0.16/0.59/1.11, `ang_mean` 33/84/153, `slider_ratio` 0.14/0.5/1.0, intensity 0.28/0.44/0.59. Ranges far outside these match almost nothing.

## Features

A **diameter** is one circle width (varies with CS); a **beat** is one beat of the active timing point; ratios are 0-1 shares of moves.

| Feature | Meaning | Typical values |
|---|---|---|
| `n`, `beats` | object count; length in beats | motif 3-12 objects, 1-4 beats |
| `density` | objects per beat | 0.5-1 sparse, 1-2 half-beat, 2-3 triplet/mixed, 4 = 1/4 stream |
| `gap_mean`, `gap_min` | gap sizes in beats | 0.25 stream, 0.5 half-beat, 1 slow; `slow-rhythm` tag = `gap_mean` ≥ 1.25 |
| `stream_ratio` | share of gaps ≤ 1/4 beat | 0.8+ real stream |
| `triplet_ratio`, `half_ratio` | share of 1/3-or-1/6 / 1/2 gaps | triplet 0.4+ |
| `slow_ratio` | share of gaps ≥ 1 beat | 0.5+ airy |
| `ds_mean`, `ds_max` | spacing, diameters | <0.5 tight stream, 0.5-1.25 flow, 1.25-2.5 medium, 2.5+ big (top ~10% of real motifs; 4+ rare) |
| `stack_ratio` | share of moves < 0.15 diameter | |
| `jump_ratio`, `far_ratio` | share of moves ≥ 2.5 / ≥ 4 diameters | |
| `speed_pxms` | cursor px per ms (BPM-aware) | 0.2 calm, 0.5 brisk, 1.0+ fast |
| `ang_mean`, `ang_std` | interior angle, 180 = straight | <45 snappy, 140+ flowy; real median ~84 |
| `sharp_ratio`, `wide_ratio` | share of angles < 90 / ≥ 150 | |
| `slider_ratio`, `slider_beats`, `repeat_ratio` | slider share; mean length; share with repeats | |
| `nc_rate` | new-combo rate | |
| `regularity` | 1 = same moves repeated, 0 = all different | blank for most motifs (needs 3+ moves): use `levels: ["phrase"]`; 0.75+ repetitive, ≤0.35 varied |
| `spacing_trend`, `density_trend` | last third minus first third | positive = building, negative = releasing |
| `intensity` | mean of density/4, spacing/4, `rel` | real maps 0.28-0.59; ≤0.30 chill, ≥0.55 intense |
| `rel` | local strain / map's peak strain | |
| `stars`, `aim`, `speed`, `bpm` | source map's values (whole map) | |

Tags for `prefer_tags` / `avoid_tags` / `require_tags`: `stream`, `burst`, `jumpy`, `wide-jumps`, `stacky`, `flowy`, `snappy`, `slider-heavy`, `circles-only`, `triplets`, `slow-rhythm`, `repetitive`, `varied`, `buildup`, `release`, `kiai`, `intense`, `chill`, plus any added via `annotate`. Built-in tags are computed at load (always current, each on ~5-35% of patterns; a tag that fits everything says nothing); only `annotate` tags are stored.

## Vibe words (seeds, not rules)

| Vibe | Target sketch |
|---|---|
| chill, calm, gentle | `intensity [0, 0.33]`, `density [0.5, 1.5]`, `ds_mean [0.5, 2]`, high `slow_ratio` |
| floaty, dreamy, airy | `wide_ratio [0.5, 1]`, `slow_ratio [0.3, 1]`, `slider_ratio [0.3, 1]`, `jump_ratio [0, 0.2]`, prefer `flowy` |
| flowy, smooth | `ang_mean [135, 180]`, `wide_ratio [0.6, 1]`, `sharp_ratio [0, 0.15]` |
| aggressive, hype | `intensity [0.5, 1]`, `jump_ratio [0.4, 1]` or high `stream_ratio`, `density [2, 4]` |
| snappy, punchy | `ang_mean [40, 100]`, `sharp_ratio [0.4, 1]`, higher `half_ratio` |
| bouncy | `half_ratio [0.5, 1]`, `ds_mean [1.5, 3]`, low `ang_mean` (back-and-forth), high `regularity` |
| technical | phrase level: `regularity [0, 0.4]`, high `ang_std`, mixed `triplet_ratio` and `half_ratio`, prefer `varied` |
| simple, readable | `regularity [0.6, 1]`, `density [1, 2]`, `ds_mean [0.8, 2]`, `jump_ratio [0, 0.3]` |
| streamy | `stream_ratio [0.7, 1]`, `density [3.5, 4.5]`, `n` 6+ |
| jumpy | `jump_ratio [0.5, 1]`, `ds_mean [2.5, 5]` |
| slidery | `slider_ratio [0.5, 1]`, optionally `slider_beats [1, 4]` |
| stacky, dense | `stack_ratio [0.4, 1]`, `ds_mean [0, 0.5]`, some `triplet_ratio` |
| triplets, swingy | `triplet_ratio [0.4, 1]` |
| climax, drop, chorus | `intensity [0.5, 1]`, prefer `kiai`, `intense` |
| break, intro, outro | `intensity [0, 0.25]`, high `slow_ratio`, small `n` |

## Combining

- Several words: use all; weight the dominant one (`"weights": {"jump_ratio": 2}`). Contradictions trigger the ambiguity check.
- "Building into X": search start and destination separately and present as a sequence, or use `spacing_trend`/`density_trend` positive with `buildup` at `levels: ["phrase"]`.
- "Chorus" / "whole section" → `levels: ["phrase", "section"]`; "something for this bar" → `["motif"]`.
- Use 3-5 well-chosen features: every listed feature pulls the score.

## Ambiguous words: what to ask

One to three questions, once, with options answerable instantly.

- **"emotional", "dramatic", "epic"**: slow wide sliders, tense fast stream, or big-jump climax?
- **"cool", "sick", "fun"**: no intensity at all. How hard should it hit; jumps, flow or streams?
- **"chill but intense"**: calm that builds, intense with gentle spacing, or two separate parts?
- **"something different"**: rarer patterns (bigger wildcard share), another shape family, or another energy than last round? If a previous round exists, infer instead of asking.
- Missing difficulty context isn't ambiguity: beats are tempo-free, so proceed and offer to adapt spacing.
