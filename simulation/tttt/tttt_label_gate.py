#!/usr/bin/env python3
"""tttt pilot label-validation gate (the lessons of the v6 forensic, applied
BEFORE any GPU time):
  1. structural census: within-particle dup daughters, masked/oob slots
  2. double-booking profile: FRti.b == SRqqtj.b (same-top double description)
     -- the decoder-eviction driver
  3. physics of the labels: m(b,q1,q2), m(q1,q2), m(b+fj_qq), FB sdmass
  4. composition + per-event labeled-top counts
"""
import argparse

import numpy as np
import h5py
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ap = argparse.ArgumentParser(
    description="Validate the label physics of a converted multi-top h5.",
    epilog="Example: python tttt_label_gate.py "
           "-f /data/spatop/tttt_15M/h5/tttt_training.h5 -o /data/spatop/plots/tttt_15M_labels.png")
ap.add_argument("-f", "--file", default="/data/spatop/tttt_pilot/h5/tttt_training.h5",
                help="converted h5 to check (default: the tttt pilot)")
ap.add_argument("-n", "--n-tops", type=int, default=4,
                help="tops per event: 2 for ttbar, 4 for tttt, 6 for six-top")
ap.add_argument("-o", "--out", default="/data/spatop/plots_dp_fixed/tttt_pilot_labels.png",
                help="output figure path")
ap.add_argument("-l", "--label", default=None,
                help="name used in the figure title (default: derived from --file)")
args = ap.parse_args()

PATH = args.file
NT = args.n_tops
LABEL = args.label or PATH.split("/")[-3] if PATH.count("/") >= 3 else PATH
with h5py.File(PATH, "r") as h:
    jm = np.asarray(h["INPUTS/Jets/MASK"]); n, njet = jm.shape
    fjm = np.asarray(h["INPUTS/BoostedJets/MASK"]); nfj = fjm.shape[1]
    print(f"{PATH}: {n:,} events, {njet} jet slots, {nfj} fj slots")
    jpt = np.asarray(h["INPUTS/Jets/pt"]); jeta = np.asarray(h["INPUTS/Jets/eta"])
    jphi = np.arctan2(np.asarray(h["INPUTS/Jets/sinphi"]), np.asarray(h["INPUTS/Jets/cosphi"]))
    jmass = np.asarray(h["INPUTS/Jets/mass"])
    fpt = np.asarray(h["INPUTS/BoostedJets/fj_pt"]); feta = np.asarray(h["INPUTS/BoostedJets/fj_eta"])
    fphi = np.arctan2(np.asarray(h["INPUTS/BoostedJets/fj_sinphi"]), np.asarray(h["INPUTS/BoostedJets/fj_cosphi"]))
    fmass = np.asarray(h["INPUTS/BoostedJets/fj_mass"]); fsd = np.asarray(h["INPUTS/BoostedJets/fj_sdmass"])
    T = {f"{topo}t{i}": {d: np.asarray(h[f"TARGETS/{topo}t{i}/{d}"]) for d in daus}
         for topo, daus in [("FR", ["b","q1","q2"]), ("SRqq", ["b","qq"]), ("FB", ["bqq"])]
         for i in range(1, NT+1)}

# 1. structural census
bad_dup = np.zeros(n, bool); bad_slot = np.zeros(n, bool)
for p, td in T.items():
    # duplicates are only meaningful WITHIN one index space (collection)
    for coll, sel in (("J", lambda d: d not in ("qq", "bqq")),
                      ("B", lambda d: d in ("qq", "bqq"))):
        daus = [d for d in td if sel(d)]
        if len(daus) < 2:
            continue
        idxs = np.stack([td[d] for d in daus], 1)
        valid = idxs >= 0
        s = np.sort(np.where(valid, idxs, -np.arange(1, idxs.shape[1]+1)[None,:]), 1)
        bad_dup |= ((s[:,1:] == s[:,:-1]) & (s[:,1:] >= 0)).any(1)
    daus = list(td)
    idxs = np.stack([td[d] for d in daus], 1)
    for k, d in enumerate(daus):
        mm = fjm if d in ("qq","bqq") else jm
        v = idxs[:,k]; ok = v >= 0
        oob = ok & (v >= mm.shape[1])
        pad = ok & ~oob & ~mm[np.arange(n), np.clip(v, 0, mm.shape[1]-1)]
        bad_slot |= (oob | pad)
print(f"1. STRUCTURAL: dup-daughter events {bad_dup.sum()}  masked/oob {bad_slot.sum()}  "
      f"({'PASS' if (bad_dup|bad_slot).sum()==0 else 'FAIL'})")

