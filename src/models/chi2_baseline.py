"""Chi-squared baseline for SPAtop top reconstruction.

Consolidates the previous fully_resolved_baseline.py / fully_boosted_baseline.py
/ boosted_resolved_baseline.py scripts into one importable module + CLI that
produces a single prediction h5 consumable by src/analysis (the chi2 code path
of parse_resolved_w_target / parse_boosted_w_target).

Physics (unchanged from the tuned originals):
  Fully-resolved arm: for each top in turn, W candidates = all pairs of
    non-b-tagged jets, top candidates = W x b-tagged jets;
        chi2 = ((m_W - 80.37)/(0.1*80.37))^2 + ((m_top - 172.52)/(0.1*172.52))^2
    take the argmin, remove the used jets, repeat (greedy sequential).
    Reference cut for downstream selection: chi2 < 20.
  Fully-boosted arm: candidates = the leading n_tops (very)fat jets;
        "chi2" = |m_fj - 172.52|   (an absolute mass window, kept for
    consistency with the tuned cut)
    Reference cut: chi2 < 45.

Output contract (what src/analysis expects for a chi2 file -- triggers the
`except` branch because no detection_probability datasets are present):
  TARGETS/FRt{i}/{mask, b, q1, q2, pt, chi2}   (jet indices: Jets collection)
  TARGETS/FBt{i}/{mask, bqq, pt, chi2}         (fat-jet collection indices)
  INPUTS/* copied verbatim from the test file.
No SRqq/SRbq targets are written: the analysis skips its SR arms when a
prediction file has none (SR_condition), matching the original design.

Fixes vs the originals: jets are filtered by their validity MASK before
combinatorics (padded zero-pt jets used to enter the W pairing), output is
written atomically with 'w' (re-runs no longer crash on existing datasets),
nothing executes at import time, and both arms share one loader.

CLI:
    python -m src.models.chi2_baseline --test-file <test.h5> --out-file <pred.h5>
Optional QA (chi2 distributions, correct/incorrect split, ROC, accuracy
summary) with --plot-dir.
"""
import logging
import os

import awkward as ak
import click
import h5py
import numpy as np
import vector

vector.register_awkward()
logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("chi2_baseline")

TOP_MASS = 172.52  # GeV
W_MASS = 80.37  # GeV
RESOLVED_CHI2_CUT = 20  # reference values used by src/analysis; tuned by eye
BOOSTED_CHI2_CUT = 45  # on the chi2 distributions of the original scripts


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------
def _mask_of(group, n_events):
    for key in ("MASK", "mask"):
        if key in group:
            return np.asarray(group[key]).astype(bool)
    return None


def _phi_of(group, prefix=""):
    if f"{prefix}phi" in group:
        return np.asarray(group[f"{prefix}phi"])
    return np.arctan2(np.asarray(group[f"{prefix}sinphi"]),
                      np.asarray(group[f"{prefix}cosphi"]))


def load_jets(in_file):
    """Small-radius jets as a jagged Momentum4D array, padded slots removed.

    The per-event `index` field is the ORIGINAL slot index in the h5, which is
    what the prediction file must reference.
    """
    g = in_file["INPUTS"]["Jets"]
    pt = np.asarray(g["pt"])
    jets = ak.zip(
        {
            "pt": pt,
            "eta": np.asarray(g["eta"]),
            "phi": _phi_of(g),
            "mass": np.asarray(g["mass"]),
            "btag": np.asarray(g["btag"]).astype(bool),
            "index": ak.local_index(ak.Array(pt), axis=1),
        },
        with_name="Momentum4D",
    )
    mask = _mask_of(g, len(pt))
    if mask is None:
        mask = pt > 0
    return ak.drop_none(ak.mask(jets, ak.Array(mask)))


