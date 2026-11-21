#!/usr/bin/env python3
"""Make a variant of a library pattern. Output is a node JSON for card.py (nothing is saved to the library).

usage: python3 -I mutate.py LIB.zip NODE_ID --op OP --out variant.json
  OP: mirror_x | mirror_y | rotate:DEG | scale:FACTOR | retime:OTHER_NODE_ID

Why these four: they change the *feel* (direction, size, speed of the cursor, rhythm) while keeping the
idea recognisable. Every variant is re-derived through the same code as library patterns, so its features
are comparable. Variants are pulled back inside the playfield; anything that can't fit is reported.
"""
import argparse
import copy
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import osu_lib as L  # noqa: E402


def xform_points(full, fn):
    for r in full["o"]:
        r[0], r[1] = fn(r[0], r[1])
        if len(r) > 9 and r[4] == "s":
            ex = r[9]
            ex["p"] = [list(fn(px, py)) for px, py in ex["p"]]
            ex["e"] = list(fn(*ex["e"]))


def bbox(full):
    xs, ys = [], []
    for r in full["o"]:
        xs.append(r[0]); ys.append(r[1])
        if len(r) > 9 and r[4] == "s":
            for px, py in L.slider_path(r[9]["c"], r[9]["p"], r[9]["l"]):
                xs.append(px); ys.append(py)
    return min(xs), min(ys), max(xs), max(ys)


def fit_playfield(full, notes):
    x0, y0, x1, y1 = bbox(full)
    dx = -x0 if x0 < 0 else (L.PLAY_W - x1 if x1 > L.PLAY_W else 0)
    dy = -y0 if y0 < 0 else (L.PLAY_H - y1 if y1 > L.PLAY_H else 0)
    if x1 - x0 > L.PLAY_W or y1 - y0 > L.PLAY_H:
        notes.append("pattern is larger than the playfield after this change; parts sit outside it")
    if dx or dy:
        xform_points(full, lambda x, y: (int(round(x + dx)), int(round(y + dy))))
        notes.append("shifted by (%+d, %+d) to stay inside the playfield" % (dx, dy))


def centroid(full):
    return (sum(r[0] for r in full["o"]) / len(full["o"]), sum(r[1] for r in full["o"]) / len(full["o"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lib")
    ap.add_argument("node")
    ap.add_argument("--op", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    lib = L.load_library(a.lib)
    hdr, node, rows = L.find_node(lib, a.node)
    if node is None:
        sys.exit(json.dumps({"error": "node not found"}))
    by_id = {r["id"]: r for r in rows if not r.get("hdr")}
    full = copy.deepcopy(L.node_full(by_id, node))
    notes = []
    op = a.op
    if op == "mirror_x":
        xform_points(full, lambda x, y: (L.PLAY_W - x, y))
    elif op == "mirror_y":
        xform_points(full, lambda x, y: (x, L.PLAY_H - y))
    elif op.startswith("rotate:"):
        deg = float(op.split(":")[1])
        cx, cy = centroid(full)
        c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
        xform_points(full, lambda x, y: (int(round(cx + (x - cx) * c - (y - cy) * s)),
                                         int(round(cy + (x - cx) * s + (y - cy) * c))))
        fit_playfield(full, notes)
    elif op.startswith("scale:"):
        f = float(op.split(":")[1])
        cx, cy = centroid(full)
        xform_points(full, lambda x, y: (int(round(cx + (x - cx) * f)), int(round(cy + (y - cy) * f))))
        for r in full["o"]:
            if len(r) > 9 and r[4] == "s":
                r[9]["l"] = round(r[9]["l"] * f, 2)
        if any(r[4] == "s" for r in full["o"]):
            notes.append("slider lengths were scaled too, so they now last %.2fx as long at the same SV; "
                         "adjust SV or length in the editor to keep the rhythm" % f)
        fit_playfield(full, notes)
    elif op.startswith("retime:"):
        oid = op.split(":", 1)[1]
        _, other, orows = L.find_node(lib, oid)
        if other is None:
            sys.exit(json.dumps({"error": "retime source not found: %s" % oid}))
        ofull = L.node_full({r["id"]: r for r in orows if not r.get("hdr")}, other)
        if len(ofull["o"]) != len(full["o"]):
            sys.exit(json.dumps({"error": "retime needs equal object counts (%d vs %d)" % (len(full["o"]), len(ofull["o"]))}))
        bl = full["o"][0][7]
        t0, b0 = full["o"][0][2], full["o"][0][3]
        acc = 0.0
        for i, r in enumerate(full["o"]):
            if i:
                acc += (ofull["o"][i][2] - ofull["o"][i - 1][2]) / ofull["o"][i - 1][7]
            r[2] = int(round(t0 + acc * bl))
            r[3] = round(b0 + acc, 3)
        notes.append("rhythm borrowed from %s; positions unchanged, so spacing per beat changed" % oid)
    else:
        sys.exit(json.dumps({"error": "unknown op: %s" % op}))

    ab, mv, an, f = L.derive(full)
    for k in ("aim", "speed", "rel", "stars"):          # difficulty can't be recomputed for a variant
        if node["f"].get(k) is not None:
            f[k] = node["f"][k]
    L.add_intensity(f)
    out = {"id": "%s~%s" % (node["id"], op.replace(":", "")), "src_id": node["id"], "op": op,
           "map": "%s [%s]" % (hdr["title"], hdr["version"]), "ts": node["src"]["ts"], "full": full,
           "abs": ab, "f": f, "tags": L.autotag(f), "notes": notes}
    with open(a.out, "w") as fh:
        json.dump(out, fh, separators=(",", ":"))
    print(json.dumps({"ok": True, "out": a.out, "id": out["id"], "notes": notes, "cluster_changed": ab["cl"] != node["abs"]["cl"],
                      "features": {k: f.get(k) for k in ("n", "density", "ds_mean", "jump_ratio", "ang_mean", "intensity")}}))


if __name__ == "__main__":
    main()
