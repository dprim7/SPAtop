# What `balance_particles` actually does, and why it destroyed the reweighting arm

**Short version.** `balance_particles` does *not* weight topologies. It weights
each event by its **topology-presence class** — the (nFR, nSRqq, nFB) counts —
using an inverse-effective-frequency rule, so that every class contributes an
equal share of the loss. On our 6-target event file that means **2 events can
carry the same total loss weight as 82,259 events**, and the mean per-event
weight collapses to 0.0009. That is the whole explanation for the collapse we
measured (event purity 37.2% → 15.2%, FR 26.0 → 1.6).

Reproduce: `python reports/scripts/balance_particles_probe.py <test file>`
(replicates `spanet/dataset/jet_reconstruction_dataset.py:344-384` exactly).

## The mechanism

1. Equivalence classes are the orbits of the target power set under the event
   permutation group. With FRt1↔FRt2, SRqqt1↔SRqqt2, FBt1↔FBt2 the orbit of a
   subset is determined purely by *how many* of each topology are present, so a
   class ≡ (nFR, nSRqq, nFB) — 27 classes for 6 targets.
2. Each class is counted over events where **exactly** that set is present.
3. Weight = effective-number-of-samples (arXiv:1901.05555) with
   `beta = 1 - 1/N`, i.e. essentially **1/count**, then normalized so the mean
   class weight is 1.
4. The per-event weight multiplies that event's loss
   (`jet_reconstruction_training.py:238-240`).

Because the *class* weights are equalized but the classes have wildly unequal
populations, the *per-event* weights become wildly unequal.

## Measured on the fixed test set (187,348 events)

| class | events | per-event weight | share of total loss |
|---|---|---|---|
| 1FR 0SR 0FB | 82,259 | 0.0001 | 5.19% |
| 0FR 1SR 0FB | 39,387 | 0.0002 | 4.65% |
| 1FR 1SR 0FB | 27,422 | 0.0003 | 4.51% |
| … | | | ~4.2% each |
| 0FR 2SR 2FB | 3 | 1.8240 | 3.15% |
| 2FR 1SR 2FB | **2** | **2.4319** | **2.80%** |

- **Weight spread across populated classes: 22,193×.**
- **Mean per-event weight: 0.0009** — the data term is scaled down ~1100× while
  `l2_penalty` stays fixed, so weight decay silently dominates. This is a second,
  independent failure mode on top of the gradient being hijacked by freak events.
- Three classes with **zero** events still receive the largest weights (7.30),
  because the code adds `+1` to every class count; they inflate the
  normalization and shrink everyone else.

## Why the original SPANet paper enables it safely

The paper's setup is **fully-resolved ttbar only** — 2 targets, so 3 classes:

| event file | targets | classes | weight spread | mean weight |
|---|---|---|---|---|
| resolved-only (OG paper) | 2 | 3 | **11×** | 0.35 |
| multi-topology (our v11) | 6 | 27 | **22,193×** | 0.0009 |

The flag is a mild, sensible correction in the world it was designed for. Our
multi-topology extension inherited it, and the class explosion turned it
pathological. This is not a bug in SPANet; it is a setting that does not
transfer.

## What to use instead

`particle_loss_weights` (dprim7/SPANet@feat/particle-loss-weights): explicit
per-topology weights, e.g. `"FRt:3,SRqqt:2,FBt:1"`, **renormalized to mean 1.0**
so the loss scale — and hence the effective weight decay — is unchanged and the
ratio is the only variable.

Note that the *equal* configuration needs no weights at all: the total loss is
`mean()` over the per-target terms and each topology owns exactly 2 of the 6
targets, so **FR:SR:FB = 1:1:1 is already the default**.
