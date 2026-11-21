#!/usr/bin/env python3
"""Library housekeeping: stats, taste logging, annotations, removal.

usage:
  python3 -I library.py stats  LIB.zip
  python3 -I library.py taste  LIB.zip --json '{...}'      # append one feedback entry
  python3 -I library.py annotate LIB.zip NODE_ID [--desc "..."] [--tags a,b]
  python3 -I library.py remove LIB.zip DIFF_KEY
  python3 -I library.py init   LIB.zip                      # empty library

taste entry (all keys optional except text):
{"text": "raw words from the user", "shown": ["node ids"], "vibe": "the prompt it was about",
 "prefs": [{"f": "jump_ratio", "dir": 1, "s": 0.8}],      # dir +1 = wants more, -1 = wants less; s 0..1
 "like_tags": [], "avoid_tags": [], "like_clusters": [], "avoid_clusters": [],
 "like_nodes": [], "avoid_nodes": [], "learned": "one-line summary of what this teaches"}
"""
import argparse
import datetime
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import osu_lib as L  # noqa: E402

LIST_KEYS = ["shown", "like_tags", "avoid_tags", "like_clusters", "avoid_clusters", "like_nodes", "avoid_nodes"]


def cmd_stats(a):
    lib = L.load_library(a.lib)
    m = lib["manifest"]
    lv = Counter()
    cl = Counter()
    for hdr, nd in L.iter_nodes(lib):
        lv[nd["lv"]] += 1
        if nd["lv"] == "m":
            cl[nd["abs"]["cl"]] += 1
    top = []
    for c, k in cl.most_common(5):
        ex = next(nd for _, nd in L.iter_nodes(lib, {"m"}) if nd["abs"]["cl"] == c)
        top.append({"cluster": c, "seen": k, "kinds": ex["abs"]["k"], "rhythm": ex["abs"]["r"], "dist": ex["abs"]["d"]})
    # p10 / median / p90 of key features over real motifs (3+ objects): use these to calibrate vibe targets
    pct = {}
    for ft in ("density", "ds_mean", "jump_ratio", "stream_ratio", "slider_ratio", "ang_mean", "intensity", "stars"):
        vals = sorted(nd["f"][ft] for _, nd in L.iter_nodes(lib, {"m"}) if nd["f"]["n"] >= 3 and nd["f"].get(ft) is not None)
        if vals:
            pick = lambda q: vals[min(len(vals) - 1, int(q * len(vals)))]
            pct[ft] = [pick(0.1), pick(0.5), pick(0.9)]
    print(json.dumps({"maps": [{"key": x["key"], "title": x["title"], "version": x["version"], "stars": x["stars"],
                                "engine": x.get("engine")} for x in m["maps"]],
                      "engine": m.get("diff_engine"), "levels": {"motif": lv["m"], "phrase": lv["p"], "section": lv["s"]},
                      "motif_clusters": len(cl), "most_common_motifs": top, "feature_p10_p50_p90": pct,
                      "taste_entries": len(lib["taste"]), "updated": m.get("updated")}, indent=1))


def cmd_taste(a):
    lib = L.load_library(a.lib)
    e = json.loads(a.json)
    if not isinstance(e, dict) or not e.get("text"):
        sys.exit("taste entry needs a 'text' field")
    clean = {"ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
             "text": str(e["text"])[:1000], "vibe": str(e.get("vibe", ""))[:300],
             "learned": str(e.get("learned", ""))[:300], "prefs": []}
    for p in e.get("prefs", []):
        if p.get("f") and isinstance(p.get("dir", 1), (int, float)):
            clean["prefs"].append({"f": str(p["f"]), "dir": 1 if p["dir"] > 0 else -1,
                                   "s": max(0.0, min(1.0, float(p.get("s", 1))))})
    for k in LIST_KEYS:
        clean[k] = [str(x) for x in e.get(k, [])][:50]
    lib["taste"].append(clean)
    L.save_library(lib, a.lib)
    print(json.dumps({"ok": True, "taste_entries": len(lib["taste"])}))


def cmd_annotate(a):
    lib = L.load_library(a.lib)
    hdr, node, rows = L.find_node(lib, a.node)
    if node is None:
        sys.exit("node not found: %s" % a.node)
    if a.desc is not None:
        node["desc"] = a.desc[:400]
    if a.tags:
        for t in (x.strip() for x in a.tags.split(",")):
            if t and t not in node["tags"]:
                node["tags"].append(t)
    L.save_library(lib, a.lib)
    print(json.dumps({"ok": True, "id": node["id"], "tags": L.tags_of(node), "desc": node["desc"]}))


def cmd_remove(a):
    lib = L.load_library(a.lib)
    if a.key not in lib["diffs"]:
        sys.exit("no such diff key; run stats to list keys")
    del lib["diffs"][a.key]
    lib["manifest"]["maps"] = [m for m in lib["manifest"]["maps"] if m["key"] != a.key]
    L.save_library(lib, a.lib)
    print(json.dumps({"ok": True, "maps": len(lib["manifest"]["maps"])}))


def cmd_init(a):
    if os.path.exists(a.lib):
        sys.exit("already exists: %s" % a.lib)
    L.save_library(L.empty_library(), a.lib)
    print(json.dumps({"ok": True, "path": a.lib}))


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("stats", cmd_stats), ("taste", cmd_taste), ("annotate", cmd_annotate),
                     ("remove", cmd_remove), ("init", cmd_init)):
        p = sp.add_parser(name)
        p.add_argument("lib")
        if name == "taste":
            p.add_argument("--json", required=True)
        if name == "annotate":
            p.add_argument("node")
            p.add_argument("--desc")
            p.add_argument("--tags")
        if name == "remove":
            p.add_argument("key")
        p.set_defaults(fn=fn)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
