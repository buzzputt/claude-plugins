#!/usr/bin/env python3
"""Build an idea card for one pattern: an SVG preview + an editor how-to.

usage:
  python3 -I card.py LIB.zip NODE_ID --out DIR [--label A] [--max-objs 32]
  python3 -I card.py --node-json mutated.json --out DIR [--label B]     # for mutate.py output

Writes DIR/<label>-<id>.svg and prints JSON: {svg, quick:[...], steps:[...], snap, ds_median, shape, ...}
`quick` is the 3-5 line overview; `steps` is the full placement table (give it only when asked for more).
"""
import argparse
import colorsys
import html
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import osu_lib as L  # noqa: E402

CURVE = {"B": "Bezier", "P": "Perfect circle", "L": "Linear", "C": "Catmull"}


def hue(i, n):
    """Blue -> orange across the pattern, as a plain hex colour (works in every SVG renderer)."""
    h = (215 - 195 * (i / max(n - 1, 1))) / 360.0
    r, g, b = colorsys.hls_to_rgb(h, 0.52, 0.72)
    return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))


def turn_text(v1, v2):
    if math.hypot(*v1) < 2 or math.hypot(*v2) < 2:
        return None
    dev = math.degrees(math.atan2(v1[0] * v2[1] - v1[1] * v2[0], v1[0] * v2[0] + v1[1] * v2[1]))
    return dev  # y-down screen coords: positive = clockwise (right turn)


def shape_name(objs, moves, devs, D):
    n = len(objs)
    if n < 3:
        return "stack" if n == 2 and moves and math.hypot(*moves[0]) < 0.15 * D else "pair"
    dd = [math.hypot(*m) / D for m in moves]
    if all(d < 0.15 for d in dd):
        return "stack"
    real = [d for d in devs if d is not None]
    if not real:
        return "freeform"
    mags = [abs(d) for d in real]
    avg = sum(mags) / len(mags)
    signs = [1 if d > 0 else -1 for d in real if abs(d) >= 3]     # direction of every real turn, even gentle ones
    same = bool(signs) and all(s == signs[0] for s in signs)
    big = [1 if d > 0 else -1 for d in real if abs(d) >= 15]
    alt = len(big) >= 3 and all(big[i] != big[i + 1] for i in range(len(big) - 1))
    if avg > 160:
        return "back-and-forth"
    if avg < 6:
        return "straight line"
    if same and 100 <= avg <= 140:
        return "triangle loop"
    if same and 75 <= avg < 100:
        return "square loop"
    if same and avg < 60:
        return "curved flow (arc/circle)"
    if alt and avg >= 30:
        return "zig-zag"
    return "freeform"


def analyse(full):
    objs = L.unpack(full)
    D = L.diameter(full["cs"])
    moves = [(objs[i + 1]["x"] - objs[i]["ex"], objs[i + 1]["y"] - objs[i]["ey"]) for i in range(len(objs) - 1)]
    devs = [turn_text(moves[i - 1], moves[i]) for i in range(1, len(objs) - 1)]
    gaps = [(objs[i + 1]["t"] - objs[i]["t"]) / objs[i]["bl"] for i in range(len(objs) - 1)]
    ds_est = []
    for i, m in enumerate(moves):
        d = math.hypot(*m)
        if gaps[i] > 0.01 and d > 0.15 * D:
            ds_est.append(d / (full["sm"] * 100 * objs[i]["sv"] * gaps[i]))
    return objs, D, moves, devs, gaps, ds_est


def overlap_levels(objs, D):
    """How many earlier objects sit on top of this one (stacks, or a pattern returning to its start).
    Used only to nudge the drawing so every number stays readable."""
    lv = []
    for i, o in enumerate(objs):
        lv.append(sum(1 for j in range(i)
                      if math.hypot(objs[j]["x"] - o["x"], objs[j]["y"] - o["y"]) < (0.35 if j >= i - 2 else 0.7) * D))
    return lv