def load_boosted(in_file):
    """Boosted collection for the FB arm.

    Uses VeryBoostedJets (vfj_*) when present -- the collection the original
    boosted baseline and this branch's analysis are written against -- and
    falls back to BoostedJets (fj_*) for two-collection files.
    """
    if "VeryBoostedJets" in in_file["INPUTS"]:
        g, prefix = in_file["INPUTS"]["VeryBoostedJets"], "vfj_"
    else:
        g, prefix = in_file["INPUTS"]["BoostedJets"], "fj_"
    pt = np.asarray(g[f"{prefix}pt"])
    fjets = ak.zip(
        {
            "pt": pt,
            "eta": np.asarray(g[f"{prefix}eta"]),
            "phi": _phi_of(g, prefix),
            "mass": np.asarray(g[f"{prefix}mass"]),
            "index": ak.local_index(ak.Array(pt), axis=1),
        },
        with_name="Momentum4D",
    )
    mask = _mask_of(g, len(pt))
    if mask is None:
        mask = pt > 0
    return ak.drop_none(ak.mask(fjets, ak.Array(mask)))


# --------------------------------------------------------------------------
# the two chi2 arms
# --------------------------------------------------------------------------
def resolved_chi2(jets, n_tops=2):
    """Greedy sequential fully-resolved reconstruction.

    Returns {FRt{i}_{mask,b,q1,q2,pt,chi2}} with -1 / nan fills where no
    candidate exists (mask False).
    """
    bjets = jets[jets.btag]
    ljets = jets[~jets.btag]

    out = {}
    for i in range(1, n_tops + 1):
        w = ak.combinations(ljets, 2, axis=1, fields=["j1", "j2"])
        w = ak.with_field(w, (w.j1 + w.j2).mass, "w_mass")

        t = ak.cartesian({"w": w, "b": bjets}, axis=1)
        top_p4 = t.w.j1 + t.w.j2 + t.b
        t = ak.with_field(t, top_p4.mass, "top_mass")
        t = ak.with_field(t, top_p4.pt, "top_pt")

        chi2 = (
            ((t.w.w_mass - W_MASS) / (0.1 * W_MASS)) ** 2
            + ((t.top_mass - TOP_MASS) / (0.1 * TOP_MASS)) ** 2
        )
        best_idx = ak.argmin(chi2, axis=1)
        best = ak.firsts(t[ak.local_index(t) == best_idx])
        best_chi2 = ak.firsts(chi2[ak.local_index(chi2) == best_idx])

        found = ~ak.is_none(best)
        out[f"FRt{i}_mask"] = ak.to_numpy(found)
        out[f"FRt{i}_b"] = ak.to_numpy(ak.fill_none(best.b.index, -1)).astype(np.int64)
        out[f"FRt{i}_q1"] = ak.to_numpy(ak.fill_none(best.w.j1.index, -1)).astype(np.int64)
        out[f"FRt{i}_q2"] = ak.to_numpy(ak.fill_none(best.w.j2.index, -1)).astype(np.int64)
        out[f"FRt{i}_pt"] = ak.to_numpy(ak.fill_none(best.top_pt, -1.0)).astype(np.float32)
        out[f"FRt{i}_chi2"] = ak.to_numpy(ak.fill_none(best_chi2, np.inf)).astype(np.float32)

        # remove the used jets before reconstructing the next top
        bjets = bjets[bjets.index != ak.fill_none(best.b.index, -1)]
        ljets = ljets[
            (ljets.index != ak.fill_none(best.w.j1.index, -1))
            & (ljets.index != ak.fill_none(best.w.j2.index, -1))
        ]
    return out


def boosted_chi2(fjets, n_tops=2):
    """Fully-boosted arm: the leading n_tops (very)fat jets are the candidates,
    scored by |m - m_top| (kept from the tuned original)."""
    out = {}
    for i in range(1, n_tops + 1):
        slot = ak.firsts(fjets[ak.local_index(fjets) == i - 1])
        found = ~ak.is_none(slot)
        out[f"FBt{i}_mask"] = ak.to_numpy(found)
        out[f"FBt{i}_bqq"] = ak.to_numpy(ak.fill_none(slot.index, -1)).astype(np.int64)
        out[f"FBt{i}_pt"] = ak.to_numpy(ak.fill_none(slot.pt, -1.0)).astype(np.float32)
        out[f"FBt{i}_chi2"] = ak.to_numpy(
            ak.fill_none(abs(slot.mass - TOP_MASS), np.inf)
        ).astype(np.float32)
    return out


