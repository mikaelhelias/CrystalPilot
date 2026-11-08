"""Frame (batch) rejection from delta-CC1/2.

delta-CC1/2 of a batch is CC1/2 without it minus CC1/2 with it (Assmann et al.,
2016); a batch with delta-CC1/2 < 0 lowers CC1/2.  Programs: XDSCC12, DIALS
(dials.compute_delta_cchalf).

Input `data`:
    {"frames": [{"batch": int, "delta_only": float}, ...] in batch order,
     "summary": {"median_delta_only": float, "mad_delta_only": float} (optional),
     "frames_per_batch": int (optional, default 1)}

Two rules share one search:
- `suggest`: ranges a user reviews, capped at 20 % of the batches by default.
- `automatic`: what a program may exclude unreviewed in one pass: only ranges
  with mean delta-CC1/2 < 0, at most 10 % of the batches; a range larger than
  what is left of the 10 % gives its worst part (>= 3 consecutive batches) when
  that part is still below 0.  Diederichs recommends excluding no more than
  about 10 % per iteration.
"""
import math

SUGGEST_LIMIT = 0.20
AUTO_LIMIT = 0.10
AUTO_MIN_PART = 3
REASON_LABELS = {"radiation_damage": "damage tail", "negative_block": "negative block", "isolated_bad": "outliers"}


def _sum(values):
    total = 0
    for value in values:
        total = total + value
    return total


