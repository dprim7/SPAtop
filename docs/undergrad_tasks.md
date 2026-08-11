# Undergrad task ladder: the chi2 baseline, and on to four tops

You wrote the first version of the chi2 baseline. It has since been
consolidated into one tested module (`src/models/chi2_baseline.py`) with a
test suite that runs automatically on every pull request. That module is
**your area** — this document is a ladder of six tasks in it, ordered so each
one teaches what the next one needs.

Every task here runs on a laptop or the login node. None of them need cluster
or GPU accounts.

Work through them in order. Each is a few days at ~5 h/week. Ask questions
early and often — being stuck for a week is worse than asking a question that
turns out to be easy.

---

## Setup (once)

**1. Get the code.**

```bash
git clone https://github.com/dprim7/SPAtop.git
cd SPAtop
```

**2. Make an environment** (python ≥ 3.9; conda/micromamba/venv all fine):

```bash
pip install numpy h5py awkward vector click matplotlib pytest hist scipy numba
```

**3. Get the data.** Nothing is committed to git — data files are downloaded.
These are public HTTPS links, no account needed:

```bash
mkdir -p data/delphes
# the test set with truth labels (~144 MB)
curl -o data/delphes/tt_hadronic_testing_fixed.h5 \
  https://traindatavol.nrp-nautilus.io/spatop/tpm70_wpm30_FB350_fixed_test/all_merged.h5
# a SPANet prediction on that same test set, for comparison (task 3)
curl -o data/delphes/spanet_blocks_pred.h5 \
  https://traindatavol.nrp-nautilus.io/spatop/tpm70_wpm30_FB350_fixed_eval/tt_hadronic_dp_swpbest_blocks.h5
```

**4. Check everything works:**

```bash
pytest tests/ -q          # should print "14 passed"
```

If that passes, you have a working setup.

## How we work

- **Never commit to a shared branch.** Make your own:
  `git checkout -b yourname/short-description`.
- **One pull request per task.** Small PRs get reviewed fast; big ones sit.
- **CI must be green.** Opening a PR runs `pytest tests/` automatically
  (`.github/workflows/tests.yml`). A red X means something broke — read the
  log, it names the failing test.
- **Notebooks**: clear the outputs before committing (`Kernel → Restart &
  Clear Output`), otherwise the diff is thousands of lines of base64 images.

## Where things are

| What | Where |
|---|---|
| The baseline module | `src/models/chi2_baseline.py` |
| How to run it | `docs/chi2_baseline.md` ← **read this first** |
| Notebook version | `notebooks/chi2_baseline.ipynb` |
| Tests | `tests/test_chi2_baseline.py`, `tests/test_roundtrip_analysis.py` |
| Toy-event builder used by tests | `tests/conftest.py` |
| Group analysis / plots | `src/analysis/` |

## A little physics vocabulary

A top quark decays to a b quark and a W boson; the W decays to two more
quarks. So one top ≈ three quarks ≈ (usually) three jets in the detector. Our
events have **two** tops, all decaying to quarks ("all-hadronic").

Depending on how fast the top is moving, its three quarks land in the detector
differently, which is why there are three "topologies":

- **FR** (fully resolved) — three separate small jets. Our job: pick which
  three, out of ~10. This is the hard combinatorial problem.
- **SRqq** (semi-resolved) — the two W quarks merged into one big "fat" jet,
  the b is still separate. Pick 1 small jet + 1 fat jet.
- **FB** (fully boosted) — the whole top is inside one fat jet. Just pick the
  fat jet.

**Jet assignment** = deciding which jets came from which top. That is all
this code does. Two ways to score how well we did:

- **Purity** — of the tops we claimed, what fraction are real?
- **Efficiency** — of the real tops, what fraction did we find?

The chi2 baseline is the classical, non-machine-learning way to do the
assignment: try combinations, keep the one whose masses look most like a real
W (80.4 GeV) and top (172.5 GeV). It is the reference that the neural network
(SPANet) has to beat.

