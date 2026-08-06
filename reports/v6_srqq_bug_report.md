# Why SRqq is unlearnable-looking on delphes v6: decoder eviction, not label noise

**TL;DR.** The v6 SRqq labels are ~89% physically correct. They score ~0.5% because
**v6's labeling convention double-books the b-jet between the FR and SRqq descriptions
of the same top for every single SRqq target (1,456,366 of 1,456,367 on the test set)**,
while SPANet's prediction decoder enforces globally exclusive jet assignment
(`spanet/network/prediction_selection.py:185-199`: greedy most-confident-first, claimed
jets masked to −inf in *every* other particle's distribution). The FR head — trained on
v6's excellent FR labels — claims the b during decoding in **90.2%** of SRqq targets,
evicting SRqq to leftover jets. The loss never decodes, so training happily converges
(SRqq assignment NLL ≈ 0.5 ⇒ ~55–60% probability on the exact labeled pair) while
SPANet's own validation purity reads ~0.5% — the internal contradiction that gave the
mechanism away. Thomas's fixed production works because it cut b double-booking from
~100% to 36% of SRqq targets, i.e. **the fix made the data conform to the decoder**.

## Evidence chain (all reproducible; figures in `plots_dp_fixed/`)

1. **Learnability, in-domain** (`event_metrics.csv`, run 69v6t2vw): a v6-trained model
   reconstructs 44.6% FR / **1.0% SRqq** / 99.9% FB *on v6's own test set*. Whatever is
   wrong is not domain shift.
2. **The labels are good** (`v6_srqq_proof_mass.png` + containment): for same-top
   FR↔SRqq double labels, the labeled `qq` fat jet contains both q1 and q2 (via the
   100%-geometrically-consistent `matchedfj`) in **88.9%** of v6 cases (fixed: 93.3%).
   m(b + fj_qq) forms a real peak (~145 GeV — shifted low vs fixed's 173: definition /
   calibration drift between eras, a separate, secondary observation; also v6 "FB" fat
   jets are W-massed, sdmass ≈ 80).
3. **Training-time contradiction** (W&B 69v6t2vw): SRqq assignment loss 0.52–0.84
   (better than FR's 1.5–2.4) *simultaneously* with SPANet's own SRqq purity 0.003–0.012.
   Loss ≈ −log P(target) ⇒ the model places ~55–60% probability on the exact labeled
   (b, qq) pair it then "gets wrong". Only a convention/constraint difference between
   the loss path and the decode path can do this.
4. **The constraint, in code**: `extract_prediction` decodes greedily and masks every
   claimed jet in **all** particles' distributions (global exclusivity across FRt1/2,
   SRqqt1/2, FBt1/2). Alternative descriptions of the *same* top cannot both hold the b.
5. **Total contention in v6**: SRqq targets whose b is also an FR target's b:
   **1,456,367 of 1,456,368** (v6 test). Fixed: 33,306 of 92,780 (36%).
6. **Causal isolation** (`v6_srqq_proof_eviction.png`): SRqq exact-pair agreement —
   v6 contested 0.5%; fixed contested 37.9% vs fixed free 34.1% (mild contention on
   fixed because either description can win and the loser's score is spread between FR
   and SRqq). Direct eviction measurement: an FR *prediction* occupies SRqq's true b in
   **90.2%** of v6 targets (fixed: 17.4%).

Falsified along the way (kept for the record): labels-are-noise (2), stale matching
table (`matchedfj` 100% consistent in both files, `v6_srqq_proof_matchedfj.png`),
row-truncation join (v6's stored `deltaRfj` is a different-era quantity — it fails
alignment at row 0, and is additionally misaligned in *length*: 16,008,000 rows vs
15,358,683 events; we regenerated the column exactly, validated 100.0000% against the
fixed file's encoding: `floor(min ΔR(jet, valid fj))`, 999 = no fat jet, 0 = padding).

## Proposed fixes

**A. Pipeline (Thomas — the complete fix).** Regenerate v6 targets with the fixed-era
exclusivity semantics (his fix already encodes the rule that took double-booking
100%→36%). FR and FB labels do not need re-deriving — FR is validated by the transfer
result (training on v6 FR labels *doubles* FR performance on the trusted fixed test
set, 49.8 vs 26.0 slot-free). Deliverables he may want: this report, the deltaRfj
regeneration formula, and the one structurally-invalid event (5,847,747, SRqqt2
pointing at a masked fat-jet slot — also present in v8).

**B. Code (principled; benefits the FIXED data too).** Make decoding exclusivity
group-aware: mask claimed jets only within the same topology group (FRt1↔FRt2 etc.),
or between groups that are *not* alternative descriptions of one top. Even on the fixed
data, 17.4% of SRqq targets currently lose their b to an FR prediction — a free
recovery of several points of SRqq/event purity. Small change in
`extract_prediction`'s mask loop; could be a config flag
(e.g. `exclusive_decoding: "global" | "per_group"`).

**C. What is NOT recoverable data-side.** With only the h5, removing the double-booking
means deleting essentially all v6 SRqq targets (only 1 is uncontested) — i.e. v6 is
FR/FB-only for us until A or B lands. The v6 FR result (best FR in the campaign)
stands regardless.

## Status of our v6 copies (traindatavol `/data/spatop/delphes_v6/`)

- `deltaRfj` regenerated (validated encoding); original files on cms-ml untouched.
- Event 5,847,747's SRqqt2 invalidated (training-blocking).
- Trained model: `logs/spatop/69v6t2vw/` (gs8pex8v config, 10 epochs); eval preds in
  `fixed_eval/tt_hadronic_dp_v6blocks_fixedtest.h5` and `delphes_v6/eval/`.
  Evals of this checkpoint must pin `dprim7/SPANet@0983c4f` (pre-refactor code).
