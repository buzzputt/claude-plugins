#!/usr/bin/env python3
"""Shared helpers for osu-pattern-lab (osu!standard). Standard library only.

Design rule: every derived thing (abstract layer, features, tags) is computed
from a *full layer* (a list of compact objects). Ingest, mutate and card all go
through derive(), so a mutated pattern is scored exactly like a library one.
"""
import bisect
import datetime
import hashlib
import json
import math
import os
import re
import tempfile
import zipfile
from collections import Counter

PLAY_W, PLAY_H = 512, 384
MAX_MEMBER = 40 * 1024 * 1024      # refuse absurd zip members (zip-bomb guard)
MAX_OSU = 8 * 1024 * 1024
SCHEMA = 1

# ----------------------------------------------------------------- rhythm
GAP_GRID = [(1 / 16, "1/16"), (1 / 12, "1/12"), (1 / 8, "1/8"), (1 / 6, "1/6"),
            (1 / 4, "1/4"), (1 / 3, "1/3"), (3 / 8, "3/8"), (1 / 2, "1/2"),
            (2 / 3, "2/3"), (3 / 4, "3/4"), (1.0, "1"), (4 / 3, "4/3"),
            (1.5, "3/2"), (2.0, "2"), (3.0, "3"), (4.0, "4")]


def quantize_gap(b):
    """beats -> (snapped_beats, token). Off-grid gaps get a '~' token."""
    if b <= 0.01:
        return 0.0, "0"
    if b >= 4.5:
        v = round(b * 2) / 2
        return v, ("%g" % v)
    best = min(GAP_GRID, key=lambda g: abs(g[0] - b))
    if abs(best[0] - b) <= max(0.02, 0.08 * b):
        return best
    v = round(b * 20) / 20
    return v, "~%.2f" % v


def snap_divisor(beat_values):
    """Smallest common editor snap (1/N) that lands every gap on the grid."""
    for n in (1, 2, 3, 4, 6, 8, 12, 16):
        if all(abs(v * n - round(v * n)) < 0.06 for v in beat_values if v > 0):
            return n
    return 16


# --------------------------------------------------------------- geometry
def diameter(cs):
    return 2 * (54.4 - 4.48 * cs)


def _bezier(ctrl, n):
    out = []
    m = len(ctrl)
    for s in range(n + 1):
        t = s / n
        pts = list(ctrl)
        for _ in range(1, m):
            pts = [((1 - t) * pts[i][0] + t * pts[i + 1][0],
                    (1 - t) * pts[i][1] + t * pts[i + 1][1]) for i in range(len(pts) - 1)]
        out.append(pts[0])
    return out


def _poly_len(poly):
    return sum(math.dist(poly[i], poly[i + 1]) for i in range(len(poly) - 1))


