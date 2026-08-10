"""Unit tests for src/models/chi2_baseline.py.

Contract enshrined here (per group decision):
  * b-tag partitioning: W candidates from non-b-tagged jets only, b from
    b-tagged jets only.
  * Greedy disjointness: top 1 is the global chi2 minimum; top 2 uses the
    remaining jets; the two never share a jet.
  * FB candidates are the leading n_tops (very)fat jets.
Deliberately NOT enshrined: the exact chi2 formulas / score values (only that
planted perfect tops score much better than junk, and scores are finite).
"""
import math

import h5py
import numpy as np
import pytest

from src.models.chi2_baseline import (
    boosted_chi2,
    load_boosted,
    load_jets,
    resolved_chi2,
    write_predictions,
)
from tests.conftest import JUNK_B, JUNK_LIGHT, TOP_MASS, ToyEvents, plant_top


def run_resolved(toys, path):
    with h5py.File(path, "r") as f:
        return resolved_chi2(load_jets(f), n_tops=2)


# ---------------------------------------------------------------------------
# known-answer recovery
# ---------------------------------------------------------------------------
def test_planted_top_recovered(tmp_path):
    toys = ToyEvents()
    toys.add(plant_top() + JUNK_LIGHT + JUNK_B)
    res = run_resolved(toys, toys.write(tmp_path / "t.h5"))

    assert res["FRt1_mask"][0]
    assert res["FRt1_b"][0] == 0
    assert {res["FRt1_q1"][0], res["FRt1_q2"][0]} == {1, 2}  # pair as a set
    assert res["FRt1_chi2"][0] < 1.0  # exact-mass plant => near-zero score
    # junk-only second top must score far worse
    assert not res["FRt2_mask"][0] or res["FRt2_chi2"][0] > res["FRt1_chi2"][0]


def test_two_planted_tops_disjoint(toy_two_top_file):
    toys, path = toy_two_top_file
    res = run_resolved(toys, path)
    for ev in range(6):
        used = [
            res[f"FRt{i}_{d}"][ev] for i in (1, 2) for d in ("b", "q1", "q2")
        ]
        assert res["FRt1_mask"][ev] and res["FRt2_mask"][ev]
        assert len(set(used)) == 6, "greedy tops must not share jets"
        # both planted triplets recovered (as sets, t1/t2 order free)
        triplets = {frozenset(used[:3]), frozenset(used[3:])}
        assert triplets == {frozenset({0, 1, 2}), frozenset({3, 4, 5})}
        # greedy order: first pick is the better (or equal) candidate
        assert res["FRt1_chi2"][ev] <= res["FRt2_chi2"][ev] + 1e-6


# ---------------------------------------------------------------------------
# b-tag partitioning (spec)
# ---------------------------------------------------------------------------
def test_btag_partitioning(tmp_path, toy_two_top_file):
    # perfect kinematic triplet but the "b" is NOT tagged: the only tagged jet
    # (index 3) MUST be chosen as b, and the W legs must come from the
    # untagged set. (No chi2-magnitude assertion: leftover pairings are
    # allowed to be kinematically good; the spec is the partitioning.)
    toys = ToyEvents()
    b, q1, q2 = plant_top()
    untagged_b = (b[0], b[1], b[2], b[3], False)
    toys.add([untagged_b, q1, q2] + JUNK_B)
    res = run_resolved(toys, toys.write(tmp_path / "t.h5"))
    assert res["FRt1_b"][0] == 3, "b must come from the b-tagged jet"
    assert {res["FRt1_q1"][0], res["FRt1_q2"][0]} <= {0, 1, 2}

    # property over the mixed toys: every reconstructed top respects the
    # partitioning
    mix, path = toy_two_top_file
    res2 = run_resolved(mix, path)
    for ev, jets in enumerate(mix.jets):
        for i in (1, 2):
            if res2[f"FRt{i}_mask"][ev]:
                assert jets[res2[f"FRt{i}_b"][ev]][4] is True
                assert jets[res2[f"FRt{i}_q1"][ev]][4] is False
                assert jets[res2[f"FRt{i}_q2"][ev]][4] is False


def test_no_btag_no_candidate(tmp_path):
    toys = ToyEvents()
    b, q1, q2 = plant_top()
    toys.add([(b[0], b[1], b[2], b[3], False), q1, q2] + JUNK_LIGHT)
    res = run_resolved(toys, toys.write(tmp_path / "t.h5"))
    assert not res["FRt1_mask"][0]
    assert res["FRt1_b"][0] == -1
    assert np.isinf(res["FRt1_chi2"][0])


