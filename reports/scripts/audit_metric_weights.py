import numpy as np, h5py

print("========== CLAIM 5: bool vs float64 weighted_jet_accuracies ==========")
rng = np.random.default_rng(0)
n_perm, n_tgt, n_ev = 2, 6, 5
correct = rng.random((n_perm, n_tgt, n_ev)) < 0.5
for label, w in (("weights all 1.0 (our data: no WEIGHT dataset)", np.ones((n_tgt, n_ev))),
                 ("weights != 1 (only if TARGETS/<p>/WEIGHT exists)",
                  rng.uniform(0.2, 2.5, size=(n_tgt, n_ev)))):
    b = np.zeros((n_perm, n_tgt, n_ev), dtype=bool)      # vanilla fork
    f = np.zeros((n_perm, n_tgt, n_ev), dtype=np.float64) # pairwise fork (our fix)
    for i in range(n_perm):
        for j in range(n_tgt):
            b[i, j] = correct[i, j] * w[j]
            f[i, j] = correct[i, j] * w[j]
    num_b, num_f = b.sum(1).max(0), f.sum(1).max(0)
    den = (np.ones((n_tgt, n_ev)) * w).sum(0)
    print(f"  {label}")
    print(f"    vanilla(bool) metric : {np.mean(num_b/den):.6f}")
    print(f"    ours(float64) metric : {np.mean(num_f/den):.6f}")
    print(f"    identical            : {np.allclose(num_b/den, num_f/den)}")

print("\n========== CLAIM 3: tops counted in more than one category ==========")
P = "data/delphes/tt_hadronic_testing_fixed.h5"
with h5py.File(P) as h:
    tg = h["TARGETS"]
    def m(p):
        g = tg[p]; k = "MASK" if "MASK" in g else "mask"
        return np.asarray(g[k]).astype(bool)
    def b(p):
        return np.asarray(tg[p]["b"])
    parts = ["FRt1","FRt2","SRqqt1","SRqqt2","FBt1","FBt2"]
    masks = np.stack([m(p) for p in parts])
    n_ev = masks.shape[1]
    n_present = masks.sum(0)

    # a physical top described twice = an FR and an SRqq target sharing the b jet
    dup = np.zeros(n_ev, dtype=int)
    for fr in ("FRt1","FRt2"):
        for sr in ("SRqqt1","SRqqt2"):
            both = m(fr) & m(sr) & (b(fr) == b(sr)) & (b(fr) >= 0)
            dup += both
    tot_slots = int(n_present.sum())
    print(f"  events                                    : {n_ev:,}")
    print(f"  total target slots (metric denominator)   : {tot_slots:,}")
    print(f"  slots that re-describe an already-counted top: {int(dup.sum()):,} "
          f"({100*dup.sum()/tot_slots:.1f}% of all slots)")
    print(f"  events containing >=1 double-described top: {int((dup>0).sum()):,} "
          f"({100*(dup>0).mean():.1f}% of events)")
    print(f"  mean targets/event, all events            : {n_present.mean():.3f}")
    print(f"  mean targets/event, events with a double  : {n_present[dup>0].mean():.3f}")
    print(f"  mean targets/event, events without        : {n_present[dup==0].mean():.3f}")