def render_svg(full, title, sub, max_objs):
    objs = L.unpack(full)
    total = len(objs)
    objs = objs[:max_objs]
    n = len(objs)
    D = L.diameter(full["cs"])
    steps = sorted(math.hypot(objs[i + 1]["x"] - objs[i]["ex"], objs[i + 1]["y"] - objs[i]["ey"]) for i in range(n - 1))
    med = steps[len(steps) // 2] if steps else D
    # dense patterns: shrink drawn circles so neighbours just touch and every number stays readable
    k = max(0.45, min(1.0, med / (0.95 * D)))
    r = D / 2 * k
    sh = overlap_levels(objs, D * k)
    nudge = max(7, 0.9 * r)     # >= ~1.3r apart, so the buried number stays visible
    off = [(nudge * h, nudge * h) for h in sh]
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="-30 -34 572 596" role="img">',
           "<title>%s</title>" % html.escape(title),
           "<style>.bg{fill:#fff}.pf{fill:#f6f6f3;stroke:#dcdcd6}.gl{stroke:#dcdcd6}.ms{stroke:#6b6b66}.mf{fill:#6b6b66}"
           ".oc{stroke:#fff}.rg{stroke:#e0a100}text{font-family:system-ui,-apple-system,sans-serif;fill:#222}"
           ".m{fill:#6b6b66}@media (prefers-color-scheme:dark){.bg{fill:#1c1c1a}.pf{fill:#262624;stroke:#3a3a37}"
           ".gl{stroke:#3a3a37}.ms{stroke:#a2a29a}.mf{fill:#a2a29a}.oc{stroke:#1c1c1a}.rg{stroke:#f0c040}"
           "text{fill:#ecece6}.m{fill:#a2a29a}}</style>",
           '<defs><marker id="ar" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" '
           'orient="auto"><path d="M0 0L8 4L0 8z" class="mf"/></marker></defs>',
           '<rect x="-30" y="-34" width="572" height="596" class="bg"/>',
           '<text x="0" y="-14" font-size="15" font-weight="600">%s</text>' % html.escape(title),
           '<rect x="0" y="0" width="512" height="384" rx="4" class="pf"/>']
    for gx in range(64, 512, 64):
        out.append('<line x1="%d" y1="0" x2="%d" y2="384" class="gl" stroke-width=".6"/>' % (gx, gx))
    for gy in range(64, 384, 64):
        out.append('<line x1="0" y1="%d" x2="512" y2="%d" class="gl" stroke-width=".6"/>' % (gy, gy))
    # cursor path
    for i in range(n - 1):
        x1, y1 = objs[i]["ex"] + off[i][0], objs[i]["ey"] + off[i][1]
        x2, y2 = objs[i + 1]["x"] + off[i + 1][0], objs[i + 1]["y"] + off[i + 1][1]
        if math.hypot(x2 - x1, y2 - y1) > 4:
            out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" class="ms" stroke-width="1.4" '
                       'stroke-dasharray="5 4" marker-end="url(#ar)" opacity=".8"/>' % (x1, y1, x2, y2))
    # bodies first, heads on top
    for i, o in enumerate(objs):
        col = hue(i, n)
        ox, oy = off[i]
        if o["k"] == "s":
            path = L.slider_path(o["sl"]["c"], o["sl"]["p"], o["sl"]["l"])
            pts = " ".join("%.1f,%.1f" % (px + ox, py + oy) for px, py in path)
            out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="%.1f" stroke-linecap="round" '
                       'stroke-linejoin="round" opacity=".28"/>' % (pts, col, r * 1.8))
            out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2" stroke-linecap="round" '
                       'stroke-linejoin="round"/>' % (pts, col))
            ex, ey = o["ex"] + ox, o["ey"] + oy
            out.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" stroke="%s" stroke-width="2.5"/>' % (ex, ey, r * 0.45, col))
            if o["sl"]["n"] > 1:
                out.append('<text x="%.1f" y="%.1f" font-size="11" text-anchor="middle" font-weight="700" '
                           'fill="%s" style="fill:%s">x%d</text>' % (ex, ey - r * 0.6, col, col, o["sl"]["n"]))
    for i, o in enumerate(objs):
        col = hue(i, n)
        ox, oy = off[i]
        x, y = o["x"] + ox, o["y"] + oy
        if o["k"] == "p":
            out.append('<circle cx="%d" cy="%d" r="%.1f" fill="none" stroke="%s" stroke-width="3"/>' % (x, y, r * 1.6, col))
        if o["nc"]:
            out.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" class="rg" stroke-width="2" '
                       'stroke-dasharray="3 3"/>' % (x, y, r + 5))
        out.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" class="oc" stroke-width="2"/>' % (x, y, r, col))
        out.append('<text x="%.1f" y="%.1f" font-size="%.0f" font-weight="700" text-anchor="middle" '
                   'dominant-baseline="central" style="fill:#fff">%s</text>' % (x, y + 1, max(11, r * 0.95), "S" if o["k"] == "p" else i + 1))
    # rhythm strip
    t0 = objs[0]["t"]
    bl = objs[0]["bl"]
    t_end = max(o["te"] for o in objs)
    span = max((t_end - t0) / bl, 0.5)
    X0, X1, Y = 16, 496, 462
    sx = lambda t: X0 + (t - t0) / bl / span * (X1 - X0)
    out.append('<text x="0" y="418" font-size="11" class="m">rhythm (beats from first object)</text>')
    out.append('<line x1="%d" y1="%d" x2="%d" y2="%d" class="gl" stroke-width="1.5"/>' % (X0, Y, X1, Y))
    step = 1 if span <= 16 else 4 if span <= 64 else 8     # beat-tick spacing: always labelled
    b = 0
    while b <= span + 1e-6:
        x = X0 + b / span * (X1 - X0)
        out.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" class="ms" stroke-width="1.2"/>' % (x, Y - 9, x, Y + 9))
        out.append('<text x="%.1f" y="%d" font-size="9.5" text-anchor="middle" class="m">%g</text>' % (x, Y + 22, b))
        b += step
    if span <= 6:
        q = 0.25
        while q <= span + 1e-6:
            if abs(q - round(q)) > 1e-6:
                x = X0 + q / span * (X1 - X0)
                out.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" class="gl" stroke-width="1"/>' % (x, Y - 5, x, Y + 5))
            q += 0.25
    for i, o in enumerate(objs):
        col = hue(i, n)
        x = sx(o["t"])
        if o["k"] == "s":
            xe = max(sx(o["te"]), x + 6)
            out.append('<rect x="%.1f" y="%d" width="%.1f" height="12" rx="6" fill="%s" opacity=".55"/>' % (x - 6, Y - 6, xe - x + 12, col))
        out.append('<circle cx="%.1f" cy="%d" r="6.5" fill="%s" class="oc" stroke-width="1.5"/>' % (x, Y, col))
        if n <= 24:
            out.append('<text x="%.1f" y="%d" font-size="9.5" text-anchor="middle" font-weight="600">%d</text>' % (x, Y - 13, i + 1))
        if i < n - 1:
            x2 = sx(objs[i + 1]["t"])
            if x2 - x >= 26:
                tok = L.quantize_gap((objs[i + 1]["t"] - o["t"]) / o["bl"])[1]
                out.append('<text x="%.1f" y="%d" font-size="10" text-anchor="middle" class="m">%s</text>' % ((x + x2) / 2, Y + 38, tok))
    notes = []
    if total > n:
        notes.append("showing first %d of %d objects" % (n, total))
    if k < 0.98:
        notes.append("circles drawn at %d%% of true size so this dense pattern stays readable" % round(k * 100))
    if any(sh):
        notes.append("objects landing on top of each other are nudged down-right so each number shows")
    out.append('<text x="0" y="518" font-size="11.5" class="m">%s</text>' % html.escape(sub))
    for j, note in enumerate(notes):                      # one short line each so nothing clips
        out.append('<text x="0" y="%d" font-size="11" class="m">%s</text>' % (536 + 16 * j, html.escape(note)))
    H = 596 + 16 * max(0, len(notes) - 1)
    out.append("</svg>")
    return "\n".join(out).replace('572 596', '572 %d' % H).replace('height="596"', 'height="%d"' % H)