---

# The ladder

## Task 1 — Run it all, then delete the old scripts

*Learn the repo and the PR flow, with no risk of breaking anything.*

**Do:**
1. Work through `docs/chi2_baseline.md` end to end: run the CLI on the test
   file you downloaded, with `--plot-dir plots/chi2_qa`, and look at the four
   QA plots it makes.
2. Run the notebook (`notebooks/chi2_baseline.ipynb`) top to bottom.
3. Read `tests/test_chi2_baseline.py`. For each test, write yourself one
   sentence on what it protects.
4. Open a PR deleting the three superseded scripts:
   `src/models/fully_resolved_baseline.py`,
   `src/models/fully_boosted_baseline.py`,
   `src/models/boosted_resolved_baseline.py`.

**Why deleting is safe:** the consolidated module was checked assignment-by-
assignment against those exact scripts on 187,348 events. Every difference was
traced to a specific bug fix; there were no unexplained differences. Ask for
the fidelity report if you want to see the evidence.

**Done when:** PR merged with CI green, and you can explain what the phrase
"the tests deliberately do not pin the chi2 formulas" means.

## Task 2 — Retune the chi2 cuts on the current data

*Own the QA workflow, and produce your first result the group will use.*

The baseline scores each candidate with a chi2. Downstream, only candidates
below a cut are kept: **20** for resolved, **45** for boosted. Those numbers
were picked by eye, years ago, on a dataset we no longer use.

Here is what those cuts do on the *current* test file (this is the QA printout
from Task 1 — you will reproduce it):

```
FRt1: candidates 166064 | pass cut 145595 (87.7%) | purity all 24.7% | purity after cut 28.1%
FRt2: candidates  85266 | pass cut  30914 (36.3%) | purity all  8.3% | purity after cut 22.6%
FBt1: candidates 129027 | pass cut  14285 (11.1%) | purity all  8.8% | purity after cut 65.8%
FBt2: candidates  84567 | pass cut   5358 ( 6.3%) | purity all  4.8% | purity after cut 59.8%
```

Read those two middle columns against each other. The boosted cut throws away
89% of candidates and lifts purity from 9% to 66% — it is doing real work. The
resolved cut keeps 88% of candidates and lifts purity by 3 points — it is
close to doing nothing at all. **A cut that keeps almost everything is not a
cut.** That is the thing to fix.

**Do:**
1. Run with `--plot-dir` on the current test file. The QA plots show the chi2
   distribution split into *correct* and *incorrect* assignments (it can tell,
   because the test file has truth labels).
2. Pick better cuts using a criterion you can state in one sentence — e.g.
   "the cut where purity reaches 80%", or "where we lose more correct than
   incorrect candidates". Any defensible rule is fine; an undefended number
   is not.
3. Write the new cuts and your reasoning into `docs/chi2_baseline.md`, and
   update the defaults in `src/models/chi2_baseline.py`.

**Hint:** the QA printout already gives you purity before and after the cut,
per top. You may want to loop over candidate cut values and plot purity and
efficiency against the cut — that plot is the deliverable.

**Note:** downstream code takes the cuts from a plot tag of the form
`chi2_<boostedcut>_<resolvedcut>` (e.g. `chi2_45_20`), so changing cuts needs
no code changes elsewhere.

**Done when:** new cuts justified in the docs, plots committed, CI green.
(The tests will not fight you: they check structure, not cut values.)

## Task 3 — How far behind SPANet is the baseline?

*Connect your work to the group's headline numbers.*

The group compares models with a table of per-topology accuracy and event
purity. The chi2 baseline is not in that table yet. Put it there.

**Do:** run the baseline on the test file, then compute, for the chi2
predictions: for each topology (FR / SRqq / FB), the fraction of true tops
that were correctly reconstructed; and the fraction of events where
*everything* present was right. Compare against the SPANet prediction file you
downloaded.

