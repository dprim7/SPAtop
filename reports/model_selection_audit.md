# Audit: the five model-selection problems raised on main

All five are real code-level issues. Their impact on our branches differs a lot,
so the verdicts below separate "is the bug real" from "did it change our
numbers". Every number here is reproducible with the scripts in
`reports/scripts/audit_*.py`.

Bottom line: **four of the five did not touch our results, because we had
already worked around them. The fifth (W&B summary ranking) did affect our
sweeps and is the root cause of the winner mis-pick we flagged in July.**

---

## 1. Evaluation loads the wrong checkpoint: REAL and severe. Our impact: none.

`spanet/evaluation.py:56-57`

```python
if checkpoint is None:
    checkpoint = sorted(glob(f"{log_directory}/checkpoints/epoch*"))[-1]
```

The comment above it says "best-performing checkpoint on validation data"; it is
a lexicographic sort. `save_top_k=3, mode='max'` on
`validation_average_jet_accuracy` (`train.py:144-151`) means the three files on
disk really are the best three, so the damage is limited to picking the wrong
one of the three. Both failure modes the postdoc describes are confirmed:
`'3' < '9'` so `epoch=9` sorts above `epoch=24`, and absent a single-digit epoch
it takes the latest rather than the best.

Measured on the actual checkpoint directories of eight of our runs
(`audit_checkpoint_selection.py`):

| run | default would load | true best | gap |
|---|---|---|---|
| sweep blocks winner gs8pex8v | 0.387 (epoch 9) | 0.429 (epoch 24) | 0.042 |
| sweep vanilla winner g2vc1w2g | 0.395 (epoch 9) | 0.412 (epoch 17) | 0.017 |
| sweep blocks e19osz6f | 0.389 (epoch 7) | 0.423 (epoch 25) | 0.034 |
| sweep blocks sqjfkudn | 0.393 (epoch 9) | 0.421 (epoch 15) | 0.028 |
| reweighting gqdxggcd | 0.126 (epoch 8) | 0.217 (epoch 39) | **0.091** |
| OG-ref gusmb6vq | 0.174 (epoch 9) | 0.200 (epoch 11) | 0.026 |
| v6 blocks 69v6t2vw | 0.160 (epoch 9) | 0.161 (epoch 5) | 0.001 |
| v6 vanilla rwlfpx3x | 0.159 | 0.159 | same file |

**7 of 8 would have loaded a sub-optimal checkpoint**, every one of them through
the single-digit-epoch path.

**Why our numbers are safe:** all eight of our eval jobs pass `-ckpt` explicitly.
Seven parse `validation_average_jet_accuracy=...` out of the filename and take
the max; the eighth (`spatop-eval-ab-axol1tl.yml`, the earliest) hardcodes full
paths, and its header comment already documents this exact bug. The default path
is never exercised by our jobs. The group's `kube/v8`-`v10` eval jobs, which pass
only the log directory, are affected.

## 2. Metric ignores detection and false positives: REAL. Our impact: material, and already known.

Confirmed in `jet_reconstruction_validation.py`: `validation_average_jet_accuracy`
scores `jet_predictions` (the argmax assignment) against targets, restricted to
`has_targets = tot_target_weights > 0`. Detection output (`particle_scores`)
feeds only the `particle/*` metrics and never this one. So the metric cannot see
a predicted top that does not exist, and it is not the merged, overlap-removed
quantity the group reports.

We found this independently and it is documented, but the mitigation we recorded
at the time (metric-robustness check, Spearman rho >= 0.97 against
`jet/accuracy_1_of_1` and event purity, same winners) is weaker than it looked:
**every one of those alternatives is also assignment-only**, so that check could
not have detected this problem.

The evidence that it genuinely matters is our own: under the group's
dp-based selection the v6 vanilla and v6 blocks resolved curves lie on top of
each other, while exact-match FR separates them by 5 points (54.8 vs 49.8). The
sweep metric and the reported quantity disagree in exactly the way claimed.

Caveat that limits the damage: this bias is shared by every arm, so A/B
comparisons are far less affected than absolute values.

## 3. Tops in more than one category count more than once: REAL, and bounded.

The per-event denominator is the number of present target slots summed over all
six particles, so a top labelled both FR and SRqq occupies two slots. Measured on
the fixed test set (`audit_metric_weights.py`):

