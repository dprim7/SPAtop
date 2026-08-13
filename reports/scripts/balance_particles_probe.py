#!/usr/bin/env python3
"""Replicate SPANet's compute_particle_balance() exactly on our data and report
the weights it actually assigns. Mirrors
spanet/dataset/jet_reconstruction_dataset.py:344-384."""
import itertools, sys
import numpy as np, h5py

PATH = sys.argv[1] if len(sys.argv) > 1 else "data/delphes/tt_hadronic_testing_fixed.h5"
PARTS = ["FRt1", "FRt2", "SRqqt1", "SRqqt2", "FBt1", "FBt2"]

with h5py.File(PATH) as f:
    tg = f["TARGETS"]
    masks = []
    for p in PARTS:
        g = tg[p]
        key = "MASK" if "MASK" in g else "mask"
        masks.append(np.asarray(g[key]).astype(bool))
masks = np.stack(masks)                       # (6, n_events)
n_targets, n_events = masks.shape
print(f"{PATH}\n{n_events:,} events, {n_targets} targets\n")

# event permutation group: FRt1<->FRt2, SRqq1<->SRqq2, FBt1<->FBt2  => 8 elements
def perms():
    for a in (0, 1):
        for b in (0, 1):
            for c in (0, 1):
                m = {}
                m[0], m[1] = (1, 0) if a else (0, 1)
                m[2], m[3] = (3, 2) if b else (2, 3)
                m[4], m[5] = (5, 4) if c else (4, 5)
                yield m
GROUP = list(perms())

def power_set(n):
    for r in range(n + 1):
        for s in itertools.combinations(range(n), r):
            yield frozenset(s)

eq_classes = set()
for s in power_set(n_targets):
    eq_classes.add(frozenset(frozenset(g[x] for x in s) for g in GROUP))

full = frozenset(range(n_targets))
counts = {}
for eq in eq_classes:
    c = 0
    for pos in eq:
        neg = full - pos
        p = masks[list(pos), :].all(0) if pos else np.ones(n_events, bool)
        ng = masks[list(neg), :].any(0) if neg else np.zeros(n_events, bool)
        c += int((p & ~ng).sum())
    counts[eq] = c + 1                        # the +1 in the source

beta = 1 - 10 ** (-np.log10(n_events))
w = {k: (1 - beta) / (1 - beta ** v) for k, v in counts.items()}
norm = sum(w.values())
wn = {k: len(w) * v / norm for k, v in w.items()}

def label(eq):
    rep = sorted(eq, key=lambda s: sorted(s))[0]
    nfr = len({0, 1} & set(rep)); nsr = len({2, 3} & set(rep)); nfb = len({4, 5} & set(rep))
    return f"{nfr}FR {nsr}SR {nfb}FB"

rows = sorted(((label(k), counts[k] - 1, wn[k]) for k in eq_classes), key=lambda r: -r[1])
print(f"{'class':>12} {'events':>10} {'weight':>12}   {'share of loss':>14}")
tot_w = sum((c) * w_ for _, c, w_ in rows)
for lab, c, w_ in rows:
    if c == 0 and w_ < 1e-3:
        continue
    share = 100 * c * w_ / tot_w if tot_w else 0
    print(f"{lab:>12} {c:>10,} {w_:>12.4f}   {share:>13.2f}%")

nz = [w_ for _, c, w_ in rows if c > 0]
print(f"\nweight spread over POPULATED classes: min {min(nz):.5f}  max {max(nz):.4f} "
      f"=> ratio {max(nz)/min(nz):,.0f}x")
empty = [(lab, w_) for lab, c, w_ in rows if c == 0]
print(f"classes with ZERO events but non-zero weight: {len(empty)} "
      f"(max weight {max((w for _, w in empty), default=0):.4f})")
print(f"mean per-event weight = {tot_w/n_events:.4f}  (unweighted would be 1.0)")
