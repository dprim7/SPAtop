# Why four tops is harder to learn than two: combinatorics, exclusivity, exchangeability

Working note, 2026-08-13. Written after the tt and tttt architecture results
disagreed in sign, to pin down *which* kind of difficulty the pairwise
attention bias is actually relieving.

The short version: three distinct mechanisms make multi-top assignment hard,
they scale differently in the number of tops $T$ and the number of jets $N$,
and the measurement we already have discriminates between them. It points away
from raw combinatorics and towards the permutation symmetry of identical tops.

## 1. The counting

An event gives $N$ reconstructed jets. For $T$ fully-resolved tops we choose
$T$ disjoint triplets $A_k=(b_k,\{q_1,q_2\}_k)$. The number of distinct
hypotheses is

$$
H_T(N) \;=\; \frac{N!}{(N-3T)!\;2^{T}\;T!}
$$

The $2^T$ removes the $q_1 \leftrightarrow q_2$ symmetry within each top, the
$T!$ removes the exchange of identical tops. With our slot counts
($N = 3T+4$):

| $T$ | $N$ | $H_T(N)$ | $\log_{10} H_T$ |
|---|---|---|---|
| 2 | 10 | $1.9\times10^{4}$ | 4.3 |
| 4 | 16 | $2.3\times10^{9}$ | 9.4 |
| 6 | 22 | $1.0\times10^{15}$ | 15.0 |

Single-top discrimination, the size of one head's softmax denominator, grows
far more slowly:

$$
H_1(N) = \frac{N(N-1)(N-2)}{2} \;=\; 360,\; 1680,\; 4620 \quad (N=10,16,22)
$$

## 2. Three mechanisms, not one

Write the joint posterior over assignments:

$$
P(A_1,\dots,A_T \mid J) \;=\; \frac{1}{Z(J)} \prod_{k=1}^{T} \phi(A_k \mid J)
\prod_{k<l} \mathbb{1}\!\left[A_k \cap A_l = \varnothing\right]
$$

**If the tops were statistically independent**, the indicators would drop out,
$Z(J)$ would factorise, and one would learn a *single* scorer $\phi$ and apply
it $T$ times. Then $T$ would cost search time at decode and nothing at
training. Difficulty would be pure combinatorics. They are not independent,
and the couplings separate into:

**(a) Exclusivity.** The $\binom{T}{2}$ indicator terms make $Z(J)$
non-factorisable. This is a hard-constraint Markov random field, equivalently
weighted 3-uniform hypergraph matching. Constraint count: $1,\,6,\,15$ for
$T=2,4,6$. This is the same coupling that caused the v6 SRqq eviction (see
`v6_srqq_bug_report.md`): SPANet's decoder enforces it globally at inference.

**(b) Exchangeability.** Identical tops mean the *targets* are defined only up
to permutation. The loss minimises over the permutation group:

$$
\mathcal{L}(J) \;=\; \min_{\sigma \in \mathcal{S}_T} \sum_{k=1}^{T}
-\log \frac{\exp S_{\sigma(k)}\!\left(A_k^{\text{true}}\right)}
{\sum_{A} \exp S_{\sigma(k)}(A)}
$$

with $|\mathcal{S}_T| = T! = 2,\,24,\,720$. Early in training the scores are
near-random, so $\arg\min_\sigma$ is close to arbitrary and credit lands on a
different head each batch. This is a symmetry-breaking / identifiability
problem. It scales factorially in $T$ and is **independent of $N$**.

**(c) Per-top discrimination.** Each head must beat $H_1(N)$ competitors. This
is the only mechanism that grows with jet multiplicity, and it grows mildly:
a factor 4.7 from $N=10$ to $N=16$.

## 3. What the data says

Mechanism (c) depends on $N$. Mechanisms (a) and (b) depend only on $T$. So
binning the pairwise-minus-vanilla gap by jet multiplicity *within* a dataset
separates them. Result (`plots_dp_fixed/complexity_trend.png`, from existing
predictions):

