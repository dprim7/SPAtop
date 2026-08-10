"""Integration: chi2 baseline output through the group analysis (chi2 path).

Builds the toy test file, runs the full baseline via its CLI, then feeds the
prediction into src.analysis.plot.calc_pur_eff exactly as
reports/run_analysis.py does. Asserts the chi2 code path engages (no
probability datasets -> except-branch), the SR arms stay off, and the
purity/efficiency results are populated and finite where the toys have
statistics. No golden numbers are pinned.
"""
import h5py
import numpy as np
import pytest
from click.testing import CliRunner

from src.models.chi2_baseline import main as chi2_cli

BINS = {
    "FR": np.arange(0, 300, 50),
    "SRqq": np.arange(100, 400, 100),
    "SRbq": np.arange(100, 400, 100),
    "FB": np.arange(200, 1000, 200),
    "all": np.arange(0, 1000, 200),
}


@pytest.fixture
def pred_file(toy_two_top_file, tmp_path):
    _, test_path = toy_two_top_file
    out = tmp_path / "chi2_pred.h5"
    result = CliRunner().invoke(
        chi2_cli,
        ["--test-file", str(test_path), "--out-file", str(out)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    return test_path, out


def test_cli_end_to_end(pred_file):
    _, out = pred_file
    with h5py.File(out, "r") as f:
        assert f["TARGETS/FRt1/mask"][...].sum() >= 9  # all planted events found


def test_analysis_roundtrip(pred_file):
    from src.analysis.plot import calc_pur_eff

    test_path, out = pred_file
    results, sr_condition = calc_pur_eff(
        str(test_path), str(out), BINS, chi2_cuts=[45, 20]
    )

    assert not sr_condition, "chi2 file must not trigger the SR arms"

    # resolved and boosted purities/efficiencies exist and contain finite,
    # sane values in at least one populated bin
    for key in ("pur_r", "eff_r", "pur_b", "eff_b", "pur_m", "eff_m"):
        assert results[key] is not None, f"{key} missing"
        vals = np.asarray(results[key], dtype=float)
        finite = vals[np.isfinite(vals)]
        assert len(finite) > 0, f"{key} has no populated bins"
        assert ((finite >= 0) & (finite <= 1)).all(), f"{key} outside [0,1]"

    # the toys plant exact tops: the populated resolved-purity bins should be
    # excellent (well above 0.5) -- a loose physics sanity, not a golden value
    pur_r = np.asarray(results["pur_r"], dtype=float)
    assert np.nanmax(pur_r) > 0.5


def test_qa_report_runs(toy_two_top_file, tmp_path):
    """QA is optional but should not rot: smoke-run it on the toys."""
    from src.models.chi2_baseline import (
        boosted_chi2,
        load_boosted,
        load_jets,
        qa_report,
        resolved_chi2,
    )

    _, test_path = toy_two_top_file
    plot_dir = tmp_path / "qa"
    with h5py.File(test_path, "r") as f:
        res = resolved_chi2(load_jets(f), 2)
        boo = boosted_chi2(load_boosted(f), 2)
        qa_report(f, res, boo, 2, str(plot_dir))
    produced = {p.name for p in plot_dir.iterdir()}
    assert {
        "chi2_resolved_distributions.pdf",
        "chi2_resolved_roc.pdf",
        "chi2_boosted_distributions.pdf",
        "chi2_boosted_roc.pdf",
    } <= produced
