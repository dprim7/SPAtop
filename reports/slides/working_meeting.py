#!/usr/bin/env python3
"""Working-meeting deck, 2026-08-13. Content only — theme lives in deck.py.

Rules of the house (see deck.py): assertion headlines, <=4 bullets of <=10
words, one piece of evidence per slide, everything else goes in `notes`.
"""
import os
from deck import render

P = "../plots_dp_fixed"   # figures, relative to reports/slides/

DECK = {
    "title": "SPAtop — working meeting, 13 Aug 2026",
    "footer": "SPAtop · t̄t reconstruction & the multi-top program · 13 Aug 2026",
    "slides": [
        {
            "type": "title",
            "title": "Jet assignment for t̄t — and the multi-top program",
            "subtitle": "Sweep verdict · bigger training set · first four-top results",
            "meta": ["Daniel Primosch", "UC San Diego", "13 August 2026"],
        },
        {
            "title": "Eight feedback items closed — and two results that change the plan",
            "bullets": [
                "Sweep decided: **pairwise blocks**, at 4× fewer parameters",
                "Class reweighting and the OG config: **both negative**",
                "Bigger dataset: fully-resolved **26% → 55%**",
                "New 15M four-top sample: **pairwise wins decisively**",
            ],
            "notes": "Roadmap slide. The two 'change the plan' items are the bigger "
                     "dataset (data axis is first-order for ttbar) and the tttt result "
                     "(architecture axis is first-order for four tops).",
        },
        {
            "title": "Block-pairwise wins the sweep at a quarter of the model size",
            "table": {
                "head": ["sweep", "winner", "params", "best val_avg_jet_acc"],
                "rows": [
                    {"cells": ["vanilla", "g2vc1w2g", "21.2 M", "0.4124"]},
                    {"cells": ["block-pairwise", "gs8pex8v", "5.3 M", "0.4293"], "win": True},
                ],
            },
            "bullets": [
                "Winner is the **smallest model** in the pool",
                "Ranking robust to metric choice (ρ ≥ 0.97)",
                "Caveat: v1 sweeps optimised a **NaN metric** — random search",
            ],
            "notes": "30 trials total (10 vanilla / 20 blocks), bayes + hyperband(min 15), "
                     "50 epochs, fixed dataset. The block MLPs add ~700 parameters, so this "
                     "is not a capacity effect — every 21M and 84M vanilla trial loses.\n\n"
                     "Metric check was retroactive over all 29 logged trials: Spearman rho "
                     ">= 0.97 and identical winners vs jet/accuracy_1_of_1 and event purity. "
                     "The two metrics that would flip the winner don't discriminate "
                     "(low-stat 3-of-3; detection accuracy spans only 0.852-0.861).\n\n"
                     "The v1 caveat: validation_accuracy = jet/accuracy_6_of_6 is structurally "
                     "NaN for mutually-exclusive topologies, so it was never logged and bayes "
                     "had no signal. Ellison's original sweep had the same flaw. Fixed in v2 "
                     "and now documented in the fork.\n\n"
                     "Hyperband behaved: every kill sat exactly on the 15/45-epoch rungs, "
                     "including one 84.5M vanilla trial with the best training loss and "
                     "rising validation loss.",
        },
        {
            "title": "Class reweighting and the OG-paper config both hurt",
            "table": {
                "head": ["arm (fixed data, same test set)", "FR", "SRqq", "FB", "event purity"],
                "rows": [
                    {"cells": ["blocks winner config", "26.0", "71.3", "99.7", "37.2"], "win": True},
                    {"cells": ["+ balance_particles", "1.6", "44.2", "99.7", "15.2"]},
                    {"cells": ["OG SPANet-paper config", "5.1", "36.6", "96.2", "14.6"]},
                ],
            },
            "bullets": [
                "FB is already ~100% findable — **nothing to gain**",
                "Downweighted FR classes (67% of events) collapse",
                "OG row **confounded**: that recipe also sets reweighting",
            ],
            "notes": "balance_particles uses effective-number weights over topology-presence "
                     "equivalence classes. It upweights the rare FB-presence classes, which are "
                     "already reconstructed ~99.7% of the time, while heavily downweighting the "
                     "FR-dominant classes that make up two thirds of the fixed dataset. Lose-only "
                     "trade on this composition.\n\n"
                     "Secondary confound worth mentioning if asked: class weights shrink the loss "
                     "~100x while l2_penalty stays fixed, so effective weight decay is much "
                     "stronger. If the group still wants class balance, try sqrt/capped weights "
                     "with rescaled l2.\n\n"
                     "OG config also plateaued at epoch 11 (lr 1.5e-3, zero dropout). A clean "
                     "architecture-only reference run is a one-line change if wanted.",
        },
        {
            "title": "Correction: our earlier per-topology numbers were slot-ordered",
            "figure": f"{P}/accuracy_by_topology_permfree.png",
            "bullets": [
                "FB is **~99.7%** reconstructed — the old 50% was a coin flip",
                "SRqq **71.3%** for both architectures",
                "FR 26.0 vs 25.0 — the “**2× FR**” claim was slot ordering",
            ],
            "notes": "SPANet's own convention permits the t1<->t2 permutation within a topology "
                     "group; our earlier numbers compared FRt1-prediction against FRt1-truth "
                     "strictly. Re-derived permutation-aware numbers agree with SPANet's logged "
                     "event purity to better than 0.5 points, which is the cross-check.\n\n"
                     "State this before someone finds it. The real ttbar edge for blocks is about "
                     "1 point, consistent with the pt-curves and the sweep gap.\n\n"
                     "Also from this study, an actionable item for the analysis pipeline: ranking "
                     "candidates by MARGINAL probability beats detection probability at every "
                     "operating point (FR ~50% vs ~20% purity at low efficiency). The group "
                     "pipeline currently selects on dp via dp_to_TopNumProb.",
        },
        {
            "title": "The bigger training set nearly doubles fully-resolved reconstruction",
            "table": {
                "head": ["model (evaluated on the trusted fixed test set)", "FR", "SRqq", "FB"],
                "rows": [
                    {"cells": ["blocks — fixed data, 864 k events", "26.0", "71.3", "99.7"]},
                    {"cells": ["blocks — delphes v6, 15.4 M events", "49.8", "3.0 *", "98.3"], "win": True},
                    {"cells": ["vanilla — delphes v6, 15.4 M events", "54.8", "1.3 *", "89.6"], "win": True},
                ],
            },
            "bullets": [
                "Group curves: **+10 pts** resolved purity above 150 GeV",
                "**3–6×** the high-pT efficiency (0.6 vs 0.05 at 300 GeV)",
                "\\* SRqq needs a fix — next slide",
            ],
            "notes": "v6 = 15.36M events on cms-ml, the only column-complete large set. We "
                     "repaired two mechanical defects before use (see backup).\n\n"
                     "Cost side: v6 labels cover essentially no soft resolved tops below ~120 GeV "
                     "— definition drift between production eras that the group should be aware "
                     "of. Crossover with the fixed-data models is at ~180 GeV.\n\n"
                     "Evaluated on the TRUSTED fixed test set deliberately: if v6 labels were "
                     "bad, that would show as poor transfer. FR nearly doubling is the evidence "
                     "that v6's FR labels are sound.",
        },
        {
            "title": "v6's SRqq failure is decoder eviction, not bad labels",
            "figure": f"{P}/v6_srqq_proof_eviction.png",
            "bullets": [
                "v6 SRqq labels are **~89% physically correct**",
                "But the b-jet is double-booked with FR in **~100%** of targets",
                "SPANet's decoder is globally exclusive → SRqq is evicted",
                "Same effect costs **17.4%** on our current fixed data",
            ],
            "notes": "The diagnostic that cracked it: SRqq assignment loss ~0.5 (the model puts "
                     "55-60% probability on the exact labeled pair) while SPANet's own purity "
                     "read 0.5%. Loss and purity score the same targets, so they can only "
                     "diverge if the DECODE step changes the answer.\n\n"
                     "extract_prediction (prediction_selection.py:185-199) decodes greedily and "
                     "masks each claimed jet in EVERY other particle's distribution. v6 labels "
                     "the same top both FR-wise and SRqq-wise with the same b, for 1,456,367 of "
                     "1,456,368 targets. Fixed data: 36% — which is why it works there.\n\n"
                     "TWO FIXES. (A) Thomas regenerates v6 targets under the fixed-era "
                     "exclusivity rule; FR/FB need no rework. (B) group-aware decoding "
                     "exclusivity — don't mask across FR<->SRqq, which are alternative "
                     "descriptions of one top. (B) is worth points on models we have ALREADY "
                     "trained, independent of v6.\n\n"
                     "Full write-up: reports/v6_srqq_bug_report.md.",
        },
        {
            "title": "In t̄t the attention bias is a sample-efficiency device",
            "table": {
                "head": ["FR reconstruction, slot-order-free", "864 k events", "15.4 M events"],
                "rows": [
                    {"cells": ["vanilla", "25.0", "54.8"], "win": False},
                    {"cells": ["block-pairwise", "26.0", "49.8"]},
                ],
            },
            "bullets": [
                "Blocks leads narrowly at small data, **4× parameter efficiency**",
                "Vanilla **wins outright** at 15.4 M events",
                "Group pt-curves: architectures **equivalent** at scale",
            ],
            "notes": "Caveat to state: the vanilla arm ran with blocks-tuned hyperparameters and "
                     "still won at scale, so the conclusion is conservative. One run per cell, no "
                     "seed variance — the 5-point large-data gap is probably robust, the 1-point "
                     "small-data gap is not.\n\n"
                     "Nuance in the other direction: blocks transfers the boosted topology across "
                     "dataset eras much better (FB 98.3 vs 89.6), though partly because it "
                     "carries the old FB definition more faithfully.\n\n"
                     "Reading: ttbar's ~1.9e4 assignment hypotheses are learnable from data "
                     "alone, so the bias is a crutch that data eventually replaces.",
        },
        {
            "title": "We built the four-top chain end to end this cycle",
            "bullets": [
                "Card → MadGraph → Delphes → converter → gate → SPANet",
                "Group converter used **unmodified** at `--n-tops 4`",
                "15 M events generated: 750 shards, **zero failures**, ~6 h",
                "**1.63 M train / 408 k test**, label gate PASS",
            ],
            "notes": "The group's converter was already parameterised in n_tops with "
                     "IntRange(2,4) — Tommy built for this. The only new artifacts are a "
                     "one-line MadGraph process card and the 4-top event yaml.\n\n"
                     "Gate results at scale: zero structural defects across 3.06M labeled tops, "
                     "double-booking 29.1% (BETTER than our ttbar training set's 36%), and all "
                     "label-physics windows reproduced (FR 94.3%, W 100.0%, SRqq 83.9%, FB "
                     "85.4%). Acceptance is 13.6% from the >=12-jet cut.\n\n"
                     "Cost model: MadGraph ~0.15 s/event steady state. 1M is an afternoon, 15M "
                     "is an overnight run at 100 parallel shards.",
        },
        {
            "title": "In four tops, pairwise wins decisively",
            "table": {
                "head": ["tttt, 1.63 M training events", "FR", "SRqq", "FB", "event", "val"],
                "rows": [
                    {"cells": ["vanilla", "15.4", "43.6", "99.8", "29.0", "0.4046"]},
                    {"cells": ["block-pairwise", "28.4", "52.9", "99.8", "35.2", "0.4558"], "win": True},
                ],
            },
            "kicker": "FR +13.0 points — an 84% relative improvement.",
            "bullets": [
                "SRqq **+9.3**, event-level **+6.2**",
                "Group's own metric agrees: **~2× purity and 2–3× efficiency**",
            ],
            "notes": "Both arms: identical gs8pex8v-derived hyperparameters, 15 epochs, same "
                     "1.63M training events, evaluated on the same 408k test events.\n\n"
                     "The group-metric check matters because in ttbar their selection ERASED the "
                     "exact-match gap. Here it confirms it: resolved purity ~2x vanilla across "
                     "50-300 GeV AND 2-3x the efficiency — strictly dominant, no purity/efficiency "
                     "trade to argue about. Merged purity leads by 10-15 points below 400 GeV.\n\n"
                     "Those curves were computed on a 100k-event subsample for memory reasons.",
        },
        {
            "title": "And the advantage grows with data — the opposite of t̄t",
            "table": {
                "head": ["FR gap, blocks − vanilla", "t̄t", "tttt"],
                "rows": [
                    {"cells": ["small data", "+1.0  (864 k)", "+3.3  (10.9 k)"]},
                    {"cells": ["large data", "−5.0  (15.4 M)", "+13.0  (1.63 M)"], "win": True},
                ],
            },
            "bullets": [
                "t̄t: ~2 × 10⁴ hypotheses — **learnable from data alone**",
                "tttt: ~10⁸ hypotheses — **the bias supplies what data cannot**",
            ],
            "notes": "This is the money slide. In ttbar the bias is a sample-efficiency device "
                     "that more data replaces and eventually overtakes. In tttt the gap WIDENS "
                     "by 4x going from 10.9k to 1.63M training events — the pair-level physics "
                     "(kT, z, deltaR, m^2) is supplying combinatorial structure the plain "
                     "transformer does not extract even from 1.6 million events.\n\n"
                     "If challenged on statistics: one run per arm, but a 13-point gap is far "
                     "beyond plausible seed noise; the 1-point ttbar small-data gap is not, and "
                     "I don't lean on it.",
        },
        {
            "title": "Recommendation: stock SPANet for t̄t, keep pairwise for multi-top",
            "bullets": [
                "t̄t offline: **stock SPANet** — shared tooling, no fork to maintain",
                "Use it for **assignment only**, not as a discriminator",
                "Multi-top: **keep and upstream** the pairwise bias",
                "Data is first-order for t̄t; architecture is first-order for tttt",
            ],
            "notes": "On the discriminator point, if it comes up: the model has never seen "
                     "background, so its probabilities are calibrated to WHICH topology a ttbar "
                     "event has, not WHETHER an event is ttbar. Jet assignment is an intra-event "
                     "ranking, so process-level mismodelling largely cancels and the output is "
                     "validatable in data through the top and W mass peaks. A discriminator is an "
                     "inter-event, process-level statement fully exposed to QCD mismodelling. "
                     "Discriminate downstream on the assigned candidates' physical observables.\n\n"
                     "On upstreaming: if pairwise becomes load-bearing for the multi-top program, "
                     "the maintenance argument inverts — it should live upstream where HHH-style "
                     "users share the code path, not in a personal branch. We had a branch move "
                     "under a running eval this cycle and it broke checkpoint loading.",
        },
        {
            "type": "decisions",
            "title": "What we need from this meeting",
            "decisions": [
                "**v6 SRqq relabel** — regenerate targets under the fixed-era rule (Thomas)",
                "**Group-aware decoding** — recovers 17.4% on our *current* data too",
                "**The ≥3n-jet cut** — 13.6% acceptance dominates four-top event economy",
                "**Selection variable** — switch pipeline from detection to marginal probability",
                "**tttt next step** — dedicated sweep, more statistics, or both?",
            ],
            "notes": "Decision 2 is the one to push: it is a small change in extract_prediction, "
                     "it is PR-able, and it pays off on models the group has already trained — "
                     "independent of anything v6.\n\n"
                     "Decision 3: since SPANet trains on partial events anyway, loosening the cut "
                     "could turn a 15M generation into ~5M usable events instead of 2M.\n\n"
                     "Decision 5: tttt hyperparameters were inherited from the ttbar sweep and "
                     "never tuned for four tops — blocks may well do better still.",
        },
        {"type": "divider", "title": "Backup"},
        {
            "title": "Caveats, stated up front",
            "bullets": [
                "**One run per arm** everywhere — no seed variance",
                "tttt used t̄t-derived hyperparameters, 15 epochs",
                "tttt group curves on a 100 k-event subsample",
                "Delphes-level throughout — no pile-up or detector realism claims",
            ],
            "notes": "Also: v6 arms are FR/FB-only until SRqq is resolved; both tttt arms were "
                     "still improving slowly at 15 epochs.",
        },
        {
            "title": "Pipeline defects found this cycle",
            "bullets": [
                "v6 `deltaRfj` written with the **pre-cleaning row count**",
                "One structurally invalid SRqqt2 target — killed five runs",
                "Train/test split keyed on a **filename substring**",
                "Pythia card has no trailing newline → appends silently lost",
            ],
            "notes": "deltaRfj: 16,008,000 rows vs 15,358,683 events in all v6 files; silently "
                     "dropped in v7/v8. We reverse-engineered the encoding — floor(min deltaR to "
                     "a valid fat jet), 999 sentinel, 0 on padding — and validated it 100.0000% "
                     "exact against the fixed dataset before rewriting our copies.\n\n"
                     "Poisoned event: index 5,847,747, SRqqt2 pointing at a masked fat-jet slot. "
                     "Present in v8 too.\n\n"
                     "Split bug: convert_to_h5.py decides train vs test by looking for 'training' "
                     "in the OUTPUT filename. We hit it at 15M scale and got identical train and "
                     "test sets until caught. Deserves an explicit CLI flag.\n\n"
                     "Newline: appending to LHE_condor.cmnd without a leading \\n glues onto the "
                     "final comment line and is ignored — cost us an 80% event deficit. The "
                     "condor scripts' echo -e is load-bearing.\n\n"
                     "Also: DelphesPythia8 is absent from the mapyde image and must be built; "
                     "analysis env needs numba==0.60.0/llvmlite==0.43.0 pinned.",
        },
        {
            "title": "Where everything lives",
            "bullets": [
                "Data: `/data/spatop/{tttt_15M, delphes_v6, tttt_pilot}/`",
                "Code, jobs, figures: branch `claude/great-curie-12c321`",
                "Forensics: `reports/v6_srqq_bug_report.md`",
                "Generation recipe: `simulation/tttt/README.md`",
            ],
            "notes": "W&B runs: jeoe2uix / qvkb6l9q (tttt 15M vanilla/blocks), "
                     "gs8pex8v / g2vc1w2g (ttbar sweep winners), 7gcuyuk4 / 7ud0ns0s (tttt pilot).",
        },
    ],
}

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "working_meeting_2026-08-13.html")
    notes = os.path.join(here, "working_meeting_2026-08-13_notes.md")
    render(DECK, out, notes)
    print(f"wrote {out}\nwrote {notes}")