| dataset | gap across $N$ | gap across labelled tops |
|---|---|---|
| tttt, 1.63M train | $+13.3 \to +12.1$ ($N=12\to16$) | $+12.8,\,+13.5,\,+14.1,\,+13.1$ |
| tt, 15.4M train | $-5.5 \to -2.9$ ($N=6\to10$) | $-5.0,\,-4.7$ |
| tt, 864k train | $+1.9 \to -0.4$ ($N=6\to10$) | $+1.1,\,+0.2$ |

**The gap is flat in $N$ and jumps by 18 points between $T=2$ and $T=4$.** The
difficulty the bias relieves therefore tracks $T$, not $N$: evidence for the
exchangeability or exclusivity channel, not for raw per-event search.

A plausible mechanism: the pairwise features $m_{ij}$, $\Delta R_{ij}$, $k_T$,
$z$ give the heads a physically anchored basis to differentiate on immediately,
so the permutation symmetry breaks in the first epochs rather than the network
wandering among $T!$ near-degenerate configurations.

Note also that the tt and tttt jet ranges (6 to 10, and 12 to 16) do not
overlap, so per-event jet count cannot interpolate between the processes even
in principle.

## 4. Why six tops is the discriminating measurement

The complexity axis is discrete. Top production increments in pairs, so the
only clean points are $T = 2, 4, 6$ (odd counts require an associated $W$, for
example three-top production at roughly 2 fb, and are not worth the trouble).
There is no continuum to interpolate. But three points do discriminate between
the three mechanisms, because they scale differently:

$$
\log_{10} H_T = 4.3,\; 9.4,\; 15.0 \qquad
\binom{T}{2} = 1,\; 6,\; 15 \qquad
\ln T! = 0.69,\; 3.18,\; 6.58
$$

A gap at $T=6$ only modestly above $T=4$ favours the $\ln T!$ (exchangeability)
picture. A much larger one favours raw combinatorics. Six-top generation is
running as of 2026-08-13 (`kube/spatop-6t-gen-axol1tl.yml`, production-only
matrix element plus Pythia hadronic decays, the route measured to work on
2026-08-10; the fully decayed 2→18 element is impractical).

## 5. Caveats to keep attached to any conclusion

- **$T$ and data volume are confounded in what we have.** tt was trained at
  864k and 15.4M events, tttt at 1.63M. The clean fix is cheap: train tt on
  the v6 set restricted to about 1.63M events (`dataset_limit` $\approx 0.106$)
  and compare against tttt at 1.63M.
- **The tttt vanilla arm may be undertuned.** It inherited tt-derived
  hyperparameters and ran 15 epochs. Its flat 15% across all event complexities
  looks more like a bad optimisation basin than graceful degradation. Until a
  vanilla-only learning-rate and epoch scan says otherwise, part of the +13
  could be a tuning artifact.
- **$T$ is not a clean knob physically.** Six tops sit near threshold
  ($\ge 6 m_t \approx 1.04$ TeV of rest mass), so they are slower, more
  spherical and more resolved than four tops. Kinematics change along with the
  combinatorics.
- **One run per arm throughout.** No seed variance anywhere in this comparison.

## 6. Open experiments, in priority order

1. Vanilla-only tuning scan on tttt: does a properly tuned vanilla close the
   +13? Roughly 6 short jobs.
2. Matched-data comparison: tt at 1.63M events versus tttt at 1.63M, isolating
   $T$ from data volume. One training.
3. Six-top point: gap at $T=6$, discriminating $\ln T!$ from $\log H_T$.
   Generation running; conversion needs the converter's `--n-tops` range
   widened from `IntRange(2,4)` and the $\ge 3T$ jet cut revisited (18 jets
   would be brutally inefficient).
4. Two-arm dataset-fraction curves per process, to see whether the tttt gap has
   peaked or is still rising.
