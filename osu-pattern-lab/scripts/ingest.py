#!/usr/bin/env python3
"""Ingest .osu / .osz files into a pattern library zip (create or extend).

usage: python3 -I ingest.py INPUT [INPUT ...] --zip OUT.zip [--base EXISTING.zip] [--force]

INPUT may be a .osu, an .osz (only .osu members are read; audio is never touched),
or a folder of .osu files. Prints one JSON summary to stdout.
"""
import argparse
import datetime
import glob
import json
import math
import os
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import osu_lib as L  # noqa: E402

REST_FLOOR = 2.0          # a gap must be at least this long (beats) to count as a rest...
REST_REL = 2.5            # ...and at least this many times the map's median gap (easy diffs live at 2 beats/object)
SECTION_REST_FLOOR = 4.0
MIN_MOTIF = 3             # motifs smaller than this merge forward (crossing a measure line only for these)
MAX_MERGED_MOTIF = 10
MAX_PHRASE_MEASURES = 4
MAX_SECTION_BEATS = 64


# ---------------------------------------------------------------- difficulty
def load_engine():
    try:
        import rosu_pp_py as rp
        from importlib.metadata import version
        return rp, version("rosu-pp-py")
    except Exception:
        return None, None


def map_difficulty(rp, raw):
    """Whole-map stars + per-400ms aim/speed strain from the official-algorithm port."""
    if rp is None:
        return None
    fd, tmp = tempfile.mkstemp(suffix=".osu")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(raw)
        bm = rp.Beatmap(path=tmp)
        d = rp.Difficulty()
        a = d.calculate(bm)
        s = d.strains(bm)
        return {"stars": round(a.stars, 3), "aim": round(a.aim, 3), "speed": round(a.speed, 3),
                "L": s.section_length, "sa": list(s.aim), "ss": list(s.speed)}
    except Exception as e:  # keep ingesting without difficulty rather than fail the map
        return {"error": str(e)[:120]}
    finally:
        os.unlink(tmp)


def local_diff(dif, t0, t1, t_first):
    """Mean aim/speed strain over the sections a pattern spans, plus its share of the map's peak."""
    if not dif or "sa" not in dif:
        return {}
    Ls, sa, ss = dif["L"], dif["sa"], dif["ss"]
    k0 = math.ceil(t_first / Ls)
    lo = max(0, min(len(sa) - 1, math.ceil(t0 / Ls) - k0))
    hi = max(lo, min(len(sa) - 1, math.ceil(t1 / Ls) - k0))
    comb = [sa[i] + ss[i] for i in range(len(sa))]
    peak = max(comb) or 1.0
    win = range(lo, hi + 1)
    return {"aim": round(sum(sa[i] for i in win) / len(win), 2),
            "speed": round(sum(ss[i] for i in win) / len(win), 2),
            "rel": round(sum(comb[i] for i in win) / len(win) / peak, 3)}


# ------------------------------------------------------------------- chopping
def gap_beats(objs, i):
    return (objs[i + 1]["t"] - objs[i]["t"]) / objs[i]["bl"]


def rest_beats(objs, i, j):
    """Silence between object i finishing and object j starting, in beats."""
    return (objs[j]["t"] - objs[i]["te"]) / objs[i]["bl"]


