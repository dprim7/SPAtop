# Speaker notes: SPAtop Update, 13 Aug 2026

## Overview

Roadmap slide. The two items that change the plan are the bigger dataset (data axis is first-order for ttbar) and the four-top result (architecture axis is first-order for tttt).

The 26 -> 55% measure, if asked: fraction of true fully-resolved tops whose complete jet assignment (b, q1, q2) is exactly correct, slot-order-free, on the trusted fixed test set.

## Pairwise attention wins the sweep at a quarter of the model size

30 trials total (10 vanilla, 20 pairwise), bayes plus hyperband(min 15), 50 epochs, fixed dataset. The pairwise MLPs add about 700 parameters, so this is not a capacity effect: every 21M and 84M vanilla trial loses.

Metric check was retroactive over all 29 logged trials: Spearman rho >= 0.97 and identical winners against jet/accuracy_1_of_1 and event purity. The two metrics that would flip the winner do not discriminate (low-stat 3-of-3; detection accuracy spans only 0.852 to 0.861).

The v1 caveat: validation_accuracy = jet/accuracy_6_of_6 is structurally NaN for mutually-exclusive topologies, so it was never logged and bayes had no signal. Ellison's original sweep had the same flaw. That makes v1 effectively random search, so v1 numbers are not a like-for-like comparison against v2. Fixed in v2 and documented in the fork.

Hyperband behaved: every kill sat exactly on the 15 or 45 epoch rungs, including one 84.5M vanilla trial with the best training loss and rising validation loss.

## Class reweighting and the legacy config both hurt

All numbers are the percentage of true tops of that topology whose full assignment is exactly correct, slot-order-free. Event purity is the percentage of events in which every present target is correct.

balance_particles uses effective-number weights over topology-presence equivalence classes. It upweights the rare FB-presence classes, which are already reconstructed about 99.7% of the time, while heavily downweighting the FR-dominant classes that make up two thirds of the fixed dataset. A lose-only trade on this composition.

Secondary confound if asked: class weights shrink the loss by about 100x while l2_penalty stays fixed, so effective weight decay is much stronger. If the group still wants class balance, try sqrt or capped weights with rescaled l2.

The legacy config also plateaued at epoch 11 (lr 1.5e-3, zero dropout). A clean architecture-only reference run is a one-line change if wanted.

Legacy numbers verified live against Alexanders101/SPANet options_files/full_hadronic_ttbar/full_training.json. Vanilla column is the g2vc1w2g sweep winner; heads, encoder layers, clip and balance_particles come from the sweep base config, which every trial shared.

## Correction: our earlier per-topology numbers were slot-ordered

SPANet's own convention permits the t1 to t2 permutation within a topology group; our earlier numbers compared FRt1-prediction against FRt1-truth strictly. The re-derived permutation-aware numbers agree with SPANet's logged event purity to better than 0.5 points, which is the cross-check.

State this before someone else finds it. The real ttbar edge for pairwise is about 1 point, consistent with the pt-curves and the sweep gap.

Also from this study, an actionable item for the analysis pipeline: ranking candidates by MARGINAL probability beats detection probability at every operating point (FR about 50% vs 20% purity at low efficiency). The group pipeline currently selects on dp via dp_to_TopNumProb.

## The bigger training set nearly doubles fully-resolved reconstruction

v6 is the 15.36M-event delphes set on cms-ml, the only column-complete large set available. We repaired two mechanical defects before use (see backup).

Cost side: v6 labels cover essentially no soft resolved tops below about 120 GeV, a definition drift between production eras that the group should be aware of. Crossover with the fixed-data models is at about 180 GeV.

Evaluated on the TRUSTED fixed test set deliberately: if v6 labels were bad, that would show up as poor transfer. FR nearly doubling is the evidence that v6 FR labels are sound.

## v6's SRqq failure is decoder eviction, not bad labels