**Two conventions that will bite you if nobody warns you** (they cost a
previous student-week to find):

1. In prediction files, indices for fat-jet daughters are counted from the
   *start of the combined jet list*, but truth indices are counted within
   their own collection. So before comparing a fat-jet index, subtract the
   number of small-jet slots (10).
2. "Top 1" and "top 2" are just slot labels — a model finding both tops but
   in the other order is completely correct. Compare **sets**, not slots.
   Ignoring this makes models look far worse than they are.

**Done when:** a small table (markdown or CSV) with a chi2 row beside the
SPANet rows, plus a paragraph: where is chi2 closest to the network, where is
it furthest, and does that make physical sense?

## Task 4 — Add the semi-resolved arm

*Your first real algorithm design.*

The baseline handles FR and FB but has no SRqq arm — `docs/chi2_baseline.md`
lists this under "Known limitations". Add it.

**Design questions to answer before coding** (write them down, discuss with a
mentor):
- Candidates are (b-tagged small jet) × (fat jet). What is the chi2? The fat
  jet should have the W mass; the jet+fatjet system should have the top mass.
- Does an SRqq top compete with FR and FB tops for the same jets, or is each
  arm independent? (Look at how the FR arm removes its jets before finding
  the next top — `src/models/chi2_baseline.py`, `resolved_chi2`.)

**Do:** implement it next to `resolved_chi2`/`boosted_chi2`, extend
`write_predictions`, extend the toy events in `tests/conftest.py` (they
already build fat jets), and add tests in the style of the existing ones —
including one where you plant an SRqq top with exact masses and check it's
found.

**Stretch (with a mentor):** the group's analysis has no chi2 path for SRqq in
`src/analysis/semi_resolved.py`. Adding one lets your SRqq tops appear in the
official purity/efficiency plots.

**Done when:** tests green including new SRqq known-answer toys, and the
Task 3 table gains an SRqq row for chi2.

## Task 5 — Is greedy good enough?

*A small, genuinely open research question.*

The baseline is **greedy**: it finds the single best top, removes those jets,
then finds the best top from what's left. That is not guaranteed to be the
best *pair* of tops — maybe a slightly worse first top allows a much better
second one.

**Do:**
1. Implement the exhaustive alternative: score every pair of non-overlapping
   top candidates and take the best total.
2. On the test file, measure: how often do greedy and exhaustive disagree? And
   when they disagree, which one matches truth more often?
3. Time them both.

**Done when:** a table of those numbers plus a recommendation — keep greedy,
or switch, and why. If exhaustive is better but too slow, say so and quantify
the trade-off; that is a real result either way.

## Task 6 — Four tops

*Get ready for where the group is going next.*

The group is expanding to **tttt** — four top quarks in one event. The
combinatorics get dramatically worse: choosing three jets out of ten for two
tops is thousands of possibilities; for four tops out of ~16 jets it is
hundreds of millions. Nobody knows yet how well a greedy chi2 does there.

The functions already take an `n_tops` argument, so the code may work at
`--n-tops 4` — but "may work" is not "is correct".

**Do:**
1. Extend the toy-event builder (`tests/conftest.py`) to plant **four** exact
   tops in one event.
2. Write tests at four tops: all four found, no two tops sharing a jet, b-tag
   rules still respected.
3. Using your exhaustive code from Task 5 on these toys (small enough to brute
   force), measure how much greedy loses at four tops versus two.

**Done when:** `--n-tops 4` is demonstrably correct on toys, plus a short note
on how greedy degrades with more tops. When the first real four-top sample is
produced, your baseline runs on it immediately — quite possibly the first
reconstruction result anyone has on that sample.

---

## Later, once you have cluster accounts

Running SPANet trainings and evaluations, repeat-with-different-seeds studies,
and helping validate new datasets. All of that needs Nautilus and Weights &
Biases accounts — ask when you get to Task 5 or so.