# --------------------------------------------------------------------------
# output
# --------------------------------------------------------------------------
def write_predictions(out_file, in_file, resolved, boosted, n_tops=2):
    """Single atomic writer: INPUTS copied verbatim + chi2-contract TARGETS."""
    with h5py.File(out_file, "w") as f:
        for coll_name, coll in in_file["INPUTS"].items():
            for feat_name, feat in coll.items():
                f.create_dataset(f"INPUTS/{coll_name}/{feat_name}", data=np.asarray(feat))
        for i in range(1, n_tops + 1):
            for key in ("mask", "b", "q1", "q2", "pt", "chi2"):
                f.create_dataset(f"TARGETS/FRt{i}/{key}", data=resolved[f"FRt{i}_{key}"])
            for key in ("mask", "bqq", "pt", "chi2"):
                f.create_dataset(f"TARGETS/FBt{i}/{key}", data=boosted[f"FBt{i}_{key}"])
    log.info("wrote %s", out_file)


# --------------------------------------------------------------------------
# optional QA against truth targets
# --------------------------------------------------------------------------
def _truth(in_file, particle, daughter):
    g = in_file["TARGETS"][particle]
    for key in (daughter, daughter.upper()):
        if key in g:
            return np.asarray(g[key])
    raise KeyError(f"TARGETS/{particle}/{daughter}")


def _truth_mask(in_file, particle):
    g = in_file["TARGETS"][particle]
    for key in ("mask", "MASK"):
        if key in g:
            return np.asarray(g[key]).astype(bool)
    # fall back to daughter validity
    first = [k for k in g.keys() if k not in ("pt",)][0]
    return np.asarray(g[first]) >= 0


def resolved_correct(in_file, res, i, n_tops=2):
    """Swap-aware, either-truth-slot match for predicted FRt{i}."""
    pred_b, pred_q1, pred_q2 = res[f"FRt{i}_b"], res[f"FRt{i}_q1"], res[f"FRt{i}_q2"]
    correct = np.zeros(len(pred_b), bool)
    for j in range(1, n_tops + 1):
        tb = _truth(in_file, f"FRt{j}", "b")
        tq1 = _truth(in_file, f"FRt{j}", "q1")
        tq2 = _truth(in_file, f"FRt{j}", "q2")
        tm = _truth_mask(in_file, f"FRt{j}")
        correct |= (
            tm
            & (pred_b == tb)
            & (((pred_q1 == tq1) & (pred_q2 == tq2)) | ((pred_q1 == tq2) & (pred_q2 == tq1)))
        )
    return correct


def boosted_correct(in_file, boo, i, n_tops=2):
    pred = boo[f"FBt{i}_bqq"]
    correct = np.zeros(len(pred), bool)
    for j in range(1, n_tops + 1):
        correct |= _truth_mask(in_file, f"FBt{j}") & (pred == _truth(in_file, f"FBt{j}", "bqq"))
    return correct