The diagnostic that cracked it: SRqq assignment loss about 0.5 (the model puts 55 to 60% probability on the exact labeled pair) while SPANet's own purity read 0.5%. Loss and purity score the same targets, so they can only diverge if the DECODE step changes the answer.

extract_prediction (prediction_selection.py:185-199) decodes greedily and masks each claimed jet in EVERY other particle's distribution. v6 labels the same top both FR-wise and SRqq-wise with the same b, for 1,456,367 of 1,456,368 targets. Fixed data sits at 36%, which is why it works there.

TWO FIXES. (A) Thomas regenerates v6 targets under the fixed-era exclusivity rule; FR and FB need no rework. (B) group-aware decoding exclusivity, meaning do not mask across FR and SRqq, which are alternative descriptions of one top. (B) is worth points on models we have ALREADY trained, independent of v6.

Full write-up: reports/v6_srqq_bug_report.md.

## In t̄t the attention bias is a sample-efficiency device

Caveat to state: the vanilla arm ran with pairwise-tuned hyperparameters and still won at scale, so the conclusion is conservative. One run per cell, no seed variance. The 5-point large-data gap is probably robust, the 1-point small-data gap is not.

Nuance in the other direction: pairwise transfers the boosted topology across dataset eras much better (FB 98.3 vs 89.6), though partly because it carries the old FB definition more faithfully.

Reading: ttbar's roughly 1.9e4 assignment hypotheses are learnable from data alone, so the bias is a crutch that data eventually replaces.

## After the standard selection the two t̄t architectures are equivalent

Standard analysis means the SPAtop group's own pipeline, tcoulvert/SPAtop src/analysis: candidates are selected with dp_to_TopNumProb and matched to generator tops by deltaR. It is the selection an actual analysis would apply, as opposed to our exact-index match.

Four models here: the fixed-data pair (light) and the v6 pair (dark). The point is that within each dataset the vanilla and pairwise curves lie on top of each other, while the dataset axis separates them cleanly. Purity above 150 GeV: v6 pair 0.55 to 0.62 against 0.45 to 0.52 for the fixed pair. Efficiency at 300 GeV: 0.6 against 0.05.

All-category version is in backup.

## In four tops, pairwise wins decisively

Both arms: identical gs8pex8v-derived hyperparameters, 15 epochs, same 1.63M training events, evaluated on the same 408k test events.

The group-metric check matters because in ttbar their selection ERASED the exact-match gap. Here it confirms it: resolved purity about 2x vanilla across 50 to 300 GeV AND 2 to 3x the efficiency, strictly dominant, with no purity/efficiency trade to argue about. Merged purity leads by 10 to 15 points below 400 GeV.

Those curves were computed on a 100k-event subsample for memory reasons.

## Standard selection confirms it: pairwise doubles resolved purity

Purity roughly 2x vanilla across 50 to 300 GeV AND 2 to 3x the efficiency, so pairwise is strictly dominant with no purity/efficiency trade to argue about.

This is the check that matters: in ttbar the same selection ERASED the exact-match gap. Here it confirms it.

## The advantage holds across all four-top categories

Purity leads by 10 to 15 points below 400 GeV and converges above about 500 GeV, where events are boosted and the assignment is easy. That is the expected shape if the bias is helping with combinatorics.

Semi-resolved and boosted panels are in backup.

## And the advantage grows with data, the opposite of t̄t

This is the money slide. In ttbar the bias is a sample-efficiency device that more data replaces and eventually overtakes. In tttt the gap WIDENS by 4x going from 10.9k to 1.63M training events: the pair-level physics (kT, z, deltaR, m^2) is supplying combinatorial structure the plain transformer does not extract even from 1.6 million events.

If challenged on statistics: one run per arm, but a 13-point gap is far beyond plausible seed noise. The 1-point ttbar small-data gap is not, and I do not lean on it.

## Recommendation: vanilla SPAtop for t̄t, pairwise for multi-top