def test_insufficient_jets(tmp_path):
    toys = ToyEvents()
    toys.add([(40.0, 0.0, 0.0, 5.0, True)])  # one b-jet, no light jets
    toys.add([(40.0, 0.0, 0.0, 5.0, False), (35.0, 0.1, 1.0, 4.0, False)])  # no b
    res = run_resolved(toys, toys.write(tmp_path / "t.h5"))
    assert not res["FRt1_mask"].any() and not res["FRt2_mask"].any()


# ---------------------------------------------------------------------------
# padded-jet exclusion (the bug fixed during consolidation)
# ---------------------------------------------------------------------------
def test_padded_jets_never_used(toy_two_top_file):
    toys, path = toy_two_top_file
    res = run_resolved(toys, path)
    n_real = np.array([len(j) for j in toys.jets])
    for i in (1, 2):
        for d in ("b", "q1", "q2"):
            idx = res[f"FRt{i}_{d}"]
            assert ((idx < n_real) | (idx == -1)).all(), (
                "assignment points at a padded slot"
            )


# ---------------------------------------------------------------------------
# FB arm: leading fat jets (spec); score form NOT asserted
# ---------------------------------------------------------------------------
def test_fb_leading_fatjets(toy_two_top_file):
    toys, path = toy_two_top_file
    with h5py.File(path, "r") as f:
        boo = boosted_chi2(load_boosted(f), n_tops=2)
    n_vfj = np.array([len(v) for v in toys.vfjs])
    assert (boo["FBt1_mask"] == (n_vfj >= 1)).all()
    assert (boo["FBt2_mask"] == (n_vfj >= 2)).all()
    assert (boo["FBt1_bqq"][n_vfj >= 1] == 0).all(), "FBt1 = leading fat jet"
    assert (boo["FBt2_bqq"][n_vfj >= 2] == 1).all(), "FBt2 = subleading fat jet"
    assert np.isfinite(boo["FBt1_chi2"][n_vfj >= 1]).all()


# ---------------------------------------------------------------------------
# loader format handling
# ---------------------------------------------------------------------------
def test_loader_phi_from_trig_and_uppercase_mask(tmp_path):
    toys = ToyEvents()
    toys.add(plant_top() + JUNK_LIGHT + JUNK_B)
    p1 = toys.write(tmp_path / "a.h5", jets_phi_as_trig=False)
    p2 = toys.write(tmp_path / "b.h5", jets_phi_as_trig=True)
    r1, r2 = run_resolved(toys, p1), run_resolved(toys, p2)
    for key in ("FRt1_b", "FRt1_q1", "FRt1_q2"):
        assert (r1[key] == r2[key]).all()


def test_loader_boosted_fallback(tmp_path):
    toys = ToyEvents()
    toys.add(plant_top(), vfjs=[(500.0, 0.0, 0.0, TOP_MASS)])
    path = toys.write(tmp_path / "t.h5", include_vbj=False)
    with h5py.File(path, "r") as f:
        fjets = load_boosted(f)  # falls back to (empty) BoostedJets
        boo = boosted_chi2(fjets, n_tops=2)
    assert not boo["FBt1_mask"].any()


def test_loader_missing_mask_uses_pt(tmp_path):
    toys = ToyEvents()
    toys.add(plant_top() + JUNK_LIGHT + JUNK_B)
    path = toys.write(tmp_path / "t.h5", jets_mask_key=None)
    res = run_resolved(toys, path)
    assert res["FRt1_mask"][0] and res["FRt1_b"][0] == 0


# ---------------------------------------------------------------------------
# output contract
# ---------------------------------------------------------------------------
def test_output_contract_and_rerun(toy_two_top_file, tmp_path):
    toys, path = toy_two_top_file
    out = tmp_path / "pred.h5"
    with h5py.File(path, "r") as f:
        res = resolved_chi2(load_jets(f), 2)
        boo = boosted_chi2(load_boosted(f), 2)
        write_predictions(out, f, res, boo, 2)
        write_predictions(out, f, res, boo, 2)  # re-run must not raise

    with h5py.File(out, "r") as f:
        for i in (1, 2):
            fr = f["TARGETS"][f"FRt{i}"]
            assert set(fr.keys()) == {"mask", "b", "q1", "q2", "pt", "chi2"}
            assert fr["mask"].dtype == bool
            assert np.issubdtype(fr["b"].dtype, np.integer)
            fb = f["TARGETS"][f"FBt{i}"]
            assert set(fb.keys()) == {"mask", "bqq", "pt", "chi2"}
            # chi2 routing: the analysis picks the chi2 code path only when
            # probability datasets are ABSENT
            assert "detection_probability" not in fr
            assert "assignment_probability" not in fr
        assert not any("SR" in k for k in f["TARGETS"]), (
            "SR targets would wrongly enable the analysis SR arms"
        )
        # INPUTS copied verbatim
        assert "INPUTS/Jets/pt" in f