# 2. double-booking profile
n_srqq = 0; n_contested = 0
for i in range(1, NT+1):
    sb = T[f"SRqqt{i}"]["b"]; sq = T[f"SRqqt{i}"]["qq"]
    v = (sb >= 0) & (sq >= 0)
    n_srqq += v.sum()
    fr_bs = np.stack([T[f"FRt{j}"]["b"] for j in range(1, NT+1)])
    n_contested += (v & (fr_bs == sb[None,:]).any(0)).sum()
print(f"2. DOUBLE-BOOKING: SRqq targets {n_srqq:,}; b shared with an FR target: "
      f"{n_contested:,} ({100*n_contested/max(n_srqq,1):.1f}%)  "
      f"[v6 was 100%, fixed-tt 36%]")

# composition
for topo in ("FR", "SRqq", "FB"):
    pres = np.zeros(n, int)
    for i in range(1, NT+1):
        td = T[f"{topo}t{i}"]
        pres += np.all([td[d] >= 0 for d in td], 0).astype(int)
    print(f"   {topo}: events w/ >=1: {100*(pres>0).mean():.1f}%  tops total {pres.sum():,}  "
          f"max/event {pres.max()}")

# 3. physics of the labels
def four(pt, eta, phi, m):
    return (pt*np.cos(phi), pt*np.sin(phi), pt*np.sinh(eta),
            np.sqrt((pt*np.cosh(eta))**2 + m**2))
def madd(*ps):
    s = [sum(p[k] for p in ps) for k in range(4)]
    return np.sqrt(np.clip(s[3]**2 - s[0]**2 - s[1]**2 - s[2]**2, 0, None))

frm, wm, srm, fbm = [], [], [], []
for i in range(1, NT+1):
    td = T[f"FRt{i}"]
    v = (td["b"]>=0)&(td["q1"]>=0)&(td["q2"]>=0)
    ev = np.where(v)[0]
    pb = four(jpt[ev,td["b"][ev]], jeta[ev,td["b"][ev]], jphi[ev,td["b"][ev]], jmass[ev,td["b"][ev]])
    p1 = four(jpt[ev,td["q1"][ev]], jeta[ev,td["q1"][ev]], jphi[ev,td["q1"][ev]], jmass[ev,td["q1"][ev]])
    p2 = four(jpt[ev,td["q2"][ev]], jeta[ev,td["q2"][ev]], jphi[ev,td["q2"][ev]], jmass[ev,td["q2"][ev]])
    frm.append(madd(pb,p1,p2)); wm.append(madd(p1,p2))
    sd = T[f"SRqqt{i}"]
    v = (sd["b"]>=0)&(sd["qq"]>=0)
    ev = np.where(v)[0]
    pb = four(jpt[ev,sd["b"][ev]], jeta[ev,sd["b"][ev]], jphi[ev,sd["b"][ev]], jmass[ev,sd["b"][ev]])
    pf = four(fpt[ev,sd["qq"][ev]], feta[ev,sd["qq"][ev]], fphi[ev,sd["qq"][ev]], fmass[ev,sd["qq"][ev]])
    srm.append(madd(pb,pf))
    fd = T[f"FBt{i}"]
    v = fd["bqq"] >= 0
    ev = np.where(v)[0]
    fbm.append(fsd[ev, fd["bqq"][ev]])
frm, wm, srm, fbm = map(np.concatenate, (frm, wm, srm, fbm))
def w_in(x, lo, hi): return 100*((x>=lo)&(x<hi)).mean()
print(f"3. PHYSICS: FR m(bqq) top-window {w_in(frm,123,223):.1f}%  "
      f"FR m(q1q2) W-window {w_in(wm,50,110):.1f}%  "
      f"SRqq m(b+fj) top-window {w_in(srm,123,223):.1f}%  "
      f"FB sdmass 120-250 {w_in(fbm,120,250):.1f}%")
print(f"   [fixed-ttbar references: 86.8 / 80.8 / 83.9 / 83.7]")
print(f"   [tttt 15M measured:      94.3 / 100.0 / 83.9 / 85.4]")

fig, ax = plt.subplots(2, 2, figsize=(11, 7.5))
for a, (x, b, t, l) in zip(ax.ravel(), [
        (frm, np.linspace(0,400,81), "tttt FR labels: m(b,q1,q2)", 172.8),
        (wm, np.linspace(0,300,76), "tttt FR labels: m(q1,q2)", 80.4),
        (srm, np.linspace(0,400,81), "tttt SRqq labels: m(b + fj)", 172.8),
        (fbm, np.linspace(0,300,76), "tttt FB labels: fj sdmass", 172.8)]):
    a.hist(x, bins=b, histtype="step", lw=1.6, color="#1f4e9c")
    a.axvline(l, color="gray", ls=":", lw=1)
    a.set_title(t, fontsize=10)
fig.suptitle(f"{LABEL} label physics ({n:,} events, group pipeline, --n-tops {NT})")
fig.tight_layout()
fig.savefig(args.out, dpi=140)
print(f"figure: {args.out}")
print("GATE DONE")