def suggest(data, strategies=None, limit=SUGGEST_LIMIT):
    """Bad batch ranges.

    The search adapts to how much of the data is damaged.  With under 30 % of the
    batches negative, median - MAD outliers work.  From 30 % on the median itself
    is near zero or negative, so delta-CC1/2 < 0 is the threshold and the worst
    contiguous negative blocks and the damaged tail are found instead.

    strategies (all on by default): radtail (damage tail at the end), negblock
    (negative blocks, only from 30 % negative), outlier2 (median - 2 MAD),
    outlier3 (median - 3 MAD pairs).

    Returns {"ranges": kept, "left_out": over the limit, "diagnostics": {...},
    "median", "mad"}; each range {"start", "end", "count", "avg_delta", "reason"},
    count and mean read from the batches inside it, each counted once.
    """
    strategies = strategies or {}

    def use(key):
        return strategies.get(key, True) is not False

    summary = data.get("summary") or {}
    frames = data.get("frames") or []
    count = len(frames)
    diagnostics = {"hasRadDamage": False, "radDamageOnsetIdx": None, "radDamageOnsetBatch": None}
    if not count:
        return {"ranges": [], "left_out": [], "diagnostics": diagnostics, "median": None, "mad": None}
    deltas = [f["delta_only"] for f in frames]
    negative_pct = len([v for v in deltas if v < 0]) / count * 100
    median, mad = summary.get("median_delta_only"), summary.get("mad_delta_only")
    if median is None or mad is None:
        ordered = sorted(deltas)
        median = ordered[len(ordered) // 2]
        deviations = sorted(abs(v - median) for v in ordered)
        mad = deviations[len(deviations) // 2]
        if mad < 0.01:
            mad = 0.01
    ranges, used = [], set()

    # A: damage tail.  Walking back from the end, the tail starts after the first
    # sliding window that averages >= 0; it counts at >= 10 batches and >= 5 % of the
    # data, when its second half is worse than its first or both are clearly negative.
    if use("radtail"):
        window = max(3, min(7, int(math.floor(count * 0.02))))
        onset = count
        for start in range(count - window, -1, -1):
            if _sum(deltas[start:start + window]) / window >= 0:
                onset = start + 1
                break
            if start == 0:
                onset = 0
        length = count - onset
        if length >= 10 and length >= int(math.floor(count * 0.05)):
            half = length // 2
            first_half = deltas[onset:onset + half]
            second_half = deltas[onset + half:]
            avg_first = _sum(first_half) / len(first_half)
            avg_second = _sum(second_half) / len(second_half)
            if avg_second < avg_first or (avg_first < -0.5 and avg_second < -0.5):
                diagnostics.update({"hasRadDamage": True, "radDamageOnsetIdx": onset,
                                    "radDamageOnsetBatch": frames[onset]["batch"]})
                ranges.append({"start": frames[onset]["batch"], "end": frames[count - 1]["batch"], "count": length,
                               "avg_delta": _sum(deltas[onset:]) / length, "reason": "radiation_damage"})
                used.update(range(onset, count))

    def finish(run):
        run["avg_delta"] = run["_sum"] / run["count"]
        ranges.append(run)

    def runs_below(threshold, minimum, reason, mark):
        """Contiguous runs under a threshold; mark: they count as used for later strategies."""
        run = None
        for i in range(count):
            if i in used:
                if run and run["count"] >= minimum:
                    finish(run)
                run = None
                continue
            if deltas[i] < threshold:
                if not run:
                    run = {"start": frames[i]["batch"], "end": frames[i]["batch"], "_sum": 0, "count": 0,
                           "_first": i, "reason": reason}
                run["end"] = frames[i]["batch"]
                run["_sum"] = run["_sum"] + deltas[i]
                run["count"] += 1
            else:
                if run and run["count"] >= minimum:
                    finish(run)
                    if mark:
                        used.update(range(run["_first"], run["_first"] + run["count"]))
                run = None
        if run and run["count"] >= minimum:
            finish(run)

    # B: contiguous negative blocks, when the median can no longer be trusted
    if use("negblock") and negative_pct >= 30:
        runs_below(0, 3, "negative_block", True)
    # C: statistical outliers (median - 2 MAD); stricter when B already ran
    if use("outlier2"):
        runs_below(median - 2 * mad, 5 if negative_pct >= 30 else 3, "isolated_bad", True)
    # D: severe outlier pairs (median - 3 MAD)
    if use("outlier3"):
        runs_below(median - 3 * mad, 2, "isolated_bad", False)

    merged = []
    for item in sorted(ranges, key=lambda r: r["start"]):
        if merged and item["start"] <= merged[-1]["end"] + 2:
            previous = merged[-1]
            previous["end"] = max(previous["end"], item["end"])
            if item["reason"] == "radiation_damage":
                previous["reason"] = "radiation_damage"
        else:
            merged.append({k: item[k] for k in ("start", "end", "reason")})
    # Strategies overlap, and a merged range also takes the batches in its small
    # gaps: what a range holds is read from the batches, each counted once.
    for item in merged:
        inside = [delta for frame, delta in zip(frames, deltas) if item["start"] <= frame["batch"] <= item["end"]]
        item["count"] = len(inside)
        item["avg_delta"] = _sum(inside) / len(inside)
    allowed = int(math.floor(count * limit))
    kept, left_out, excluded = [], [], 0
    for item in sorted(merged, key=lambda r: r["avg_delta"]):
        if excluded + item["count"] <= allowed:
            kept.append(item)
            excluded += item["count"]
        else:
            left_out.append(item)
    return {"ranges": sorted(kept, key=lambda r: r["start"]), "left_out": sorted(left_out, key=lambda r: r["start"]),
            "diagnostics": diagnostics, "median": median, "mad": mad}


def worst_part(frames, item, size):
    """The run of `size` consecutive batches inside a range with the lowest mean
    delta-CC1/2, and the parts of the range on either side of it."""
    inside = [f for f in frames if item["start"] <= f["batch"] <= item["end"]]
    best = None
    for i in range(len(inside) - size + 1):
        mean = sum(f["delta_only"] for f in inside[i:i + size]) / size
        if best is None or mean < best[1]:
            best = (i, mean)
    i, mean = best
    part = {"start": inside[i]["batch"], "end": inside[i + size - 1]["batch"], "count": size, "avg_delta": mean,
            "reason": item["reason"], "part_of": (item["start"], item["end"])}
    rest = []
    for piece in (inside[:i], inside[i + size:]):
        if piece:
            rest.append({"start": piece[0]["batch"], "end": piece[-1]["batch"], "count": len(piece),
                         "avg_delta": sum(f["delta_only"] for f in piece) / len(piece), "reason": item["reason"]})
    return part, rest


def automatic(data, oscillation):
    """What may be excluded without review, in one pass.

    Returns {"exclude": [...], "left_out": [...], "record": {...}}; each range as
    image numbers {"first", "last", "reason", "batches"[, "part_of"]}, with a batch
    of several images starting at its first image.  `oscillation` (degrees per
    image) gives the rotation excluded in the record.
    """
    frames = data.get("frames") or []
    width = data.get("frames_per_batch") or 1
    found = suggest(data, limit=AUTO_LIMIT)
    median, mad = found["median"], found["mad"]
    uniform = mad is None or mad <= 0.001          # nothing stands out from identical values
    ranges = [] if uniform else [r for r in found["ranges"] if r["avg_delta"] < 0]
    over = [] if uniform else [r for r in found["left_out"] if r["avg_delta"] < 0]
    not_negative = 0 if uniform else sum(r["count"] for r in found["ranges"] + found["left_out"] if r["avg_delta"] >= 0)
    budget = int(math.floor(len(frames) * AUTO_LIMIT)) - sum(r["count"] for r in ranges)
    left_out = []
    for item in sorted(over, key=lambda r: r["avg_delta"]):
        size = min(budget, item["count"])
        if size >= AUTO_MIN_PART:
            part, rest = worst_part(frames, item, size)
            if part["avg_delta"] < 0:
                ranges.append(part)
                budget -= size
                left_out.extend(r for r in rest if r["avg_delta"] < 0)
                continue
        left_out.append(item)
    ranges.sort(key=lambda r: r["start"])
    left_out.sort(key=lambda r: r["start"])
    batches = sum(r["count"] for r in ranges)
    reasons = []
    for item in ranges:
        if REASON_LABELS[item["reason"]] not in reasons:
            reasons.append(REASON_LABELS[item["reason"]])
    record = {"threshold": " + ".join(reasons) or "no range found",
              "threshold_value": None if median is None or mad is None else round(median - 2 * mad, 3),
              "median": None if median is None else round(median, 3), "mad": None if mad is None else round(mad, 4),
              "n_excluded": batches, "degrees_excluded": round(batches * width * oscillation, 1),
              "n_total": len(frames), "column": "only", "limit_pct": int(AUTO_LIMIT * 100),
              "left_out": sum(r["count"] for r in left_out), "not_negative": not_negative,
              "trimmed": len([r for r in ranges if r.get("part_of")])}

    def first_frame(batch):
        return max(1, batch - width + 1)

    def frame_range(item):
        chosen = {"first": first_frame(item["start"]), "last": item["end"],
                  "reason": "dcc_half=" + str(round(item["avg_delta"], 2)), "batches": item["count"]}
        if item.get("part_of"):
            chosen["part_of"] = [first_frame(item["part_of"][0]), item["part_of"][1]]
        return chosen

    return {"exclude": [frame_range(r) for r in ranges], "left_out": [frame_range(r) for r in left_out],
            "record": record}