def split_measure(objs, a, b, rest):
    """Cut one measure's objects a..b into motifs: rhythm-class change, rests, long combos."""
    if a == b:
        return [(a, a)]
    gaps = [gap_beats(objs, i) for i in range(a, b)]
    q = [L.quantize_gap(g)[0] for g in gaps]
    cuts, start = [], 0
    for k in range(len(gaps)):
        cut = gaps[k] >= rest
        if not cut and k > 0 and q[k - 1] > 0 and q[k] > 0:
            r = q[k] / q[k - 1]
            cut = r >= 1.9 or r <= 0.53
        if not cut and k + 1 <= len(gaps) and objs[a + k + 1]["nc"] and (k - start + 1) >= 4:
            cut = True
        if cut and a + k < b:
            cuts.append(a + k)
            start = k + 1
    out, s = [], a
    for c in cuts:
        out.append((s, c))
        s = c + 1
    out.append((s, b))
    # fold lone objects into a neighbour when the gap is short
    merged = []
    for m in out:
        if m[0] == m[1] and merged and gap_beats(objs, merged[-1][1]) < rest:
            merged[-1] = (merged[-1][0], m[1])
        else:
            merged.append(m)
    if len(merged) > 1 and merged[0][0] == merged[0][1] and gap_beats(objs, merged[0][1]) < rest:
        merged[1] = (merged[0][0], merged[1][1])
        merged.pop(0)
    return merged


def merge_small(objs, motifs, rest):
    """Undersized motifs (sparse diffs: 1-2 objects per measure) join the next one if no rest separates them."""
    out, i = [], 0
    while i < len(motifs):
        cur = motifs[i]
        i += 1
        while cur[1] - cur[0] + 1 < MIN_MOTIF and i < len(motifs):
            nxt = motifs[i]
            if rest_beats(objs, cur[1], nxt[0]) >= rest or nxt[1] - cur[0] + 1 > MAX_MERGED_MOTIF:
                break
            cur = (cur[0], nxt[1])
            i += 1
        out.append(cur)
    if len(out) > 1 and out[-1][1] - out[-1][0] + 1 < MIN_MOTIF:
        prev, last = out[-2], out[-1]
        if rest_beats(objs, prev[1], last[0]) < rest and last[1] - prev[0] + 1 <= MAX_MERGED_MOTIF:
            out[-2:] = [(prev[0], last[1])]
    return out


def make_motifs(objs, rest):
    groups, cur, ck = [], [], None
    for i, o in enumerate(objs):
        # +0.02 beat tolerance: integer-ms timing puts "beat 4.000" at 3.999 in real maps
        mk = (o["red_t"], math.floor((o["bpos"] + 0.02) / o["meter"]))
        if mk != ck and cur:
            groups.append(cur)
            cur = []
        ck = mk
        cur.append(i)
    if cur:
        groups.append(cur)
    motifs = []
    for g in groups:
        motifs += split_measure(objs, g[0], g[-1], rest)
    return merge_small(objs, motifs, rest)


def group_ranges(items, objs, breaks):
    """Generic grouping of consecutive items; `breaks(cur_items, nxt)` -> bool."""
    out, cur = [], []
    for it in items:
        if cur and breaks(cur, it):
            out.append(cur)
            cur = []
        cur.append(it)
    if cur:
        out.append(cur)
    return out