def _catmull(pts):
    out = []
    for i in range(len(pts) - 1):
        p0 = pts[i - 1] if i > 0 else pts[i]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < len(pts) else pts[i + 1]
        for s in range(12):
            t = s / 12
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t +
                                    (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2 +
                                    (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    out.append(pts[-1])
    return out


def _fit_length(poly, length):
    """Cut or linearly extend polyline so its length equals `length` (osu rule)."""
    if len(poly) < 2 or length <= 0:
        return poly
    acc = 0.0
    for i in range(len(poly) - 1):
        seg = math.dist(poly[i], poly[i + 1])
        if acc + seg >= length:
            f = (length - acc) / seg if seg > 0 else 0
            cut = (poly[i][0] + (poly[i + 1][0] - poly[i][0]) * f,
                   poly[i][1] + (poly[i + 1][1] - poly[i][1]) * f)
            return poly[:i + 1] + [cut]
        acc += seg
    # too short: extend along the last non-degenerate segment
    for i in range(len(poly) - 1, 0, -1):
        seg = math.dist(poly[i - 1], poly[i])
        if seg > 0:
            f = (length - acc) / seg
            ext = (poly[i][0] + (poly[i][0] - poly[i - 1][0]) * f,
                   poly[i][1] + (poly[i][1] - poly[i - 1][1]) * f)
            return poly + [ext]
    return poly


def slider_path(ctype, pts, length):
    """Polyline for a slider. pts includes the head position as pts[0]."""
    pts = [tuple(map(float, p)) for p in pts]
    if len(pts) < 2:
        return pts
    poly = None
    if ctype == "P" and len(pts) == 3:
        (ax, ay), (bx, by), (cx, cy) = pts
        d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        if abs(d) > 1e-6:
            ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
            uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
            r = math.hypot(ax - ux, ay - uy)
            if 1 < r < 5000:
                a0 = math.atan2(ay - uy, ax - ux)
                cross = (bx - ax) * (cy - by) - (by - ay) * (cx - bx)
                sgn = 1 if cross > 0 else -1
                sweep = length / r
                n = max(6, min(96, int(sweep / 0.15) + 1))
                poly = [(ux + r * math.cos(a0 + sgn * sweep * s / n),
                         uy + r * math.sin(a0 + sgn * sweep * s / n)) for s in range(n + 1)]
        if poly is None:
            ctype = "L"
    if poly is None and ctype == "C":
        poly = _catmull(pts)
    if poly is None and ctype == "L":
        poly = pts
    if poly is None:  # bezier with red anchors (duplicate points split segments)
        segs, cur = [], [pts[0]]
        for p in pts[1:]:
            cur.append(p)
            if p == cur[-2] and len(cur) > 2:
                segs.append(cur[:-1])
                cur = [p]
        segs.append(cur)
        poly = []
        for sg in segs:
            if len(sg) < 2:
                continue
            est = _poly_len(sg)
            seg_pts = _bezier(sg, max(4, min(64, int(est / 6))))
            poly += seg_pts if not poly else seg_pts[1:]
    return _fit_length(poly, length)


# ------------------------------------------------------------------ parse
class NotStandard(ValueError):
    """Map is a valid beatmap but another game mode; skipped, not an error."""


class Timing:
    def __init__(self, lines):
        self.all, reds, greens = [], [], []
        for ln in lines:
            p = [x.strip() for x in ln.split(",")]
            if len(p) < 2:
                continue
            try:
                t, bl = float(p[0]), float(p[1])
                meter = int(p[2]) if len(p) > 2 and p[2] else 4
                unh = (p[6] == "1") if len(p) > 6 and p[6] != "" else True
                eff = int(p[7]) if len(p) > 7 and p[7] != "" else 0
            except ValueError:
                continue
            if bl < 0:
                unh = False
            self.all.append((t, eff & 1))
            if unh:
                reds.append((t, bl, max(1, meter)))
            else:
                greens.append((t, max(0.1, min(10.0, -100.0 / bl if bl else 1.0))))
        if not reds:
            raise ValueError("beatmap has no uninherited (red) timing point")
        self.red = sorted(reds)
        self.green = sorted(greens)
        self.all.sort()
        self._rt = [r[0] for r in self.red]
        self._gt = [g[0] for g in self.green]
        self._at = [a[0] for a in self.all]

    def red_at(self, t):
        i = bisect.bisect_right(self._rt, t) - 1
        return self.red[max(i, 0)]

    def sv_at(self, t):
        red_t = self.red_at(t)[0]
        i = bisect.bisect_right(self._gt, t) - 1
        if i >= 0 and self.green[i][0] >= red_t:
            return self.green[i][1]
        return 1.0

    def kiai_at(self, t):
        i = bisect.bisect_right(self._at, t) - 1
        return bool(self.all[i][1]) if i >= 0 else False


def _kv(lines):
    d = {}
    for ln in lines:
        if ":" in ln:
            k, v = ln.split(":", 1)
            d[k.strip()] = v.strip()
    return d


def parse_map(text):
    """Parse osu!standard .osu text -> dict(meta, diff, objects, bad)."""
    text = text.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
    sections, cur = {}, None
    for ln in text.split("\n"):
        s = ln.strip()
        if not s or s.startswith("//"):
            continue
        m = re.match(r"^\[(\w+)\]$", s)
        if m:
            cur = m.group(1)
            sections[cur] = []
        elif cur:
            sections[cur].append(s)
    gen, meta, dif = (_kv(sections.get(k, [])) for k in ("General", "Metadata", "Difficulty"))
    mode = int(gen.get("Mode", "0") or 0)
    if mode != 0:
        raise NotStandard({1: "taiko", 2: "catch", 3: "mania"}.get(mode, "mode %d" % mode))
    cs = float(dif.get("CircleSize", 4))
    ar = float(dif.get("ApproachRate", dif.get("OverallDifficulty", 5)))
    od = float(dif.get("OverallDifficulty", 5))
    sm = float(dif.get("SliderMultiplier", 1.4))
    tm = Timing(sections.get("TimingPoints", []))
    objs, bad, combo = [], 0, 0
    force_nc = True
    for idx, ln in enumerate(sections.get("HitObjects", [])):
        p = ln.split(",")
        try:
            x, y, t = int(float(p[0])), int(float(p[1])), int(float(p[2]))
            typ, hs = int(p[3]), int(p[4] or 0)
            red_t, bl, meter = tm.red_at(t)
            o = {"i": idx, "x": x, "y": y, "t": t, "hs": hs, "bl": bl, "meter": meter,
                 "red_t": red_t, "bpos": (t - red_t) / bl, "kiai": tm.kiai_at(t),
                 "ex": x, "ey": y, "dur": 0, "sv": round(tm.sv_at(t), 3)}
            if typ & 128:
                raise ValueError("mania hold")
            nc = bool(typ & 4) or force_nc
            force_nc = False
            if typ & 8:
                o["k"] = "p"
                o["dur"] = max(0, int(float(p[5])) - t)
                force_nc = True
            elif typ & 2:
                o["k"] = "s"
                cp = p[5].split("|")
                ctype = cp[0]
                pts = [(x, y)] + [tuple(int(float(v)) for v in c.split(":")) for c in cp[1:]]
                slides, length = int(p[6]), float(p[7])
                sv = tm.sv_at(t)
                dur = length / (sm * 100 * sv) * bl * slides
                path = slider_path(ctype, pts, length)
                end = path[-1] if slides % 2 == 1 else path[0]
                o.update(ex=int(round(end[0])), ey=int(round(end[1])), dur=int(round(dur)), sv=round(sv, 3),
                         sl={"c": ctype, "p": [list(q) for q in pts], "n": slides,
                             "l": round(length, 2)})
            else:
                o["k"] = "c"
            combo = 1 if nc else combo + 1
            o["nc"], o["combo"], o["te"] = int(nc), combo, t + o["dur"]
            objs.append(o)
        except (ValueError, IndexError):
            bad += 1
    objs.sort(key=lambda o: (o["t"], o["i"]))
    return {"meta": meta, "diff": {"cs": cs, "ar": ar, "od": od, "sm": sm}, "objects": objs,
            "bad": bad, "timing": tm}


def map_hash(raw_bytes):
    txt = raw_bytes.decode("utf-8", "replace").lstrip("﻿").replace("\r\n", "\n")
    return hashlib.sha1(txt.encode("utf-8")).hexdigest()


def editor_ts(objs, i, span=8):
    """Timestamp in the osu! editor's pasteable format, e.g. 01:23:456 (1,2,3) - """
    t = objs[i]["t"]
    combos = ",".join(str(o["combo"]) for o in objs[i:i + span])
    return "%02d:%02d:%03d (%s) - " % (t // 60000, (t // 1000) % 60, t % 1000, combos)


# ------------------------------------------------------------ full layer
def compact_obj(o):
    """[x,y,t,bpos,kind,newcombo,hitsound,beatLength,svMult, extra?]"""
    row = [o["x"], o["y"], o["t"], round(o["bpos"], 3), o["k"], o["nc"], o["hs"], round(o["bl"], 3),
           round(o.get("sv", 1.0), 3)]
    if o["k"] == "s":
        sl = dict(o["sl"])
        sl.update(e=[o["ex"], o["ey"]], d=o["dur"])
        row.append(sl)
    elif o["k"] == "p":
        row.append({"d": o["dur"]})
    return row


def make_full(objs, diff, link_in=None):
    return {"bpm": round(60000.0 / objs[0]["bl"], 2), "cs": diff["cs"], "ar": diff["ar"],
            "od": diff["od"], "sm": diff["sm"], "o": [compact_obj(o) for o in objs],
            "li": link_in}


def unpack(full):
    out = []
    for r in full["o"]:
        x, y, t, bpos, k, nc, hs, bl, sv = r[:9]
        ex = r[9] if len(r) > 9 else None
        d = {"x": x, "y": y, "t": t, "bpos": bpos, "k": k, "nc": nc, "hs": hs, "bl": bl, "sv": sv,
             "ex": x, "ey": y, "dur": 0, "sl": None}
        if k == "s":
            d["ex"], d["ey"] = ex["e"]
            d["dur"], d["sl"] = ex["d"], ex
        elif k == "p":
            d["dur"] = ex["d"]
        d["te"] = t + d["dur"]
        out.append(d)
    return out


# ---------------------------------------------------------------- derive
DIST_BINS = [(0.15, "S"), (1.25, "N"), (2.5, "M"), (4.0, "L"), (1e9, "X")]  # in circle diameters


def dist_letter(d_diam):
    for lim, ch in DIST_BINS:
        if d_diam < lim:
            return ch


def _mean(a):
    return sum(a) / len(a) if a else None


def _std(a):
    if len(a) < 2:
        return None
    m = sum(a) / len(a)
    return math.sqrt(sum((v - m) ** 2 for v in a) / len(a))


def _r(v, n=3):
    return None if v is None else round(v, n)


def derive(full):
    """full layer -> (abstract layer, move list, angle list, feature dict)."""
    objs = unpack(full)
    n = len(objs)
    D = diameter(full["cs"])
    gaps, toks, moves = [], [], []
    for i in range(n - 1):
        g = (objs[i + 1]["t"] - objs[i]["t"]) / objs[i]["bl"]
        gaps.append(quantize_gap(g))
        v = (objs[i + 1]["x"] - objs[i]["ex"], objs[i + 1]["y"] - objs[i]["ey"])
        moves.append(v)
    dists = [math.hypot(*v) for v in moves]
    dd = [d / D for d in dists]
    letters = [dist_letter(d) for d in dd]
    devs = []   # signed direction change in degrees, None where undefined (stack)
    for i in range(1, n - 1):
        v1, v2 = moves[i - 1], moves[i]
        if math.hypot(*v1) < 2 or math.hypot(*v2) < 2:
            devs.append(None)
        else:
            devs.append(math.degrees(math.atan2(v1[0] * v2[1] - v1[1] * v2[0],
                                                v1[0] * v2[0] + v1[1] * v2[1])))
    sign = 1
    for d in devs:
        if d is not None and abs(d) >= 15:
            sign = 1 if d > 0 else -1
            break
    nd = [None if d is None else sign * d for d in devs]
    fine = [None if d is None else int(round(d / 15.0) * 15) for d in nd]
    coarse = [None if d is None else int(round(d / 45.0) * 45) for d in nd]
    sd = [quantize_gap(o["dur"] / o["bl"])[1] if o["k"] == "s" else "" for o in objs]
    kinds = "".join(o["k"] for o in objs)
    rtoks = [g[1] for g in gaps]
    key = "%s|%s|%s|%s|%s" % (kinds, "/".join(rtoks), "".join(letters),
                              ",".join("_" if c is None else str(c) for c in coarse),
                              "/".join(s for s in sd if s))
    cid = hashlib.md5(key.encode()).hexdigest()[:8]
    abstract = {"k": kinds, "r": rtoks, "sd": [s for s in sd if s], "d": "".join(letters),
                "a": fine, "key": key, "cl": cid}

    # ---- features
    gb = [g[0] for g in gaps]
    nm = max(len(gb), 1)
    ang = [180 - abs(d) for d in devs if d is not None]
    span_beats = (objs[-1]["te"] - objs[0]["t"]) / objs[0]["bl"] if n > 1 else 0
    start_span = (objs[-1]["t"] - objs[0]["t"]) / objs[0]["bl"] if n > 1 else 0
    sl = [o for o in objs if o["k"] == "s"]
    pxms = [dists[i] / max(objs[i + 1]["t"] - objs[i]["t"], 1) for i in range(len(dists))]
    triples = [(rtoks[i + 1], letters[i + 1], coarse[i]) for i in range(len(coarse))
               if i + 1 < len(rtoks)]
    reg = None
    if len(triples) >= 3:
        c = Counter(triples)
        h = -sum(v / len(triples) * math.log2(v / len(triples)) for v in c.values())
        hmax = math.log2(len(triples))
        reg = 1 - h / hmax if hmax > 0 else 1.0
    f = {
        "n": n, "beats": _r(span_beats, 2), "ms": objs[-1]["te"] - objs[0]["t"],
        "bpm": full["bpm"],
        "density": _r((n - 1) / max(start_span, 0.25), 3) if n > 1 else 0.0,
        "gap_mean": _r(_mean(gb), 3), "gap_min": _r(min(gb), 3) if gb else None,
        "stream_ratio": _r(sum(1 for g in gb if 0 < g <= 0.26) / nm, 3) if gb else 0.0,
        "triplet_ratio": _r(sum(1 for g in gb if abs(g - 1 / 3) < 0.04 or abs(g - 1 / 6) < 0.03) / nm, 3) if gb else 0.0,
        "half_ratio": _r(sum(1 for g in gb if abs(g - 0.5) < 0.04) / nm, 3) if gb else 0.0,
        "slow_ratio": _r(sum(1 for g in gb if g >= 1) / nm, 3) if gb else 0.0,
        "ds_mean": _r(_mean(dd), 3), "ds_max": _r(max(dd), 3) if dd else None,
        "stack_ratio": _r(sum(1 for d in dd if d < 0.15) / nm, 3) if dd else 0.0,
        "jump_ratio": _r(sum(1 for d in dd if d >= 2.5) / nm, 3) if dd else 0.0,
        "far_ratio": _r(sum(1 for d in dd if d >= 4.0) / nm, 3) if dd else 0.0,
        "speed_pxms": _r(_mean(pxms), 3),
        "ang_mean": _r(_mean(ang), 1), "ang_std": _r(_std(ang), 1),
        "sharp_ratio": _r(sum(1 for a in ang if a < 90) / len(ang), 3) if ang else None,
        "wide_ratio": _r(sum(1 for a in ang if a >= 150) / len(ang), 3) if ang else None,
        "slider_ratio": _r(len(sl) / n, 3),
        "slider_beats": _r(_mean([o["dur"] / o["bl"] for o in sl]), 2),
        "repeat_ratio": _r(sum(1 for o in sl if o["sl"]["n"] > 1) / n, 3),
        "nc_rate": _r(sum(o["nc"] for o in objs) / n, 3),
        "regularity": _r(reg, 3),
    }
    third = len(dd) // 3
    if len(dd) >= 6 and third >= 2:
        f["spacing_trend"] = _r(_mean(dd[-third:]) - _mean(dd[:third]), 3)
        g1, g2 = _mean(gb[:third]), _mean(gb[-third:])
        f["density_trend"] = _r((1 / g2 if g2 else 0) - (1 / g1 if g1 else 0), 3)
    else:
        f["spacing_trend"] = f["density_trend"] = None
    mv = [[_r(gb[i], 3), int(round(dists[i]))] for i in range(len(dists))]
    return abstract, mv, [_r(a, 1) for a in ang], f


def add_intensity(f):
    """intensity 0-1 = mean of: density/4, ds_mean/4, rel (local strain vs map peak)."""
    parts = []
    if f.get("density") is not None:
        parts.append(min(1.0, f["density"] / 4.0))
    if f.get("ds_mean") is not None:
        parts.append(min(1.0, f["ds_mean"] / 4.0))
    if f.get("rel") is not None:
        parts.append(min(1.0, f["rel"]))
    f["intensity"] = _r(sum(parts) / len(parts), 3) if parts else None
    return f


def autotag(f, kiai=False):
    """Baseline vibe tags, computed from features whenever a library is loaded (never stored), so
    recalibrating a threshold fixes old libraries too. Thresholds were set from the measured spread
    of a real 6-diff mapset (2-7 stars) so each tag lands on roughly 5-35% of patterns; a tag that
    fits nearly everything carries no information. Rationale in references/vibe-to-features.md."""
    t = []
    g = lambda k: f.get(k) if f.get(k) is not None else 0
    n = f["n"]
    if g("stream_ratio") >= 0.6 and n >= 6: t.append("stream")
    elif g("stream_ratio") >= 0.3 and n >= 3: t.append("burst")
    if g("jump_ratio") >= 0.5: t.append("jumpy")
    if g("far_ratio") >= 0.3: t.append("wide-jumps")
    if g("stack_ratio") >= 0.5: t.append("stacky")
    if (g("wide_ratio") >= 0.6 or g("ang_mean") >= 140) and g("jump_ratio") < 0.5: t.append("flowy")
    if f.get("ang_mean") is not None and f["ang_mean"] < 45: t.append("snappy")
    if g("slider_ratio") >= 0.67: t.append("slider-heavy")
    if f["slider_ratio"] == 0 and n >= 3: t.append("circles-only")
    if g("triplet_ratio") >= 0.4: t.append("triplets")
    if g("gap_mean") >= 1.25: t.append("slow-rhythm")
    if g("regularity") >= 0.75 and n >= 6: t.append("repetitive")
    if f.get("regularity") is not None and g("regularity") <= 0.35 and n >= 8: t.append("varied")
    if f.get("spacing_trend") is not None and (g("spacing_trend") >= 0.8 or g("density_trend") >= 1.0): t.append("buildup")
    if f.get("spacing_trend") is not None and (g("spacing_trend") <= -0.8 or g("density_trend") <= -1.0): t.append("release")
    if kiai: t.append("kiai")
    it = f.get("intensity")
    if it is not None:
        if it >= 0.55: t.append("intense")
        elif it <= 0.30: t.append("chill")
    return t


def tags_of(node):
    """Auto tags (computed at load) plus tags the user/Claude added with `annotate`."""
    return sorted(set(node.get("atags", [])) | set(node.get("tags", [])))


# -------------------------------------------------------------- library IO
def slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-")[:40] or "x"


def jline(o):
    return json.dumps(o, separators=(",", ":"), ensure_ascii=False)


def empty_library():
    return {"manifest": {"schema": SCHEMA, "tool": "osu-pattern-lab", "maps": [],
                         "diff_engine": None, "updated": None},
            "diffs": {}, "taste": []}


def load_library(path):
    lib = empty_library()
    if not path or not os.path.exists(path):
        return lib
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            name = info.filename
            if info.file_size > MAX_MEMBER or name.startswith("/") or ".." in name:
                raise ValueError("refusing suspicious zip member: %s" % name)
            if name == "manifest.json":
                lib["manifest"] = json.loads(z.read(name))
            elif name.startswith("diffs/") and name.endswith(".jsonl"):
                rows = [json.loads(l) for l in z.read(name).decode("utf-8").splitlines() if l.strip()]
                for r in rows:
                    if not r.get("hdr"):
                        r["atags"] = autotag(r["f"], bool(r.get("ki")))
                lib["diffs"][name[6:-6]] = rows
            elif name == "taste.jsonl":
                lib["taste"] = [json.loads(l) for l in z.read(name).decode("utf-8").splitlines() if l.strip()]
    return lib


def save_library(lib, path):
    lib["manifest"]["updated"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    lib["manifest"]["schema"] = SCHEMA
    fd, tmp = tempfile.mkstemp(suffix=".zip", dir=os.path.dirname(os.path.abspath(path)) or ".")
    os.close(fd)
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr("manifest.json", json.dumps(lib["manifest"], indent=1, ensure_ascii=False))
        for key, rows in sorted(lib["diffs"].items()):
            z.writestr("diffs/%s.jsonl" % key, "\n".join(
                jline({k: v for k, v in r.items() if k != "atags"}) for r in rows) + "\n")
        z.writestr("taste.jsonl", "\n".join(jline(r) for r in lib["taste"]) + ("\n" if lib["taste"] else ""))
    os.replace(tmp, path)


def iter_nodes(lib, levels=None):
    for key, rows in lib["diffs"].items():
        hdr = rows[0] if rows and rows[0].get("hdr") else {}
        for r in rows:
            if r.get("hdr"):
                continue
            if levels and r["lv"] not in levels:
                continue
            yield hdr, r


def find_node(lib, node_id):
    for key, rows in lib["diffs"].items():
        for r in rows:
            if r.get("id") == node_id:
                return rows[0], r, rows
    return None, None, None


def node_full(rows_by_id, node):
    """Rebuild a node's full layer: motifs have it; phrases/sections concat children."""
    if node.get("full"):
        return node["full"]
    parts = [node_full(rows_by_id, rows_by_id[c]) for c in node.get("ch") or []]
    if not parts:
        return None
    full = dict(parts[0])
    full["o"] = [o for p in parts for o in p["o"]]
    return full