- total target slots (the metric's denominator): 241,480
- slots that re-describe an already counted top: **33,365, i.e. 13.8%**
- events containing at least one such top: 31,999, i.e. **17.1%**
- mean targets/event: 2.32 in those events vs 1.08 in the rest

One refinement to the claim: the metric is a per-event mean, so events are
weighted equally *across* events. The distortion is *within* an event, where a
double-described top carries twice the influence of a singly-described one. The
effect is a systematic ~14% slot inflation concentrated in 17% of events, again
shared across arms.

## 4. W&B ranked by final epoch, not best: REAL, CONFIRMED, and it did affect our sweeps.

This is the one with consequences.

- `define_metric(..., summary="max")` appears **nowhere**: not in either fork,
  not in our sweep runner or configs.
- Empirically (`audit_sweep_ranking.py`), the W&B summary value equals the last
  logged value for **100% of runs in both sweeps** (29/29).
- The sweep metric config is `{goal: maximize, name: validation_average_jet_accuracy}`,
  so the Bayesian controller optimised final-epoch accuracy.

**The winner changes in both sweeps:**

| sweep | winner by summary (what bayes optimised) | winner by best-of-history (what we report) |
|---|---|---|
| vanilla nqupkqcl | w6podt1t, 0.3833 (a hyperband-killed run) | g2vc1w2g, 0.4124 |
| blocks ox8or7c7 | iflm6fht, 0.3881 | gs8pex8v, 0.4293 |

Two consequences worth stating plainly:

1. **This is the root cause of our July mis-pick.** `iflm6fht` is precisely the
   run we originally selected as the blocks winner and used for the evals and
   the pt-curves, and it is exactly the summary-ranked winner. The true
   best-of-history winners `gs8pex8v` and `g2vc1w2g` have still never been
   evaluated, so the fixed-data rows of the comparison table and the pt-curves
   are built on the runner-up models. That re-eval remains outstanding.
2. **Last-value summary interacts perversely with hyperband.** Terminated runs
   stop near their peak (killed at epoch 15 while still climbing) whereas
   completed runs decay from their peak by epoch 50. The vanilla sweep's
   summary-winner is a killed 15-epoch run. The search was rewarded for runs
   that got terminated early.

Our *reported* rankings are unaffected: the decision pack and
`sweep_summary.csv` were built from best-of-history sampled history, which is
why the discrepancy was visible at all. What was affected is the *search*, and
the choice of which models got evaluated downstream.

## 5. Forks differ when weights are not 1: REAL mechanism, but the stated trigger is wrong.

The dtype difference is real and is the fix we already made
(`weighted_jet_accuracies` is `dtype=bool` in the vanilla fork, `float64` in
ours). Numerically (`audit_metric_weights.py`): identical at unit weights,
0.4207 vs 0.5991 once weights vary. It is the only functional difference between
the two forks' metric files.

The trigger, however, is **not** `balance_particles` / `balance_jets`. Those
flags weight the training *loss*
(`jet_reconstruction_training.py:238-244`). The metric's `stacked_weights` come
from the batch targets, i.e. from a per-particle `TARGETS/<particle>/WEIGHT`
dataset in the h5, falling back to ones
(`jet_reconstruction_dataset.py:219-223`). The two `particle_*_tensor_np`
assignments inside validation are dead code: they are never read anywhere in
either fork.

None of our h5 files contain a `WEIGHT` dataset (every run logs "Warning: no
target weights in the dataset, creating ones weights"), so both forks compute
the metric identically, and **turning balancing on does not change that**. This
matters concretely: the currently running legacy resolved-only arms use the
vanilla fork *with* `balance_particles: true`, and their metric is unaffected.

---

## What to actually do

1. **Re-evaluate the true sweep winners** `gs8pex8v` and `g2vc1w2g`. This is the
   one open item that changes published numbers.
2. **Fix the checkpoint default upstream** (sort by the parsed metric, or use
   PyTorch Lightning's `best_model_path`), and add `--checkpoint` to the
   `kube/v8`-`v10` eval jobs. Our jobs already do the right thing and can serve
   as the pattern.
3. **Add `wandb.define_metric("validation_average_jet_accuracy", summary="max")`**
   to the sweep runner before any future sweep.
4. Treat the sweep metric as assignment-only by construction. If the group
   ranks on merged purity/efficiency, that quantity has to be logged during
   validation; no reweighting of the current metric will approximate it.
