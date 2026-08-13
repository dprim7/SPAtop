#!/usr/bin/env python3
"""Working-meeting deck, 2026-08-13. Content only; theme lives in deck.py.

House rules (see deck.py): assertion headlines, <=4 bullets of <=10 words, one
piece of evidence per slide, detail into `notes`, and no em dashes anywhere.
"""
import os
from deck import render

P = "../plots_dp_fixed"   # figures, relative to reports/slides/

DECK = {
    "title": "SPAtop Update, 13 Aug 2026",
    "footer": "SPAtop Update · 13 Aug 2026",
    "slides": [
        {
            "type": "title",
            "title": "SPAtop Update",
            "subtitle": "Sweep verdict · bigger training set · first four-top results",
            "meta": ["Daniel Primosch", "UC San Diego", "13 August 2026"],
        },
        {
            "title": "Overview",
            "bullets": [
                "Sweep decided: **pairwise attention**, at 4× fewer parameters",
                "Class reweighting and the legacy config: **both negative**",
                "Bigger dataset: fully-resolved tops correctly assigned, **26% → 55%**",
                "New 15M four-top sample: **pairwise wins decisively**",
            ],
            "notes": "Roadmap slide. The two items that change the plan are the bigger "
                     "dataset (data axis is first-order for ttbar) and the four-top result "
                     "(architecture axis is first-order for tttt).\n\n"
                     "The 26 -> 55% measure, if asked: fraction of true fully-resolved tops "
                     "whose complete jet assignment (b, q1, q2) is exactly correct, "
                     "slot-order-free, on the trusted fixed test set.",
        },
        {
            "title": "Pairwise attention wins the sweep at a quarter of the model size",
            "table": {
                "head": ["sweep", "winner ID", "params", "best val_avg_jet_acc"],
                "rows": [
                    {"cells": ["vanilla", "g2vc1w2g", "21.2 M", "0.4124"]},
                    {"cells": ["pairwise", "gs8pex8v", "5.3 M", "0.4293"], "win": True},
                ],
            },
            "bullets": [
                "Winner is the **smallest model** in the pool",
                "Ranking robust to metric choice (ρ ≥ 0.97)",
                "v1 sweeps optimised a metric that was structurally **NaN**",
                "Random search: not a like-for-like comparison",
            ],
            "notes": "30 trials total (10 vanilla, 20 pairwise), bayes plus hyperband(min 15), "
                     "50 epochs, fixed dataset. The pairwise MLPs add about 700 parameters, so "
                     "this is not a capacity effect: every 21M and 84M vanilla trial loses.\n\n"
                     "Metric check was retroactive over all 29 logged trials: Spearman rho "
                     ">= 0.97 and identical winners against jet/accuracy_1_of_1 and event "
                     "purity. The two metrics that would flip the winner do not discriminate "
                     "(low-stat 3-of-3; detection accuracy spans only 0.852 to 0.861).\n\n"
                     "The v1 caveat: validation_accuracy = jet/accuracy_6_of_6 is structurally "
                     "NaN for mutually-exclusive topologies, so it was never logged and bayes "
                     "had no signal. Ellison's original sweep had the same flaw. That makes v1 "
                     "effectively random search, so v1 numbers are not a like-for-like "
                     "comparison against v2. Fixed in v2 and documented in the fork.\n\n"
                     "Hyperband behaved: every kill sat exactly on the 15 or 45 epoch rungs, "
                     "including one 84.5M vanilla trial with the best training loss and rising "
                     "validation loss.",
        },
        {
            "title": "Class reweighting and the legacy config both hurt",
            "table": {
                "head": ["arm (fixed data, same test set)", "FR", "SRqq", "FB", "event purity"],
                "rows": [
                    {"cells": ["pairwise winner config", "26.0", "71.3", "99.7", "37.2"], "win": True},
                    {"cells": ["+ balance_particles", "1.6", "44.2", "99.7", "15.2"]},
                    {"cells": ["legacy SPANet-paper config", "5.1", "36.6", "96.2", "14.6"]},
                ],
            },
            "bullets": [
                "FB is already ~100% findable, so **nothing to gain**",
                "Downweighted FR classes (67% of events) collapse",
            ],
            "minitable": {
                "label": "Legacy differs on every regularisation knob",
                "head": ["", "best vanilla (g2vc1w2g)", "legacy (SPANet paper)"],
                "rows": [
                    ["learning rate", "4.7e-4", "1.5e-3"],
                    ["dropout", "0.24", "0"],
                    ["gradient clip", "10", "0"],
                    ["balance_particles", "off", "on"],
                ],
            },
            "notes": "All numbers are the percentage of true tops of that topology whose full "
                     "assignment is exactly correct, slot-order-free. Event purity is the "
                     "percentage of events in which every present target is correct.\n\n"
                     "balance_particles uses effective-number weights over topology-presence "
                     "equivalence classes. It upweights the rare FB-presence classes, which are "
                     "already reconstructed about 99.7% of the time, while heavily "
                     "downweighting the FR-dominant classes that make up two thirds of the "
                     "fixed dataset. A lose-only trade on this composition.\n\n"
                     "Secondary confound if asked: class weights shrink the loss by about 100x "
                     "while l2_penalty stays fixed, so effective weight decay is much stronger. "
                     "If the group still wants class balance, try sqrt or capped weights with "
                     "rescaled l2.\n\n"
                     "The legacy config also plateaued at epoch 11 (lr 1.5e-3, zero dropout). A "
                     "clean architecture-only reference run is a one-line change if wanted.\n\n"
                     "Architecture also differs: 8 heads and 4 encoder layers for us, 4 and 6 "
                     "for legacy. Left off the slide because the regularisation "
                     "differences are what drive the result.\n\n"
                     "Legacy numbers verified live against "
                     "Alexanders101/SPANet options_files/full_hadronic_ttbar/"
                     "full_training.json. Vanilla column is the g2vc1w2g sweep winner; "
                     "heads, encoder layers, clip and balance_particles come from the "
                     "sweep base config, which every trial shared.",
        },
        {
            "title": "Correction: our earlier per-topology numbers were slot-ordered",
            "figure": f"{P}/accuracy_by_topology_permfree.png",
            "bullets": [
                "FB is **~99.7%** reconstructed, not the 50% we showed",
                "SRqq **71.3%** for both architectures",
                "FR 26.0 vs 25.0: the “**2× FR**” claim was slot ordering",
            ],
            "notes": "SPANet's own convention permits the t1 to t2 permutation within a "
                     "topology group; our earlier numbers compared FRt1-prediction against "
                     "FRt1-truth strictly. The re-derived permutation-aware numbers agree with "
                     "SPANet's logged event purity to better than 0.5 points, which is the "
                     "cross-check.\n\n"
                     "State this before someone else finds it. The real ttbar edge for pairwise "
                     "is about 1 point, consistent with the pt-curves and the sweep gap.\n\n"
                     "Also from this study, an actionable item for the analysis pipeline: "
                     "ranking candidates by MARGINAL probability beats detection probability at "
                     "every operating point (FR about 50% vs 20% purity at low efficiency). The "
                     "group pipeline currently selects on dp via dp_to_TopNumProb.",
        },
        {
            "title": "The bigger training set nearly doubles fully-resolved reconstruction",
            "table": {
                "head": ["model (evaluated on the trusted fixed test set)", "FR", "SRqq", "FB"],
                "rows": [
                    {"cells": ["pairwise, fixed data, 864 k events", "26.0", "71.3", "99.7"]},
                    {"cells": ["pairwise, delphes v6, 15.4 M events", "49.8", "3.0 *", "98.3"], "win": True},
                    {"cells": ["vanilla, delphes v6, 15.4 M events", "54.8", "1.3 *", "89.6"], "win": True},
                ],
            },
            "bullets": [
                "Group curves: **+10 pts** resolved purity above 150 GeV",
                "**3 to 6×** the high-pT efficiency (0.6 vs 0.05 at 300 GeV)",
                "* SRqq needs a fix, see next slide",
            ],
            "notes": "v6 is the 15.36M-event delphes set on cms-ml, the only column-complete "
                     "large set available. We repaired two mechanical defects before use "
                     "(see backup).\n\n"
                     "Cost side: v6 labels cover essentially no soft resolved tops below about "
                     "120 GeV, a definition drift between production eras that the group should "
                     "be aware of. Crossover with the fixed-data models is at about 180 GeV.\n\n"
                     "Evaluated on the TRUSTED fixed test set deliberately: if v6 labels were "
                     "bad, that would show up as poor transfer. FR nearly doubling is the "
                     "evidence that v6 FR labels are sound.",
        },
        {
            "title": "v6's SRqq failure is decoder eviction, not bad labels",
            "figure": f"{P}/v6_srqq_proof_eviction.png",
            "bullets": [
                "v6 SRqq labels are **~89% physically correct**",
                "But the b-jet is double-booked with FR in **~100%** of targets",
                "SPANet's decoder is globally exclusive, so SRqq is evicted",
                "Same effect costs **17.4%** on our current fixed data",
            ],
            "notes": "The diagnostic that cracked it: SRqq assignment loss about 0.5 (the model "
                     "puts 55 to 60% probability on the exact labeled pair) while SPANet's own "
                     "purity read 0.5%. Loss and purity score the same targets, so they can only "
                     "diverge if the DECODE step changes the answer.\n\n"
                     "extract_prediction (prediction_selection.py:185-199) decodes greedily and "
                     "masks each claimed jet in EVERY other particle's distribution. v6 labels "
                     "the same top both FR-wise and SRqq-wise with the same b, for 1,456,367 of "
                     "1,456,368 targets. Fixed data sits at 36%, which is why it works there.\n\n"
                     "TWO FIXES. (A) Thomas regenerates v6 targets under the fixed-era "
                     "exclusivity rule; FR and FB need no rework. (B) group-aware decoding "
                     "exclusivity, meaning do not mask across FR and SRqq, which are alternative "
                     "descriptions of one top. (B) is worth points on models we have ALREADY "
                     "trained, independent of v6.\n\n"
                     "Full write-up: reports/v6_srqq_bug_report.md.",
        },
        {
            "title": "In t̄t the attention bias is a sample-efficiency device",
            "table": {
                "head": ["FR reconstruction, slot-order-free", "864 k events", "15.4 M events"],
                "rows": [
                    {"cells": ["vanilla", "25.0", "54.8"]},
                    {"cells": ["pairwise", "26.0", "49.8"]},
                ],
            },
            "bullets": [
                "Pairwise leads narrowly at small data, **4× parameter efficiency**",
                "Vanilla **wins** at 15.4 M events",
                "Standard analysis: architectures **equivalent** at scale",
            ],
            "notes": "Caveat to state: the vanilla arm ran with pairwise-tuned hyperparameters "
                     "and still won at scale, so the conclusion is conservative. One run per "
                     "cell, no seed variance. The 5-point large-data gap is probably robust, the "
                     "1-point small-data gap is not.\n\n"
                     "Nuance in the other direction: pairwise transfers the boosted topology "
                     "across dataset eras much better (FB 98.3 vs 89.6), though partly because "
                     "it carries the old FB definition more faithfully.\n\n"
                     "Reading: ttbar's roughly 1.9e4 assignment hypotheses are learnable from "
                     "data alone, so the bias is a crutch that data eventually replaces.",
        },
        {
            "title": "After the standard selection the two t̄t architectures are equivalent",
            "figure": f"{P}/pt_curves_2x2/SPAtop2x2_resolved.png",
            "caption": "Resolved tops. Left: purity vs reconstructed pT. "
                       "Right: efficiency vs generated pT.",
            "notes": "Standard analysis means the SPAtop group's own pipeline, "
                     "tcoulvert/SPAtop src/analysis: candidates are selected with "
                     "dp_to_TopNumProb and matched to generator tops by deltaR. It is the "
                     "selection an actual analysis would apply, as opposed to our exact-index "
                     "match.\n\n"
                     "Four models here: the fixed-data pair (light) and the v6 pair (dark). The "
                     "point is that within each dataset the vanilla and pairwise curves lie on "
                     "top of each other, while the dataset axis separates them cleanly. Purity "
                     "above 150 GeV: v6 pair 0.55 to 0.62 against 0.45 to 0.52 for the fixed "
                     "pair. Efficiency at 300 GeV: 0.6 against 0.05.\n\n"
                     "All-category version is in backup.",
        },
        {
            "title": "In four tops, pairwise wins decisively",
            "table": {
                "head": ["tttt, 1.63 M training events", "FR", "SRqq", "FB", "event", "val"],
                "rows": [
                    {"cells": ["vanilla", "15.4", "43.6", "99.8", "29.0", "0.4046"]},
                    {"cells": ["pairwise", "28.4", "52.9", "99.8", "35.2", "0.4558"], "win": True},
                ],
            },
            "kicker": "FR +13.0 points, an 84% relative improvement.",
            "bullets": [
                "SRqq **+9.3**, event-level **+6.2**",
                "Group's own metric agrees: **~2× purity and 2 to 3× efficiency**",
            ],
            "notes": "Both arms: identical gs8pex8v-derived hyperparameters, 15 epochs, same "
                     "1.63M training events, evaluated on the same 408k test events.\n\n"
                     "The group-metric check matters because in ttbar their selection ERASED the "
                     "exact-match gap. Here it confirms it: resolved purity about 2x vanilla "
                     "across 50 to 300 GeV AND 2 to 3x the efficiency, strictly dominant, with "
                     "no purity/efficiency trade to argue about. Merged purity leads by 10 to 15 "
                     "points below 400 GeV.\n\n"
                     "Those curves were computed on a 100k-event subsample for memory reasons.",
        },
        {
            "title": "Standard selection confirms it: pairwise doubles resolved purity",
            "figure": f"{P}/pt_curves_tttt/SPAtop_tttt15M_resolved.png",
            "caption": "Four-top resolved tops, 100 k-event test subsample.",
            "notes": "Purity roughly 2x vanilla across 50 to 300 GeV AND 2 to 3x the "
                     "efficiency, so pairwise is strictly dominant with no purity/efficiency "
                     "trade to argue about.\n\n"
                     "This is the check that matters: in ttbar the same selection ERASED the "
                     "exact-match gap. Here it confirms it.",
        },
        {
            "title": "The advantage holds across all four-top categories",
            "figure": f"{P}/pt_curves_tttt/SPAtop_tttt15M_merged.png",
            "caption": "All categories combined, four tops.",
            "notes": "Purity leads by 10 to 15 points below 400 GeV and converges above about "
                     "500 GeV, where events are boosted and the assignment is easy. That is the "
                     "expected shape if the bias is helping with combinatorics.\n\n"
                     "Semi-resolved and boosted panels are in backup.",
        },
        {
            "title": "And the advantage grows with data, the opposite of t̄t",
            "table": {
                "head": ["FR gap, pairwise − vanilla", "t̄t", "tttt"],
                "rows": [
                    {"cells": ["small data", "+1.0  (864 k)", "+3.3  (10.9 k)"]},
                    {"cells": ["large data", "−5.0  (15.4 M)", "+13.0  (1.63 M)"], "win": True},
                ],
            },
            "equation": [
                "<i>H<sub>T</sub></i>(<i>N</i>) = <i>N</i>! / [ (<i>N</i>−3<i>T</i>)! · 2<sup><i>T</i></sup> · <i>T</i>! ] "
                "&nbsp;&nbsp;→&nbsp;&nbsp; <span class='v'>1.9×10<sup>4</sup></span> (t̄t) "
                "&nbsp;·&nbsp; <span class='v'>2.3×10<sup>9</sup></span> (tttt)",
                "label symmetry <i>T</i>! = <span class='v'>2</span> (t̄t) "
                "&nbsp;·&nbsp; <span class='v'>24</span> (tttt) "
                "&nbsp;·&nbsp; <span class='v'>720</span> (t̄tt̄tt̄t)",
            ],

            "notes": "This is the money slide. In ttbar the bias is a sample-efficiency device "
                     "that more data replaces and eventually overtakes. In tttt the gap WIDENS "
                     "by 4x going from 10.9k to 1.63M training events: the pair-level physics "
                     "(kT, z, deltaR, m^2) is supplying combinatorial structure the plain "
                     "transformer does not extract even from 1.6 million events.\n\n"
                     "If challenged on statistics: one run per arm, but a 13-point gap is far "
                     "beyond plausible seed noise. The 1-point ttbar small-data gap is not, and "
                     "I do not lean on it.",
        },
        {
            "title": "Recommendation: vanilla SPAtop for t̄t, pairwise for multi-top",
            "bullets": [
                "t̄t: **vanilla SPAtop**",
                "t̄tt̄t, t̄tt̄tt̄t: **pairwise attention SPAtop**",
                "**First order improvements**: data for t̄t, architecture for tttt",
            ],
            "notes": "Naming: the baseline arm is vanilla SPAtop, meaning Billy's SPAtop "
                     "adaptation of SPANet (billy000400/SPANet@maad_dev) without the pairwise "
                     "bias. It is not upstream stock SPANet, and calling it that would be "
                     "wrong.\n\n"
                     "On upstreaming: if pairwise becomes load-bearing for the multi-top "
                     "program, the maintenance argument inverts. It should live upstream where "
                     "HHH-style users share the code path, not in a personal branch. We had a "
                     "branch move under a running eval this cycle and it broke checkpoint "
                     "loading.\n\n"
                     "Assignment-only rather than discriminator is assumed known in the room, so "
                     "it is off the slide. One line if challenged: the model never sees "
                     "background, so its probabilities say which topology a ttbar event has, not "
                     "whether an event is ttbar.",
        },
        {
            "type": "decisions",
            "title": "What we need from this meeting",
            "decisions": [
                "**v6 SRqq relabel**: regenerate targets under the fixed-era rule (Thomas)",
                "**Group-aware decoding**: recovers 17.4% on our *current* data too",
                "**The ≥3n-jet cut**: 13.6% acceptance dominates four-top event economy",
                "**Selection variable**: switch pipeline from detection to marginal probability",
                "**tttt next step**: dedicated sweep, more statistics, or both?",
            ],
            "notes": "Decision 2 is the one to push: it is a small change in extract_prediction, "
                     "it is PR-able, and it pays off on models the group has already trained, "
                     "independent of anything v6.\n\n"
                     "Decision 3: since SPANet trains on partial events anyway, loosening the "
                     "cut could turn a 15M generation into about 5M usable events instead of "
                     "2M.\n\n"
                     "Decision 5: tttt hyperparameters were inherited from the ttbar sweep and "
                     "never tuned for four tops, so pairwise may well do better still.",
        },
        {"type": "divider", "title": "Backup"},
        {
            "title": "Training curves: a higher plateau, not a faster one",
            "figure": f"{P}/convergence_both.png",
            "caption": "Top: t̄t sweep winners. Bottom: four tops at 1.63 M events.",
            "notes": "Honest reading of the t̄t panel: pairwise is NOT faster. Vanilla reaches "
                     "90% of its own best at epoch 5, pairwise at epoch 8. What pairwise buys "
                     "is a higher asymptote, 0.4293 against 0.4124. Both curves are flat for "
                     "tens of epochs around their best, which rules out the objection that the "
                     "sweep winner was a lucky epoch.\n\n"
                     "Four-top panel: with 1.63M events an epoch is thousands of steps, so both "
                     "arms are near their ceiling within one or two epochs. The separation is "
                     "there from the start and never closes, which argues against a "
                     "training-length artifact. It does not rule out a learning-rate artifact, "
                     "which is what the proposed vanilla tuning scan would test.",
        },
        {
            "title": "Four-top semi-resolved and boosted categories",
            "figure": f"{P}/tttt_pt_qq_boosted.png",
            "caption": "Top: semi-resolved qq. Bottom: boosted.",
            "notes": "Semi-resolved qq: pairwise leads by about 9 points. Boosted: both arms "
                     "sit at 99.8%, since picking one fat jet out of five is nearly trivial and "
                     "there is no combinatorial problem for the bias to help with. That "
                     "contrast is itself evidence for the mechanism.",
        },
        {
            "title": "How we built the four-top sample",
            "bullets": [
                "Card → MadGraph → Delphes → converter → gate → SPANet",
                "Group converter used **unmodified** at `--n-tops 4`",
                "15 M events generated: 750 shards, **zero failures**, ~6 h",
                "**1.63 M train / 408 k test**, label gate PASS",
            ],
            "callout": {
                "text": "Check physics of the four-top simulations (Tommy?)",
            },
            "notes": "The group's converter was already parameterised in n_tops with "
                     "IntRange(2,4), so Tommy built for this. The only new artifacts are a "
                     "one-line MadGraph process card and the four-top event yaml.\n\n"
                     "Gate results at scale: zero structural defects across 3.06M labeled tops, "
                     "double-booking 29.1% (better than our ttbar training set's 36%), and all "
                     "label-physics windows reproduced (FR 94.3%, W 100.0%, SRqq 83.9%, FB "
                     "85.4%). Acceptance is 13.6% from the >=12-jet cut.\n\n"
                     "Cost model: MadGraph about 0.15 s per event steady state. 1M is an "
                     "afternoon, 15M is an overnight run at 100 parallel shards.",
        },

        {
            "title": "Caveats, stated up front",
            "bullets": [
                "**One run per arm** everywhere, no seed variance",
                "tttt used t̄t-derived hyperparameters, 15 epochs",
                "tttt group curves on a 100 k-event subsample",
                "Delphes level throughout, no pile-up or detector realism claims",
            ],
            "notes": "Also: v6 arms are FR and FB only until SRqq is resolved; both tttt arms "
                     "were still improving slowly at 15 epochs.",
        },
        {
            "title": "Pipeline defects found this cycle",
            "bullets": [
                "v6 `deltaRfj` written with the **pre-cleaning row count**",
                "One structurally invalid SRqqt2 target, killed five runs",
                "Train/test split keyed on a **filename substring**",
                "Pythia card has no trailing newline, appends silently lost",
            ],
            "notes": "deltaRfj: 16,008,000 rows against 15,358,683 events in all v6 files, and "
                     "silently dropped in v7 and v8. We reverse-engineered the encoding, "
                     "floor(min deltaR to a valid fat jet) with a 999 sentinel and 0 on padding, "
                     "and validated it 100.0000% exact against the fixed dataset before "
                     "rewriting our copies.\n\n"
                     "Poisoned event: index 5,847,747, an SRqqt2 pointing at a masked fat-jet "
                     "slot. Present in v8 too.\n\n"
                     "Split bug: convert_to_h5.py decides train against test by looking for "
                     "'training' in the OUTPUT filename. We hit it at 15M scale and got "
                     "identical train and test sets until it was caught. Deserves an explicit "
                     "CLI flag.\n\n"
                     "Newline: appending to LHE_condor.cmnd without a leading backslash-n glues "
                     "onto the final comment line and is ignored, which cost us an 80% event "
                     "deficit. The condor scripts' echo -e is load-bearing.\n\n"
                     "Also: DelphesPythia8 is absent from the mapyde image and must be built; "
                     "the analysis environment needs numba==0.60.0 and llvmlite==0.43.0 pinned.",
        },
        {
            "title": "Where everything lives",
            "bullets": [
                "Data: `/data/spatop/{tttt_15M, delphes_v6, tttt_pilot}/`",
                "Code, jobs, figures: branch `claude/great-curie-12c321`",
                "Forensics: `reports/v6_srqq_bug_report.md`",
                "Generation recipe: `simulation/tttt/README.md`",
            ],
            "notes": "W&B runs: jeoe2uix and qvkb6l9q (tttt 15M vanilla and pairwise), "
                     "gs8pex8v and g2vc1w2g (ttbar sweep winners), 7gcuyuk4 and 7ud0ns0s "
                     "(tttt pilot).",
        },
    ],
}

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "working_meeting_2026-08-13.html")
    notes = os.path.join(here, "working_meeting_2026-08-13_notes.md")
    render(DECK, out, notes)
    print(f"wrote {out}\nwrote {notes}")
