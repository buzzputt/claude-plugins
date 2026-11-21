#!/usr/bin/env python3
"""Rank library patterns against a target vibe (feature ranges) + the user's taste profile.

usage: python3 -I search.py LIB.zip --target target.json [--k 5]

target.json (all keys optional except "want"):
{
  "want":    {"density": [1, 2.5], "ds_mean": 1.2, "jump_ratio": [0, 0.3]},   # scalar or [lo, hi]
  "weights": {"density": 2},                      # default 1 each
  "levels":  ["motif", "phrase"],                 # motif | phrase | section (default motif+phrase)
  "prefer_tags": ["flowy"], "avoid_tags": ["stacky"], "require_tags": [],
  "stars_min": 4, "stars_max": 6.5,               # whole-map stars of the source diff
  "bpm": [150, 200],                              # source bpm window (beats are bpm-free; this is optional)
  "min_objects": 3, "max_objects": 60,
  "exclude_nodes": ["ab12cd34:m:7"],              # already shown
  "k": 5, "wildcards": 1, "max_per_map": 2
}
Prints JSON: {"results":[...], "pool": N, "notes":[...]}
"""
import argparse
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import osu_lib as L  # noqa: E402

# Typical spread of each feature: distance is |value - want| / scale, capped at 1.
SCALES = {"n": 8, "beats": 4, "density": 2.0, "gap_mean": 0.5, "gap_min": 0.3, "stream_ratio": 0.5,
          "triplet_ratio": 0.5, "half_ratio": 0.5, "slow_ratio": 0.5, "ds_mean": 2.0, "ds_max": 3.0,
          "stack_ratio": 0.5, "jump_ratio": 0.5, "far_ratio": 0.5, "speed_pxms": 0.5, "ang_mean": 45,
          "ang_std": 40, "sharp_ratio": 0.5, "wide_ratio": 0.5, "slider_ratio": 0.5, "slider_beats": 1.5,
          "repeat_ratio": 0.4, "nc_rate": 0.3, "regularity": 0.5, "spacing_trend": 1.5,
          "density_trend": 1.5, "intensity": 0.35, "rel": 0.4, "stars": 1.5, "aim": 1.0, "speed": 1.0,
          "bpm": 40}
LEVELS = {"motif": "m", "phrase": "p", "section": "s", "m": "m", "p": "p", "s": "s"}
SHOW = ["n", "beats", "density", "ds_mean", "jump_ratio", "stream_ratio", "slider_ratio", "ang_mean",
        "regularity", "intensity", "stars", "rel"]

# taste nudges are deliberately small: the vibe prompt leads, taste breaks ties and steers
TASTE_CAP = 0.12


def fdist(val, want, scale):
    if val is None:
        return None
    if isinstance(want, (list, tuple)):
        lo, hi = want
        if lo <= val <= hi:
            # inside the range still counts, but nearer the middle ranks higher (breaks ties among "all fit")
            half = max((hi - lo) / 2.0, 1e-9)
            return 0.1 * abs(val - (lo + hi) / 2.0) / half
        return min(1.0, 0.1 + 0.9 * min(abs(val - lo), abs(val - hi)) / scale)
    return min(1.0, abs(val - want) / scale)


def build_taste(lib):
    t = {"prefs": Counter(), "like_tags": Counter(), "avoid_tags": Counter(), "like_cl": Counter(),
         "avoid_cl": Counter(), "like_nodes": set(), "avoid_nodes": set()}
    entries = lib["taste"][::-1]            # newest first
    for age, e in enumerate(entries):
        w = 0.92 ** age
        for p in e.get("prefs", []):
            t["prefs"][p["f"]] += w * float(p.get("s", 1)) * (1 if p.get("dir", 1) > 0 else -1)
        for k_src, k_dst in (("like_tags", "like_tags"), ("avoid_tags", "avoid_tags"),
                             ("like_clusters", "like_cl"), ("avoid_clusters", "avoid_cl")):
            for x in e.get(k_src, []):
                t[k_dst][x] += w
        t["like_nodes"].update(e.get("like_nodes", []))
        t["avoid_nodes"].update(e.get("avoid_nodes", []))
    return t


