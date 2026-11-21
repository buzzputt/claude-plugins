# patterns.zip layout (schema 1)

Read only to debug or extend the format. All plain JSON.

```
patterns.zip
  manifest.json
  diffs/<title>-<version>-<hash8>.jsonl     one file per difficulty
  taste.jsonl                               one line per feedback
```
Loaders reject members with `..`, absolute paths, or over 40 MB.

**manifest.json**: `schema`, `tool`, `updated`, `diff_engine` (`{name, version}` of the latest ingest), `maps[]` with `key` (file stem), `sha1` (of normalized `.osu` text), `title`, `artist`, `creator`, `version`, `stars`, `engine` (rated this diff), `n_obj`, `nodes` (`[motifs, phrases, sections]`), `ingested`.

**diffs/<key>.jsonl**: compact JSONL. Line 1 is a header (`"hdr":1`): `k` (hash8), `sha1`, metadata, `cs ar od sm`, `bpm` list, whole-map nomod `stars aim speed`, `engine`, counts, `bad_objects` (unparseable lines). Then nodes: motifs, phrases, sections.

## Node fields

| Key | Meaning |
|---|---|
| `id` | `<hash8>:<m\|p\|s>:<n>` |
| `lv` | `m` motif, `p` phrase, `s` section |
| `par`, `ch` | parent id; child ids (`null` for motifs) |
| `src` | `d` hash8; `r` `[first, last]` index into the **time-sorted** object list; `t` `[start_ms, end_ms]`; `ts` pasteable editor timestamp |
| `abs` | abstract layer (below) |
| `f` | features (see `vibe-to-features.md`) |
| `tags` | tags added by `annotate` only; built-in tags are computed from `f` and `ki` at load, never stored |
| `ki` | 1 if all objects are in kiai |
| `desc` | one-line description, empty until written |
| `mv`, `an` | motifs only: per move `[gap_beats, distance_px]`; interior angles in degrees |
| `full` | motifs only; phrases/sections rebuild theirs by concatenating children's `full.o` |

**Abstract layer** (motifs): `k` kinds (`c` circle, `s` slider, `p` spinner); `r` start-to-start gap tokens in beats (`1/4`, `1/3`, `1/2`, `1`, ..., `~0.35` off-grid); `sd` slider-duration tokens; `d` distance bin per move (`S` <0.15 diameter, `N` <1.25, `M` <2.5, `L` <4, `X` beyond); `a` signed direction changes in 15° steps, mirror-normalized (first real turn positive); `key` readable cluster key; `cl` its md5[:8]. Equal `cl` = same idea regardless of rotation, mirroring, or spacing within a bin. Phrases/sections carry `mc` (child motif cluster ids in order), `rh` (rhythm token counts), `cl`.

## Full layer

`full` = `{bpm, cs, ar, od, sm, li, o}`; `li` = `[gap_beats, distance_px]` from the previous object outside the pattern, or null. Each object in `o`:

`[x, y, t_ms, beat_pos, kind, new_combo, hitsound, beat_length_ms, sv_mult, extra?]`

- `beat_pos`: beats since the active red line.
- Slider `extra`: `{c: B|P|L|C curve, p: [[x,y],...] control points incl. head, n: slides, l: px length, e: [x,y] tail, d: duration ms}`. Duration = `l / (sm*100*sv_mult) * beat_length * n`.
- Spinner `extra`: `{d: duration ms}`.

## taste.jsonl

Entry: `ts`, `text`, `vibe`, `learned`, `prefs` (`[{f: feature, dir: +1|-1, s: 0..1}]`), and lists `shown`, `like_tags`, `avoid_tags`, `like_clusters`, `avoid_clusters`, `like_nodes`, `avoid_nodes`. Search weights each older entry 0.92x the next, caps total taste effect at 0.12 on a 0-1 score, and excludes `avoid_nodes` outright.
