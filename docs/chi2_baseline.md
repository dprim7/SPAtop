# Chi-squared baseline: how to run it

The chi2 baseline is the classical (non-ML) reference for SPAtop: it assigns
jets to top quarks by scanning jet combinations and minimizing a mass-based
chi2, and writes a prediction file that plugs into the same analysis and
plots as the SPANet predictions. Use it whenever you need the "how much does
the network actually buy us" comparison.

It lives in one module: `src/models/chi2_baseline.py`
(it replaces the older `fully_resolved_baseline.py`,
`fully_boosted_baseline.py` and `boosted_resolved_baseline.py` scripts,
which are kept for reference but should not be used).

---

## 1. Quick start

From the repository root, with the environment from the main README
(additionally needs nothing beyond the standard stack:
`numpy h5py awkward vector click matplotlib`):

```bash
python -m src.models.chi2_baseline \
    --test-file data/delphes/v4/tt_hadronic_testing_SLIMMED.h5 \
    --out-file  data/delphes/v4/tt_hadronic_chi2_baseline.h5 \
    --plot-dir  plots/chi2_qa        # optional QA plots + accuracy printout
```

Runtime is a few seconds per 100k events. `--n-tops` defaults to 2.
Re-running overwrites the output cleanly (no need to delete it first).

Prefer notebooks? `notebooks/chi2_baseline.ipynb` wraps the same functions:
set the paths in the first cell and run top to bottom.

## 2. What goes in

Any SPAtop test h5 with `INPUTS/Jets` (pt, eta, phi *or* sinphi/cosphi,
mass, btag) works. For the fully-boosted arm the module uses
`INPUTS/VeryBoostedJets` when present (the v4-era format the analysis in
this branch targets) and falls back to `INPUTS/BoostedJets` otherwise.
Padded jet slots are removed using the `MASK`/`mask` dataset (or `pt > 0`
if the file has none).

The canonical v4 test file lives on Thomas's storage:
`/storage/af/user/tsievert/topNet/SPAtop/data/delphes/v4/tt_hadronic_testing_SLIMMED.h5`.

## 3. What it computes (physics definitions)

**Fully-resolved arm** (targets `FRt1`, `FRt2`): for each top in turn,

* W candidates = all pairs of **non-b-tagged** jets,
* top candidates = each W candidate x each **b-tagged** jet,
* score: `chi2 = ((m_W - 80.37)/(0.1*80.37))^2 + ((m_top - 172.52)/(0.1*172.52))^2`,
* the argmin wins; its three jets are removed and the procedure repeats for
  the next top (greedy sequential -- the two tops never share a jet).

**Fully-boosted arm** (targets `FBt1`, `FBt2`): the candidates are the
pt-leading (very)fat jets, one per top, scored by `|m_fj - 172.52|`
(an absolute mass window rather than a normalized chi2 -- kept because the
downstream cut is tuned to that scale).

There is intentionally **no semi-resolved arm**: the analysis skips its SR
stages automatically for prediction files without SR targets.

Reference selection cuts, applied downstream by the analysis (not by the
baseline itself): resolved `chi2 < 20`, boosted `chi2 < 45`. Both were tuned
by eye on the chi2 distributions; regenerate those with `--plot-dir` if the
data changes.

## 4. What comes out

The prediction h5 contains the INPUTS copied verbatim plus, per top `i`:

```
TARGETS/FRt{i}/{mask, b, q1, q2, pt, chi2}
TARGETS/FBt{i}/{mask, bqq, pt, chi2}
```

* `mask` -- a candidate was found;
* jet indices are **per-collection** slot indices into the test file
  (`b/q1/q2` into Jets, `bqq` into the (very)fat-jet collection); `-1` when
  no candidate;
* `chi2` -- the candidate's score (`inf` when no candidate);
* there are deliberately **no** `detection_probability` /
  `assignment_probability` datasets: their absence is what routes
  `src/analysis` into its chi2 code path. Do not add them.

## 5. Feeding it to the group plots

Exactly like `reports/run_analysis.py`; the only special thing is the tag
convention -- `chi2_<boostedcut>_<resolvedcut>`:

```python
from src.analysis.plot import plot_pur_eff_w_dict

plot_pur_eff_w_dict(
    {
        "SPAtop":     "path/to/tt_hadronic_predict.h5",
        "chi2_45_20": "path/to/tt_hadronic_chi2_baseline.h5",
    },
    "path/to/tt_hadronic_testing_SLIMMED.h5",  # target_path
    save_path="plots", proj_name="SPAtop",
)
```

A bare `"chi2"` tag falls back to the default cuts `[45, 20]`.

## 6. QA mode

`--plot-dir <dir>` additionally writes, per arm:

* `chi2_*_distributions.pdf` -- chi2 histograms split into correct vs
  incorrect assignments (against the truth targets in the test file), with
  the reference cut marked. This is the plot the cuts were tuned on.
* `chi2_*_roc.pdf` -- chi2 as a candidate-quality ranking.

and prints a per-top summary: candidates found, fraction passing the cut,
assignment purity before/after the cut.

## 7. Tests

```bash
pip install pytest hist scipy   # on top of the standard stack
pytest tests/ -q
```

The suite runs on synthetic events with exactly constructed W/top masses
(no data files needed) and also pushes a baseline file through the full
analysis (`calc_pur_eff`) as an integration test. CI runs it on every
push/PR (`.github/workflows/tests.yml`). If you change the baseline's
behavior on purpose, the tests define which properties are contract:
b-tag partitioning, greedy disjointness, FB = leading fat jets, and the
output format above. The chi2 formulas themselves are not pinned by tests
and can be retuned.

## 8. Known limitations (by design, for now)

* Greedy assignment is not globally optimal across two tops.
* No semi-resolved reconstruction.
* The resolved arm requires at least one b-tagged jet; events without one
  get no FR candidate.
* The FB score is an unnormalized mass window.