def qa_report(in_file, resolved, boosted, n_tops, plot_dir,
              resolved_cut=RESOLVED_CHI2_CUT, boosted_cut=BOOSTED_CHI2_CUT):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs(plot_dir, exist_ok=True)
    log.info("== chi2 baseline QA (cuts: resolved < %s, boosted < %s) ==",
             resolved_cut, boosted_cut)

    for arm, data, correct_fn, cut in (
        ("resolved", resolved, resolved_correct, resolved_cut),
        ("boosted", boosted, boosted_correct, boosted_cut),
    ):
        prefix = "FRt" if arm == "resolved" else "FBt"
        fig_h, ax_h = plt.subplots(1, n_tops, figsize=(6 * n_tops, 4.2))
        fig_r, ax_r = plt.subplots(figsize=(6.2, 5.4))
        ax_h = np.atleast_1d(ax_h)
        for i in range(1, n_tops + 1):
            mask = data[f"{prefix}{i}_mask"]
            chi2 = data[f"{prefix}{i}_chi2"]
            correct = correct_fn(in_file, data, i, n_tops)
            sel = mask & (chi2 < cut)
            n_cand, n_sel = mask.sum(), sel.sum()
            pur_all = correct[mask].mean() if n_cand else float("nan")
            pur_sel = correct[sel].mean() if n_sel else float("nan")
            log.info(
                "%s%d: candidates %d | pass cut %d (%.1f%%) | "
                "purity all %.1f%% | purity after cut %.1f%%",
                prefix, i, n_cand, n_sel, 100 * n_sel / max(n_cand, 1),
                100 * pur_all, 100 * pur_sel,
            )
            bins = np.linspace(0, np.nanquantile(chi2[mask], 0.99), 60)
            ax_h[i - 1].hist(chi2[mask & correct], bins=bins, alpha=0.6, label="correct")
            ax_h[i - 1].hist(chi2[mask & ~correct], bins=bins, alpha=0.6, label="incorrect")
            ax_h[i - 1].axvline(cut, color="k", ls=":", lw=1)
            ax_h[i - 1].set(yscale="log", xlabel=f"chi2 ({prefix}{i})")
            ax_h[i - 1].legend()

            # ROC: rank candidates by 1/chi2
            order = np.argsort(chi2[mask])
            lab = correct[mask][order]
            tpr = np.cumsum(lab) / max(lab.sum(), 1)
            fpr = np.cumsum(~lab) / max((~lab).sum(), 1)
            auc = np.trapezoid(tpr, fpr) if hasattr(np, "trapezoid") else np.trapz(tpr, fpr)
            ax_r.plot(fpr, tpr, label=f"{prefix}{i} (AUC = {auc:.3f})")
        ax_r.plot([0, 1], [0, 1], "k--", lw=1)
        ax_r.set(xlabel="false positive rate", ylabel="true positive rate",
                 title=f"chi2 as a candidate ranking -- {arm}")
        ax_r.legend()
        fig_h.tight_layout()
        fig_r.tight_layout()
        fig_h.savefig(os.path.join(plot_dir, f"chi2_{arm}_distributions.pdf"))
        fig_r.savefig(os.path.join(plot_dir, f"chi2_{arm}_roc.pdf"))
        plt.close(fig_h)
        plt.close(fig_r)
    log.info("QA plots in %s", plot_dir)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
@click.command()
@click.option("--test-file", required=True, help="Input test h5 (truth + inputs).")
@click.option("--out-file", required=True, help="Output prediction h5.")
@click.option("--n-tops", default=2, show_default=True, help="Tops per event.")
@click.option("--plot-dir", default=None,
              help="If set, also produce QA plots + accuracy summary here.")
@click.option("--resolved-cut", default=RESOLVED_CHI2_CUT, show_default=True,
              help="Reference resolved chi2 cut (QA only; the analysis applies its own).")
@click.option("--boosted-cut", default=BOOSTED_CHI2_CUT, show_default=True,
              help="Reference boosted chi2 cut (QA only).")
def main(test_file, out_file, n_tops, plot_dir, resolved_cut, boosted_cut):
    with h5py.File(test_file, "r") as f:
        jets = load_jets(f)
        fjets = load_boosted(f)
        log.info("loaded %d events (%s boosted collection)",
                 len(jets), "VeryBoostedJets" if "VeryBoostedJets" in f["INPUTS"] else "BoostedJets")

        resolved = resolved_chi2(jets, n_tops)
        boosted = boosted_chi2(fjets, n_tops)
        write_predictions(out_file, f, resolved, boosted, n_tops)

        if plot_dir:
            qa_report(f, resolved, boosted, n_tops, plot_dir, resolved_cut, boosted_cut)


if __name__ == "__main__":
    main()