# ------------------------------------------------------------------- ingest
def ingest_map(raw, rp, rp_ver, source_name):
    pm = L.parse_map(raw.decode("utf-8", "replace"))
    objs = pm["objects"]
    if len(objs) < 4:
        raise ValueError("fewer than 4 hit objects")
    sha = L.map_hash(raw)
    h8 = sha[:8]
    meta = pm["meta"]
    dif = map_difficulty(rp, raw)
    t_first = objs[0]["t"]

    def build(i0, i1, lv):
        sub = objs[i0:i1 + 1]
        link = None
        if i0 > 0:
            p = objs[i0 - 1]
            link = [L._r((objs[i0]["t"] - p["t"]) / p["bl"], 3),
                    int(round(math.hypot(objs[i0]["x"] - p["ex"], objs[i0]["y"] - p["ey"])))]
        full = L.make_full(sub, pm["diff"], link)
        ab, mv, an, f = L.derive(full)
        f.update(local_diff(dif, sub[0]["t"], sub[-1]["te"], t_first))
        if dif and "stars" in dif:
            f["stars"] = dif["stars"]
        L.add_intensity(f)
        kiai = all(o["kiai"] for o in sub)
        return full, ab, mv, an, f, kiai

    gs = sorted(gap_beats(objs, i) for i in range(len(objs) - 1) if gap_beats(objs, i) > 0.01)
    median_gap = gs[len(gs) // 2] if gs else 1.0
    REST = max(REST_FLOOR, REST_REL * median_gap)          # what counts as "a rest" in THIS map
    SREST = max(SECTION_REST_FLOOR, 2 * REST)
    motif_rng = make_motifs(objs, REST)
    motif_info = []
    for (i0, i1) in motif_rng:
        full, ab, mv, an, f, kiai = build(i0, i1, "m")
        motif_info.append({"r": (i0, i1), "full": full, "ab": ab, "mv": mv, "an": an, "f": f, "kiai": kiai})

    def phrase_break(cur, m):
        first, last = cur[0], cur[-1]
        if rest_beats(objs, last["r"][1], m["r"][0]) >= REST:
            return True
        a, b = objs[last["r"][1]], objs[m["r"][0]]
        if a["kiai"] != b["kiai"] or a["red_t"] != b["red_t"]:
            return True
        if (b["t"] - objs[first["r"][0]]["t"]) / a["bl"] > MAX_PHRASE_MEASURES * a["meter"]:
            return True
        gm = [x["f"]["gap_mean"] for x in cur if x["f"]["gap_mean"]]
        dm = [x["f"]["ds_mean"] for x in cur if x["f"]["ds_mean"] is not None]
        if gm and m["f"]["gap_mean"] and abs(math.log2(m["f"]["gap_mean"] / (sum(gm) / len(gm)))) > 1.0:
            return True
        if dm and m["f"]["ds_mean"] is not None and abs(m["f"]["ds_mean"] - sum(dm) / len(dm)) > 2.5:
            return True
        return False

    phrase_groups = group_ranges(motif_info, objs, phrase_break)
    phrases = []
    for g in phrase_groups:
        i0, i1 = g[0]["r"][0], g[-1]["r"][1]
        full, ab, mv, an, f, kiai = build(i0, i1, "p")
        phrases.append({"r": (i0, i1), "kids": g, "ab": ab, "f": f, "kiai": kiai})

    def section_break(cur, p):
        last = cur[-1]
        if rest_beats(objs, last["r"][1], p["r"][0]) >= SREST:
            return True
        a, b = objs[last["r"][1]], objs[p["r"][0]]
        if a["kiai"] != b["kiai"]:
            return True
        if a["red_t"] != b["red_t"] and abs(a["bl"] / b["bl"] - 1) > 0.05:
            return True
        if (b["t"] - objs[cur[0]["r"][0]]["t"]) / a["bl"] > MAX_SECTION_BEATS:
            return True
        dens = [x["f"]["density"] for x in cur if x["f"]["density"]]
        if dens and p["f"]["density"]:
            r = p["f"]["density"] / (sum(dens) / len(dens))
            if r >= 2.0 or r <= 0.5:
                return True
        return False

    sec_groups = group_ranges(phrases, objs, section_break)

    rows = []
    mid = pid = sid = 0
    motif_id = {}
    for m in motif_info:
        motif_id[m["r"]] = "%s:m:%d" % (h8, mid)
        mid += 1
    phrase_ids = {}
    for p in phrases:
        phrase_ids[p["r"]] = "%s:p:%d" % (h8, pid)
        pid += 1
    sec_rows = []
    for g in sec_groups:
        i0, i1 = g[0]["r"][0], g[-1]["r"][1]
        full, ab, mv, an, f, kiai = build(i0, i1, "s")
        sid_s = "%s:s:%d" % (h8, sid)
        sid += 1
        sec_rows.append({"id": sid_s, "lv": "s", "par": None, "ch": [phrase_ids[p["r"]] for p in g],
                         "src": {"d": h8, "r": [i0, i1], "t": [objs[i0]["t"], objs[i1]["te"]],
                                 "ts": L.editor_ts(objs, i0)},
                         "abs": {"mc": [m["ab"]["cl"] for p in g for m in p["kids"]],
                                 "rh": dict(L.Counter(t for p in g for m in p["kids"] for t in m["ab"]["r"])),
                                 "key": None, "cl": None},
                         "f": f, "tags": [], "ki": int(kiai), "desc": ""})
        for p in g:
            p["par"] = sid_s
    for p in phrases:
        ab = {"mc": [m["ab"]["cl"] for m in p["kids"]],
              "rh": dict(L.Counter(t for m in p["kids"] for t in m["ab"]["r"]))}
        ab["cl"] = L.hashlib.md5(",".join(ab["mc"]).encode()).hexdigest()[:8]
        rows.append({"id": phrase_ids[p["r"]], "lv": "p", "par": p["par"],
                     "ch": [motif_id[m["r"]] for m in p["kids"]],
                     "src": {"d": h8, "r": list(p["r"]), "t": [objs[p["r"][0]]["t"], objs[p["r"][1]]["te"]],
                             "ts": L.editor_ts(objs, p["r"][0])},
                     "abs": ab, "f": p["f"], "tags": [], "ki": int(p["kiai"]), "desc": ""})
        for m in p["kids"]:
            m["par"] = phrase_ids[p["r"]]
    for s in sec_rows:
        s["abs"]["cl"] = L.hashlib.md5(",".join(s["abs"]["mc"]).encode()).hexdigest()[:8]
    mrows = []
    for m in motif_info:
        i0, i1 = m["r"]
        mrows.append({"id": motif_id[m["r"]], "lv": "m", "par": m["par"], "ch": None,
                      "src": {"d": h8, "r": [i0, i1], "t": [objs[i0]["t"], objs[i1]["te"]],
                              "ts": L.editor_ts(objs, i0)},
                      "abs": m["ab"], "f": m["f"], "mv": m["mv"], "an": m["an"], "full": m["full"],
                      "tags": [], "ki": int(m["kiai"]), "desc": ""})
    bpms = sorted({round(60000 / o["bl"], 1) for o in objs})
    hdr = {"hdr": 1, "k": h8, "sha1": sha, "title": meta.get("Title", "?"), "artist": meta.get("Artist", "?"),
           "creator": meta.get("Creator", "?"), "version": meta.get("Version", "?"),
           "mapid": meta.get("BeatmapID", ""), "setid": meta.get("BeatmapSetID", ""),
           "bpm": bpms[:6], "cs": pm["diff"]["cs"], "ar": pm["diff"]["ar"], "od": pm["diff"]["od"],
           "sm": pm["diff"]["sm"], "n_obj": len(objs), "bad_objects": pm["bad"], "source": source_name,
           "stars": dif.get("stars") if dif else None, "aim": dif.get("aim") if dif else None,
           "speed": dif.get("speed") if dif else None,
           "engine": ("rosu-pp-py " + rp_ver) if dif and "stars" in dif else None,
           "n_motif": len(mrows), "n_phrase": len(rows), "n_section": len(sec_rows)}
    if dif and "error" in dif:
        hdr["engine_error"] = dif["error"]
    return hdr, [hdr] + mrows + rows + sec_rows


# ----------------------------------------------------------------- inputs
def read_inputs(paths):
    """Yield (name, bytes). .osz members are read in memory, only *.osu, never extracted."""
    for p in paths:
        if os.path.isdir(p):
            for f in sorted(glob.glob(os.path.join(p, "**", "*.osu"), recursive=True)):
                yield from read_inputs([f])
        elif p.lower().endswith(".osu"):
            if os.path.getsize(p) > L.MAX_OSU:
                yield os.path.basename(p), None
            else:
                yield os.path.basename(p), open(p, "rb").read()
        elif p.lower().endswith((".osz", ".zip")):
            with zipfile.ZipFile(p) as z:
                for info in z.infolist():
                    if info.filename.lower().endswith(".osu") and not info.filename.startswith("/") \
                            and ".." not in info.filename:
                        yield os.path.basename(info.filename), (z.read(info) if info.file_size <= L.MAX_OSU else None)
        else:
            yield os.path.basename(p), None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--zip", required=True, help="output library path")
    ap.add_argument("--base", help="existing library to extend (may equal --zip)")
    ap.add_argument("--force", action="store_true", help="re-ingest even if hash already present")
    a = ap.parse_args()

    lib = L.load_library(a.base if a.base else (a.zip if os.path.exists(a.zip) else None))
    rp, rp_ver = load_engine()
    man = lib["manifest"]
    old_engine = (man.get("diff_engine") or {}).get("version")
    report = {"added": [], "skipped": [], "replaced": [], "failed": [], "warnings": []}
    if rp is None:
        report["warnings"].append("rosu-pp-py not importable: stars/strain left empty. "
                                  "Run: pip install -U --break-system-packages rosu-pp-py, then re-ingest with --force.")
    seen_hashes = {m["sha1"]: m for m in man["maps"]}
    for name, raw in read_inputs(a.inputs):
        if raw is None:
            report["failed"].append({"file": name, "why": "not an .osu, or larger than 8 MB"})
            continue
        try:
            sha = L.map_hash(raw)
            if sha in seen_hashes and not a.force:
                report["skipped"].append({"file": name, "why": "already in library"})
                continue
            hdr, rows = ingest_map(raw, rp, rp_ver, name)
        except L.NotStandard as e:
            report["skipped"].append({"file": name, "why": "%s diff (this skill handles osu!standard only)" % e})
            continue
        except Exception as e:
            report["failed"].append({"file": name, "why": str(e)[:160]})
            continue
        ident = (hdr["title"], hdr["artist"], hdr["creator"], hdr["version"])
        for m in list(man["maps"]):
            if (m["title"], m["artist"], m["creator"], m["version"]) == ident or m["sha1"] == sha:
                lib["diffs"].pop(m["key"], None)
                man["maps"].remove(m)
                report["replaced"].append({"file": name, "old": m["key"]})
        key = "%s-%s-%s" % (L.slug(hdr["title"]), L.slug(hdr["version"]), hdr["k"])
        lib["diffs"][key] = rows
        man["maps"].append({"key": key, "sha1": sha, "title": hdr["title"], "artist": hdr["artist"],
                            "creator": hdr["creator"], "version": hdr["version"], "stars": hdr["stars"],
                            "engine": hdr["engine"], "n_obj": hdr["n_obj"],
                            "nodes": [hdr["n_motif"], hdr["n_phrase"], hdr["n_section"]],
                            "ingested": datetime.date.today().isoformat()})
        seen_hashes[sha] = man["maps"][-1]
        report["added"].append({"file": name, "key": key, "title": hdr["title"], "version": hdr["version"],
                                "stars": hdr["stars"], "objects": hdr["n_obj"], "bad_objects": hdr["bad_objects"],
                                "motifs": hdr["n_motif"], "phrases": hdr["n_phrase"], "sections": hdr["n_section"]})
    if rp_ver:
        man["diff_engine"] = {"name": "rosu-pp-py", "version": rp_ver}
        stale = [m["key"] for m in man["maps"] if m.get("engine") and m["engine"] != "rosu-pp-py " + rp_ver]
        if stale:
            report["warnings"].append("%d diff(s) were rated by an older difficulty engine; re-upload them "
                                      "(with --force) to refresh stars: %s" % (len(stale), ", ".join(stale[:5])))
    L.save_library(lib, a.zip)
    report["library"] = {"path": a.zip, "maps": len(man["maps"]),
                         "nodes": sum(len(r) - 1 for r in lib["diffs"].values()),
                         "engine": man.get("diff_engine")}
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