def taste_nudge(node, taste, centers):
    n = 0.0
    f = node["f"]
    for feat, s in taste["prefs"].items():
        v = f.get(feat)
        if v is None or feat not in SCALES:
            continue
        z = max(-1.0, min(1.0, (v - centers.get(feat, v)) / SCALES[feat]))
        n += 0.04 * s * z
    for tg in L.tags_of(node):
        n += 0.03 * taste["like_tags"].get(tg, 0) - 0.05 * taste["avoid_tags"].get(tg, 0)
    cl = node["abs"].get("cl")
    n += 0.05 * taste["like_cl"].get(cl, 0) - 0.10 * taste["avoid_cl"].get(cl, 0)
    if node["id"] in taste["like_nodes"]:
        n += 0.05
    return max(-TASTE_CAP, min(TASTE_CAP, n))


MOMENT_PAD_MS = 1500


def same_moment(ha, a, hb, b):
    """Overlapping time in the same diff, or in sibling diffs of the same song (those are one idea in disguise)."""
    if ha["k"] == hb["k"]:
        return not (a["src"]["r"][1] < b["src"]["r"][0] or b["src"]["r"][1] < a["src"]["r"][0])
    if (ha["artist"].lower(), ha["title"].lower()) != (hb["artist"].lower(), hb["title"].lower()):
        return False
    return a["src"]["t"][0] - MOMENT_PAD_MS < b["src"]["t"][1] and b["src"]["t"][0] - MOMENT_PAD_MS < a["src"]["t"][1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lib")
    ap.add_argument("--target", required=True)
    ap.add_argument("--k", type=int)
    a = ap.parse_args()
    tg = json.load(open(a.target))
    lib = L.load_library(a.lib)
    want = tg.get("want", {})
    weights = tg.get("weights", {})
    levels = {LEVELS[x] for x in tg.get("levels", ["motif", "phrase"]) if x in LEVELS} or {"m", "p"}
    k = a.k or tg.get("k", 5)
    n_wild = tg.get("wildcards", 1) if k > 1 else 0
    notes = []
    unknown = [f for f in want if f not in SCALES]
    if unknown:
        notes.append("ignored unknown features: %s" % ", ".join(unknown))
        want = {f: v for f, v in want.items() if f in SCALES}
    if not want:
        print(json.dumps({"results": [], "pool": 0, "notes": notes + ["target has no usable features"]}))
        return

    taste = build_taste(lib)
    excl = set(tg.get("exclude_nodes", [])) | taste["avoid_nodes"]
    req, avoid, pref = (set(tg.get(x, [])) for x in ("require_tags", "avoid_tags", "prefer_tags"))
    min_n, max_n = tg.get("min_objects", 3), tg.get("max_objects", 80 if levels == {"m"} else 400)
    cl_count = Counter()
    pool = []
    for hdr, nd in L.iter_nodes(lib):
        cl_count[(nd["lv"], nd["abs"].get("cl"))] += 1
        if nd["lv"] not in levels or nd["id"] in excl:
            continue
        f = nd["f"]
        if not (min_n <= f["n"] <= max_n):
            continue
        st = f.get("stars")
        if st is not None and (st < tg.get("stars_min", -1) or st > tg.get("stars_max", 99)):
            continue
        if "bpm" in tg and not (tg["bpm"][0] <= f["bpm"] <= tg["bpm"][1]):
            continue
        tags = set(L.tags_of(nd))
        if (req and not req <= tags) or (avoid & tags):
            continue
        pool.append((hdr, nd))
    if not pool:
        print(json.dumps({"results": [], "pool": 0, "notes": notes + ["no pattern passed the filters; loosen them"]}))
        return
    centers = {ft: sum(nd["f"][ft] for _, nd in pool if nd["f"].get(ft) is not None) /
               max(1, sum(1 for _, nd in pool if nd["f"].get(ft) is not None)) for ft in SCALES}
    scored = []
    tot_w = sum(weights.get(ft, 1.0) for ft in want)
    for hdr, nd in pool:
        num = den = 0.0
        for ft, wv in want.items():
            d = fdist(nd["f"].get(ft), wv, SCALES[ft])
            if d is None:
                continue
            w = weights.get(ft, 1.0)
            num += w * d
            den += w
        if den == 0:
            continue
        score = (1 - num / den) * (den / tot_w) ** 0.5
        score += min(0.1, 0.04 * len(pref & set(L.tags_of(nd))))
        score += taste_nudge(nd, taste, centers)
        scored.append((score, hdr, nd))
    scored.sort(key=lambda x: -x[0])

    picked, per_map = [], Counter()
    # diversity cap: spread ideas across maps, but never starve a small library of results
    max_per_map = tg.get("max_per_map", max(2, -(-k // max(1, len(lib["diffs"])))))

    def ok(nd, hdr):
        if per_map[hdr["k"]] >= max_per_map:
            return False
        return not any(p[2]["abs"].get("cl") == nd["abs"].get("cl") and p[2]["lv"] == nd["lv"]
                       or same_moment(p[1], p[2], hdr, nd) for p in picked)

    for sc, hdr, nd in scored:
        if len(picked) >= k - n_wild:
            break
        if ok(nd, hdr):
            picked.append((sc, hdr, nd, False))
            per_map[hdr["k"]] += 1
    if n_wild and picked:
        best = picked[0][0]
        cands = [(sc, h, nd) for sc, h, nd in scored[:80] if sc >= max(0.35, 0.6 * best) and ok(nd, h)]
        cands.sort(key=lambda x: (cl_count[(x[2]["lv"], x[2]["abs"].get("cl"))], -x[0]))   # rarest first
        for sc, hdr, nd in cands[:n_wild]:
            picked.append((sc, hdr, nd, True))
            per_map[hdr["k"]] += 1
    if n_wild and not any(p[3] for p in picked):
        notes.append("no wildcard qualified (library too small or too uniform); filled with next-best instead")
    for sc, hdr, nd in scored:           # top up so the user still gets k ideas
        if len(picked) >= k:
            break
        if ok(nd, hdr):
            picked.append((sc, hdr, nd, False))
            per_map[hdr["k"]] += 1
    if len(lib["diffs"]) < 3:
        notes.append("library has only %d diff(s): expect repetitive ideas; more maps help" % len(lib["diffs"]))

    out = []
    for i, (sc, hdr, nd, wild) in enumerate(picked):
        f = nd["f"]
        why = []
        for ft, wv in want.items():
            d = fdist(f.get(ft), wv, SCALES[ft])
            if d is not None:
                why.append({"feature": ft, "value": f.get(ft), "want": wv, "miss": round(d, 2)})
        out.append({"label": chr(65 + i), "id": nd["id"], "level": {"m": "motif", "p": "phrase", "s": "section"}[nd["lv"]],
                    "score": round(max(0.0, min(1.0, sc)), 3), "wildcard": wild,
                    "seen": cl_count[(nd["lv"], nd["abs"].get("cl"))],
                    "map": "%s [%s]" % (hdr["title"], hdr["version"]), "mapper": hdr["creator"],
                    "ts": nd["src"]["ts"], "t_ms": nd["src"]["t"], "tags": L.tags_of(nd),
                    "desc": nd.get("desc", ""), "cluster": nd["abs"].get("cl"),
                    "abs": {k2: nd["abs"][k2] for k2 in ("k", "r", "d") if k2 in nd["abs"]},
                    "f": {s: f.get(s) for s in SHOW}, "why": why})
    print(json.dumps({"results": out, "pool": len(pool), "notes": notes}, indent=1))


if __name__ == "__main__":
    main()
