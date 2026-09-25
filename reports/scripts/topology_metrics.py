#!/usr/bin/env python3
"""Per-topology and event-level reconstruction metrics, for any number of tops.

Generalizes the 2-top comparison used in reports/plots_dp_fixed/event_metrics.csv
to an arbitrary number of tops per topology, so the same code scores the 2t and
4t programs identically.

Conventions (established during the 2t campaign, see reports/):
  * prediction h5 daughter indices are GLOBAL combined-sequence indices, truth
    indices are per-collection, so boosted daughters are shifted back by the
    number of small-jet slots;
  * within a top, unordered daughter pairs (q1,q2) may swap;
  * top slots inside a topology are labels, not identities, so a model that
    finds the right tops in a different slot order is fully correct. Reported
    numbers are therefore SLOT-ORDER-FREE. Strict-slot numbers are printed
    alongside purely as a diagnostic of how much slot ordering costs; note that
    SPANet's own validation metric is NOT strict-slot, it maxes over the event
    permutation group, so it is conceptually closer to the slot-free column.
    At 4 tops the strict column collapses (ordering 4 slots right is 1/24 by
    chance), which is why it must never be quoted as a performance number.

Usage: topology_metrics.py truth.h5 label=pred.h5 [label=pred.h5 ...]
"""
import itertools
import re
import sys

import numpy as np
import h5py


def tgrp(h):
    return h["TARGETS"] if "TARGETS" in h else h["SpecialKey.Targets"]


def discover(truth, pred):
    """Topology groups and their daughters, from the particles both files share."""
    common = set(tgrp(truth).keys()) & set(tgrp(pred).keys())
    groups = {}
    for name in sorted(common):
        m = re.match(r"^([A-Za-z]+?)t(\d+)$", name)
        if not m:
            continue
        topo, idx = m.group(1), int(m.group(2))
        daus = [k for k in tgrp(truth)[name].keys()
                if k.lower() not in ("mask", "pt") and not k.endswith("probability")]
        groups.setdefault(topo, []).append((idx, name, sorted(daus)))
    for topo in groups:
        groups[topo].sort()
    return groups


def unordered_pairs(daus):
    """q1/q2 style daughters are interchangeable within a top."""
    return [(a, b) for a in daus for b in daus
            if a < b and re.sub(r"\d+$", "", a) == re.sub(r"\d+$", "", b)]


def load(truth, pred, name, daus, n_jets, boosted_daus):
    t = {d: np.asarray(tgrp(truth)[name][d]) for d in daus}
    p = {d: np.asarray(tgrp(pred)[name][d]) - (n_jets if d in boosted_daus else 0)
         for d in daus}
    valid = np.all([t[d] >= 0 for d in daus], axis=0)
    return t, p, valid


def match(t, p, daus, pairs):
    ok = np.all([t[d] == p[d] for d in daus], axis=0)
    for a, b in pairs:
        swapped = (t[a] == p[b]) & (t[b] == p[a])
        rest = np.ones(len(ok), bool)
        for d in daus:
            if d not in (a, b):
                rest &= (t[d] == p[d])
        ok = ok | (swapped & rest)
    return ok


def score(truth_path, pred_path):
    with h5py.File(truth_path, "r") as T, h5py.File(pred_path, "r") as P:
        n_jets = T["INPUTS"]["Jets"]["MASK"].shape[1]
        groups = discover(T, P)
        # daughters drawn from a boosted collection need the index shift
        boosted = set()
        for topo, items in groups.items():
            for _, name, daus in items:
                for d in daus:
                    if d in ("qq", "bqq", "bq"):
                        boosted.add(d)

        out = {}
        for topo, items in groups.items():
            slots = []
            for _, name, daus in items:
                t, p, valid = load(T, P, name, daus, n_jets, boosted)
                slots.append((t, p, valid, daus, unordered_pairs(daus)))
            n_ev = len(slots[0][2])
            n_slots = len(slots)

            # strict slot: predicted slot i must reproduce truth slot i
            strict_ok = np.concatenate(
                [match(t, p, d, pr)[v] for (t, p, v, d, pr) in slots])
            # slot-order-free: a true top counts as found if ANY predicted slot
            # of this topology reproduces it
            found = []
            for i, (t, p_i, v, d, pr) in enumerate(slots):
                any_slot = np.zeros(n_ev, bool)
                for (_, p_j, _, _, _) in slots:
                    any_slot |= match(t, p_j, d, pr)
                found.append(any_slot[v])
            found = np.concatenate(found)

            # event-level: every present top of this topology correct under SOME
            # assignment of predicted slots to truth slots
            grp_ok = np.zeros(n_ev, bool)
            for perm in itertools.permutations(range(n_slots)):
                ok = np.ones(n_ev, bool)
                for i, j in enumerate(perm):
                    t, _, v, d, pr = slots[i]
                    _, p_j, _, _, _ = slots[j]
                    ok &= match(t, p_j, d, pr) | ~v
                grp_ok |= ok
            any_valid = np.any([s[2] for s in slots], axis=0)
            out[topo] = dict(
                n_true=int(sum(s[2].sum() for s in slots)),
                slotfree=100 * found.mean() if len(found) else float("nan"),
                strict=100 * strict_ok.mean() if len(strict_ok) else float("nan"),
                grp_ok=grp_ok, any_valid=any_valid,
            )

        has_any = np.any([v["any_valid"] for v in out.values()], axis=0)
        all_ok = np.all([v["grp_ok"] for v in out.values()], axis=0) & has_any
        out["_event"] = dict(purity=100 * all_ok.sum() / max(has_any.sum(), 1),
                             n_events=int(has_any.sum()))
        return out


def main():
    truth = sys.argv[1]
    preds = [a.split("=", 1) for a in sys.argv[2:]]
    results = {lab: score(truth, path) for lab, path in preds}
    topos = [t for t in next(iter(results.values())) if t != "_event"]

    print(f"\ntruth: {truth}")
    print(f"{'model':22}" + "".join(f"{t + ' (free/strict)':>24}" for t in topos)
          + f"{'event purity':>14}")
    for lab, r in results.items():
        row = "".join(f"{r[t]['slotfree']:>12.1f}/{r[t]['strict']:<11.1f}" for t in topos)
        print(f"{lab:22}{row}{r['_event']['purity']:>14.2f}")
    first = next(iter(results.values()))
    print(f"\ntrue tops per topology: "
          + ", ".join(f"{t}={first[t]['n_true']:,}" for t in topos)
          + f"  |  events with >=1 target: {first['_event']['n_events']:,}")


if __name__ == "__main__":
    main()