def build(full, label, title, ts, max_objs, meta_line=""):
    objs, D, moves, devs, gaps, ds_est = analyse(full)
    n = len(objs)
    snap = L.snap_divisor(gaps)
    ds_med = sorted(ds_est)[len(ds_est) // 2] if ds_est else None
    shape = shape_name(objs, moves, devs, D)
    toks = [L.quantize_gap(g)[1] for g in gaps]
    rh = ", ".join("%sx %s" % (c, t) for t, c in L.Counter(toks).most_common(4)) if toks else "single object"
    real = [abs(d) for d in devs if d is not None]
    turn = "%d" % (sum(real) / len(real)) if real else None
    dd = [math.hypot(*m) / D for m in moves]
    quick = [
        "Set up: %.0f BPM, CS %g / AR %g, beat snap 1/%d%s." % (full["bpm"], full["cs"], full["ar"], snap,
                                                                (", distance snap about %.1fx (approx.)" % ds_med) if ds_med else ""),
        "Rhythm: %d objects; gaps %s." % (n, rh),
        "Shape: %s%s; average spacing %.1f circle diameters." % (
            shape, (" with ~%s deg direction change per object" % turn) if turn else "",
            (sum(dd) / len(dd)) if dd else 0),
        "Start: place object 1 at (%d, %d), then follow the table (SVG numbers match the table)." % (objs[0]["x"], objs[0]["y"]),
    ]
    steps = []
    for i, o in enumerate(objs):
        tb = (o["t"] - objs[0]["t"]) / objs[0]["bl"]
        line = "#%d  %s  at (%d, %d)  t=+%.2f beats" % (i + 1, {"c": "circle", "s": "slider", "p": "spinner"}[o["k"]], o["x"], o["y"], tb)
        if o["nc"]:
            line += "  [new combo]"
        if i > 0:
            d = math.hypot(*moves[i - 1])
            line += "  | %s after prev, %.1f diam" % (toks[i - 1], d / D)
            if d > 0.15 * D and gaps[i - 1] > 0.01:
                line += " (~DS %.2fx)" % (d / (full["sm"] * 100 * objs[i - 1]["sv"] * gaps[i - 1]))
        if 1 <= i <= n - 2 and devs[i - 1] is not None:
            line += "  | turn %d deg %s" % (abs(devs[i - 1]), "right" if devs[i - 1] > 0 else "left")
        if o["k"] == "s":
            sl = o["sl"]
            line += "  | %s slider, %d slide(s), length %g px, lasts %.2f beats, tail (%d, %d), points %s" % (
                CURVE.get(sl["c"], sl["c"]), sl["n"], sl["l"], o["dur"] / o["bl"], o["ex"], o["ey"],
                " ".join("(%d,%d)" % tuple(p) for p in sl["p"][1:]))
        steps.append(line)
    svg = render_svg(full, "%s · %s" % (label, title), "%s · %d objects · %.0f BPM · snap 1/%d · shape: %s" %
                     (ts.strip().rstrip("-").strip() or "generated", n, full["bpm"], snap, shape), max_objs)
    return svg, {"quick": quick, "steps": steps, "snap": snap, "ds_median": round(ds_med, 2) if ds_med else None,
                 "shape": shape, "objects": n}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lib", nargs="?")
    ap.add_argument("node", nargs="?")
    ap.add_argument("--node-json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", default="A")
    ap.add_argument("--max-objs", type=int, default=32)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    if a.node_json:
        nd = json.load(open(a.node_json))
        full, title, ts, nid = nd["full"], nd.get("map", "generated"), nd.get("ts", "generated"), nd.get("id", "mutant")
        title = "%s (%s)" % (title, nd.get("op", "mutated"))
    else:
        lib = L.load_library(a.lib)
        hdr, node, rows = L.find_node(lib, a.node)
        if node is None:
            print(json.dumps({"error": "node not found: %s" % a.node}))
            sys.exit(1)
        by_id = {r["id"]: r for r in rows if not r.get("hdr")}
        full = L.node_full(by_id, node)
        title = "%s [%s]" % (hdr["title"], hdr["version"])
        ts, nid = node["src"]["ts"], node["id"]
    svg, info = build(full, a.label, title, ts, a.max_objs)
    path = os.path.join(a.out, "%s-%s.svg" % (a.label, nid.replace(":", "_")))
    with open(path, "w") as fh:
        fh.write(svg)
    info.update(svg=path, id=nid, label=a.label, source=title, ts=ts)
    if not a.node_json and node.get("ch"):
        info["children"] = node["ch"]          # phrases of a section / motifs of a phrase, for drilling down
    print(json.dumps(info, indent=1))


if __name__ == "__main__":
    main()
