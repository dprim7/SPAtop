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

## We built the four-top chain end to end this cycle

The group's converter was already parameterised in n_tops with IntRange(2,4), so Tommy built for this. The only new artifacts are a one-line MadGraph process card and the four-top event yaml.

Gate results at scale: zero structural defects across 3.06M labeled tops, double-booking 29.1% (better than our ttbar training set's 36%), and all label-physics windows reproduced (FR 94.3%, W 100.0%, SRqq 83.9%, FB 85.4%). Acceptance is 13.6% from the >=12-jet cut.

Cost model: MadGraph about 0.15 s per event steady state. 1M is an afternoon, 15M is an overnight run at 100 parallel shards.

On the ask: keep it light in the room. The point is that these are new labels from a chain nobody else has reviewed, and the person best placed to sanity-check the physics is the author of the converter. Offer the files, do not assign work.

## In four tops, pairwise wins decisively

Both arms: identical gs8pex8v-derived hyperparameters, 15 epochs, same 1.63M training events, evaluated on the same 408k test events.

The group-metric check matters because in ttbar their selection ERASED the exact-match gap. Here it confirms it: resolved purity about 2x vanilla across 50 to 300 GeV AND 2 to 3x the efficiency, strictly dominant, with no purity/efficiency trade to argue about. Merged purity leads by 10 to 15 points below 400 GeV.

Those curves were computed on a 100k-event subsample for memory reasons.

## And the advantage grows with data, the opposite of t̄t

This is the money slide. In ttbar the bias is a sample-efficiency device that more data replaces and eventually overtakes. In tttt the gap WIDENS by 4x going from 10.9k to 1.63M training events: the pair-level physics (kT, z, deltaR, m^2) is supplying combinatorial structure the plain transformer does not extract even from 1.6 million events.

If challenged on statistics: one run per arm, but a 13-point gap is far beyond plausible seed noise. The 1-point ttbar small-data gap is not, and I do not lean on it.

## Recommendation: stock SPANet for t̄t, keep pairwise for multi-top

On the discriminator point, if it comes up: the model has never seen background, so its probabilities are calibrated to WHICH topology a ttbar event has, not WHETHER an event is ttbar. Jet assignment is an intra-event ranking, so process-level mismodelling largely cancels and the output is validatable in data through the top and W mass peaks. A discriminator is an inter-event, process-level statement fully exposed to QCD mismodelling. Discriminate downstream on the assigned candidates' physical observables.

On upstreaming: if pairwise becomes load-bearing for the multi-top program, the maintenance argument inverts. It should live upstream where HHH-style users share the code path, not in a personal branch. We had a branch move under a running eval this cycle and it broke checkpoint loading.

## What we need from this meeting

Decision 2 is the one to push: it is a small change in extract_prediction, it is PR-able, and it pays off on models the group has already trained, independent of anything v6.

Decision 3: since SPANet trains on partial events anyway, loosening the cut could turn a 15M generation into about 5M usable events instead of 2M.

Decision 5: tttt hyperparameters were inherited from the ttbar sweep and never tuned for four tops, so pairwise may well do better still.

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