Naming: the baseline arm is vanilla SPAtop, meaning Billy's SPAtop adaptation of SPANet (billy000400/SPANet@maad_dev) without the pairwise bias. It is not upstream stock SPANet, and calling it that would be wrong.

On upstreaming: if pairwise becomes load-bearing for the multi-top program, the maintenance argument inverts. It should live upstream where HHH-style users share the code path, not in a personal branch. We had a branch move under a running eval this cycle and it broke checkpoint loading.

Assignment-only rather than discriminator is assumed known in the room, so it is off the slide. One line if challenged: the model never sees background, so its probabilities say which topology a ttbar event has, not whether an event is ttbar.

## What we need from this meeting

Decision 2 is the one to push: it is a small change in extract_prediction, it is PR-able, and it pays off on models the group has already trained, independent of anything v6.

Decision 3: since SPANet trains on partial events anyway, loosening the cut could turn a 15M generation into about 5M usable events instead of 2M.

Decision 5: tttt hyperparameters were inherited from the ttbar sweep and never tuned for four tops, so pairwise may well do better still.

## Training curves: a higher plateau, not a faster one

Honest reading of the t̄t panel: pairwise is NOT faster. Vanilla reaches 90% of its own best at epoch 5, pairwise at epoch 8. What pairwise buys is a higher asymptote, 0.4293 against 0.4124. Both curves are flat for tens of epochs around their best, which rules out the objection that the sweep winner was a lucky epoch.

Four-top panel: with 1.63M events an epoch is thousands of steps, so both arms are near their ceiling within one or two epochs. The separation is there from the start and never closes, which argues against a training-length artifact. It does not rule out a learning-rate artifact, which is what the proposed vanilla tuning scan would test.

## Four-top semi-resolved and boosted categories

Semi-resolved qq: pairwise leads by about 9 points. Boosted: both arms sit at 99.8%, since picking one fat jet out of five is nearly trivial and there is no combinatorial problem for the bias to help with. That contrast is itself evidence for the mechanism.

## How we built the four-top sample

The group's converter was already parameterised in n_tops with IntRange(2,4), so Tommy built for this. The only new artifacts are a one-line MadGraph process card and the four-top event yaml.

Gate results at scale: zero structural defects across 3.06M labeled tops, double-booking 29.1% (better than our ttbar training set's 36%), and all label-physics windows reproduced (FR 94.3%, W 100.0%, SRqq 83.9%, FB 85.4%). Acceptance is 13.6% from the >=12-jet cut.

Cost model: MadGraph about 0.15 s per event steady state. 1M is an afternoon, 15M is an overnight run at 100 parallel shards.

## Caveats, stated up front

Also: v6 arms are FR and FB only until SRqq is resolved; both tttt arms were still improving slowly at 15 epochs.

## Pipeline defects found this cycle

deltaRfj: 16,008,000 rows against 15,358,683 events in all v6 files, and silently dropped in v7 and v8. We reverse-engineered the encoding, floor(min deltaR to a valid fat jet) with a 999 sentinel and 0 on padding, and validated it 100.0000% exact against the fixed dataset before rewriting our copies.

Poisoned event: index 5,847,747, an SRqqt2 pointing at a masked fat-jet slot. Present in v8 too.

Split bug: convert_to_h5.py decides train against test by looking for 'training' in the OUTPUT filename. We hit it at 15M scale and got identical train and test sets until it was caught. Deserves an explicit CLI flag.

Newline: appending to LHE_condor.cmnd without a leading backslash-n glues onto the final comment line and is ignored, which cost us an 80% event deficit. The condor scripts' echo -e is load-bearing.

Also: DelphesPythia8 is absent from the mapyde image and must be built; the analysis environment needs numba==0.60.0 and llvmlite==0.43.0 pinned.

## Where everything lives

W&B runs: jeoe2uix and qvkb6l9q (tttt 15M vanilla and pairwise), gs8pex8v and g2vc1w2g (ttbar sweep winners), 7gcuyuk4 and 7ud0ns0s (tttt pilot).

