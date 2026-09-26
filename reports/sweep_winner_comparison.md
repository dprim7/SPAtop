# Vanilla vs pairwise: the true sweep winners, 2t and 4t

Every 2t number published before this used `iflm6fht` / `wclzbk8u`, the winners
under W&B's last-epoch summary ranking (see `model_selection_audit.md`). The
best-of-history winners had never been evaluated. They now have been, with
verified checkpoint selection, and all six prediction sets below are scored by
the same code (`reports/scripts/topology_metrics.py`).

Numbers are **slot-order-free**: a true top counts as reconstructed if any
predicted slot of that topology reproduces it. Event purity is bijective (every
present top correct under one consistent slot assignment).

## 2t, fixed test set (187,348 events) -- the comparable, trusted set

| model | FB | FR | SRqq | event purity |
|---|---|---|---|---|
| vanilla `g2vc1w2g` (21.2M par) | 99.8 | 28.8 | 71.6 | 38.48 |
| pairwise `gs8pex8v` (5.3M par) | 99.8 | **31.8** | 72.0 | **40.80** |

**Correcting the mis-pick widened the pairwise advantage rather than removing
it.** Against the previously published runner-up numbers:

| | FR (old -> true) | event purity (old -> true) |
|---|---|---|
| vanilla | 25.0 -> 28.8 | 36.6 -> 38.48 |
| pairwise | 26.0 -> 31.8 | 37.2 -> 40.80 |
| **pairwise minus vanilla** | **+1.0 -> +3.0** | **+0.6 -> +2.3** |

The FR gap triples and the event-purity gap nearly quadruples. Note also that
the pairwise winner does this with **4x fewer parameters** (5.3M vs 21.2M).

## 2t, v6 large test set (3,839,774 events) -- transfer, read FR only

Both models were trained on the fixed 864k dataset and are applied unchanged to
v6, so this is a cross-era robustness test, not "performance on the large set".

| model | FB* | FR | SRqq** | event purity** |
|---|---|---|---|---|
| vanilla `g2vc1w2g` | 28.9 | 13.9 | 38.1 | 18.33 |
| pairwise `gs8pex8v` | 33.3 | **22.8** | 21.6 | 14.38 |

\* v6's FB definition drifted (its "FB" fat jets are W-massed, sdmass ~80, vs
top-massed in the fixed production), so FB transfers poorly for both arms.
\*\* v6's SRqq labels are decoder-evicted (~100% of SRqq targets double-book
their b-jet with an FR target, vs 36% in the fixed set), so the SRqq column and
the event purity that depends on it are **not interpretable** here.

On the one column v6 supports, FR, **pairwise leads by 8.9 points** (22.8 vs
13.9), the largest architecture gap measured anywhere in the campaign.

## 4t, tttt_15M test set (407,830 events)

| model | FB | FR | SRqq | event purity |
|---|---|---|---|---|
| vanilla `0h3k07st` | 99.4 | 20.1 | **56.9** | 34.25 |
| pairwise `booerk48` | 99.6 | **23.3** | 55.7 | **34.81** |

Pairwise leads FR by 3.2 points (+16% relative). The two arms were separated by
0.001 in the sweep metric (0.459 vs 0.458), so the sweep metric did not resolve
a difference the physics metric shows clearly.

## Reading across the three

| setting | training events | FR winner | margin |
|---|---|---|---|
| 2t, fixed | 864k | pairwise | +3.0 |
| 2t, v6-trained (earlier 2x2) | 15.4M | vanilla | +5.0 |
| 4t, tttt | 15M | pairwise | +3.2 |

The ordering is not monotonic in dataset size, and it should not be: what
matters is task difficulty *relative to* available data. Two tops with 15M
events is the one cell where the plain transformer has enough data to learn the
combinatorics unaided. Four tops at comparable statistics is far harder
combinatorially, and there the bias pays again. That is the same
sample-efficiency argument, now with a data point on each side of the crossover.

## Caveats

- One run per cell, no seed variance.
- The 2t/v6 row is transfer, not training on v6.
- `strict-slot` numbers are omitted deliberately: at 4 tops, ordering 4 slots
  correctly is 1/24 by chance, so the column collapses and misleads. SPANet's
  own metric is permutation-aware, matching the slot-free convention used here.
