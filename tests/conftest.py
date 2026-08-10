"""Shared toy-event machinery for the chi2 baseline tests.

Everything is synthetic and self-contained: no data files, no volume access.
Toy events are constructed with explicit kinematics so the correct assignment
is known by construction:

  * `plant_top(phi0)` returns three jets (b, q1, q2), all at eta=0, whose
    invariant masses reproduce the W and top masses exactly (massless-jet
    algebra: m^2 = 2 pt1 pt2 (cosh(deta) - cos(dphi))), so the planted triplet
    is the unambiguous chi2 minimum against any junk we add.
  * `ToyEvents` collects per-event jet/fat-jet lists and truth targets and
    writes a v4-style h5 (Jets + BoostedJets + VeryBoostedJets, lowercase
    target `mask`) -- the format the branch's src/analysis consumes.
"""
import math

import h5py
import numpy as np
import pytest

TOP_MASS = 172.52
W_MASS = 80.37

N_JET_SLOTS = 10
N_FJ_SLOTS = 3
N_VFJ_SLOTS = 3


def plant_top(phi0=0.0, pt1=60.0, pt2=60.0, ptb=70.0):
    """Three massless jets at eta=0 forming an exact W and top.

    Returns [b, q1, q2] as (pt, eta, phi, mass, btag) tuples.
    """
    # m(q1,q2) = W_MASS:  2 pt1 pt2 (1 - cos dphi) = mW^2
    dphi_w = math.acos(1 - W_MASS**2 / (2 * pt1 * pt2))
    # m(q1,q2,b) = TOP_MASS: solve for the b phi via sum-to-product
    extra = TOP_MASS**2 - W_MASS**2
    # 2 ptb [pt1 (1-cos(x)) + pt2 (1-cos(x - dphi_w))] = extra, x = phi_b - phi_q1
    target = (pt1 + pt2) - extra / (2 * ptb)
    amp = math.sqrt(pt1**2 + pt2**2 + 2 * pt1 * pt2 * math.cos(dphi_w))
    shift = math.atan2(pt2 * math.sin(dphi_w), pt1 + pt2 * math.cos(dphi_w))
    x = math.acos(max(-1.0, min(1.0, target / amp))) + shift
    return [
        (ptb, 0.0, phi0 + x, 0.0, True),   # b
        (pt1, 0.0, phi0, 0.0, False),      # q1
        (pt2, 0.0, phi0 + dphi_w, 0.0, False),  # q2
    ]


JUNK_LIGHT = [(25.0, 1.8, -2.0, 40.0, False), (22.0, -1.5, 2.6, 35.0, False)]
JUNK_B = [(24.0, 2.1, -2.8, 30.0, True)]


class ToyEvents:
    def __init__(self):
        self.jets = []       # per event: list of (pt, eta, phi, mass, btag)
        self.vfjs = []       # per event: list of (pt, eta, phi, mass)
        self.truth = []      # per event: dict of targets

    def add(self, jets, vfjs=(), truth=None):
        assert len(jets) <= N_JET_SLOTS and len(vfjs) <= N_VFJ_SLOTS
        self.jets.append(list(jets))
        self.vfjs.append(list(vfjs))
        self.truth.append(truth or {})

    # ------------------------------------------------------------------
    def _padded(self, rows, n_slots, n_feat):
        out = np.zeros((len(rows), n_slots, n_feat), dtype=np.float64)
        mask = np.zeros((len(rows), n_slots), dtype=bool)
        for i, row in enumerate(rows):
            for j, feats in enumerate(row):
                out[i, j, : len(feats)] = feats
                mask[i, j] = True
        return out, mask

    def write(self, path, jets_mask_key="MASK", jets_phi_as_trig=False,
              include_vbj=True):
        """Write the toy h5. Options exercise the loader's format handling."""
        jarr, jmask = self._padded(self.jets, N_JET_SLOTS, 5)
        varr, vmask = self._padded(self.vfjs, N_VFJ_SLOTS, 4)
        n = len(self.jets)

        with h5py.File(path, "w") as f:
            g = f.create_group("INPUTS/Jets")
            g.create_dataset("pt", data=jarr[:, :, 0])
            g.create_dataset("eta", data=jarr[:, :, 1])
            if jets_phi_as_trig:
                g.create_dataset("sinphi", data=np.sin(jarr[:, :, 2]))
                g.create_dataset("cosphi", data=np.cos(jarr[:, :, 2]))
            else:
                g.create_dataset("phi", data=jarr[:, :, 2])
            g.create_dataset("mass", data=jarr[:, :, 3])
            g.create_dataset("btag", data=jarr[:, :, 4].astype(bool))
            if jets_mask_key:
                g.create_dataset(jets_mask_key, data=jmask)

            # BoostedJets: minimal but complete enough for loaders/analysis
            b = f.create_group("INPUTS/BoostedJets")
            zeros2 = np.zeros((n, N_FJ_SLOTS))
            for name in ("fj_pt", "fj_eta", "fj_phi", "fj_mass"):
                b.create_dataset(name, data=zeros2)
            b.create_dataset("MASK", data=np.zeros((n, N_FJ_SLOTS), bool))

            if include_vbj:
                v = f.create_group("INPUTS/VeryBoostedJets")
                v.create_dataset("vfj_pt", data=varr[:, :, 0])
                v.create_dataset("vfj_eta", data=varr[:, :, 1])
                v.create_dataset("vfj_phi", data=varr[:, :, 2])
                v.create_dataset("vfj_mass", data=varr[:, :, 3])
                v.create_dataset("MASK", data=vmask)

            # truth targets, v4 style (lowercase mask); -1 fills
            def tgt(particle, daughters):
                grp = f.create_group(f"TARGETS/{particle}")
                mask = np.array(
                    [bool(t.get(particle)) for t in self.truth]
                )
                grp.create_dataset("mask", data=mask)
                grp.create_dataset(
                    "pt",
                    data=np.array(
                        [t.get(particle, {}).get("pt", -1.0) for t in self.truth]
                    ),
                )
                for d in daughters:
                    grp.create_dataset(
                        d,
                        data=np.array(
                            [t.get(particle, {}).get(d, -1) for t in self.truth],
                            dtype=np.int64,
                        ),
                    )

            for i in (1, 2):
                tgt(f"FRt{i}", ("b", "q1", "q2"))
                tgt(f"SRqqt{i}", ("b", "qq"))
                tgt(f"SRbqt{i}", ("q", "bq"))
                tgt(f"FBt{i}", ("bqq",))
        return path


@pytest.fixture
def toy_two_top_file(tmp_path):
    """Deterministic mixed toy set exercising all arms."""
    toys = ToyEvents()
    # 6 clean two-top events (planted triplets at jet slots 0-2 and 3-5)
    for k in range(6):
        t1 = plant_top(phi0=0.15 * k)
        t2 = plant_top(phi0=0.15 * k + math.pi, ptb=68.0)
        toys.add(
            t1 + t2 + JUNK_LIGHT + JUNK_B,
            vfjs=[(500.0, 0.1, 0.3, TOP_MASS), (400.0, -0.2, 2.0, 80.0)],
            truth={
                "FRt1": {"b": 0, "q1": 1, "q2": 2, "pt": 150.0},
                "FRt2": {"b": 3, "q1": 4, "q2": 5, "pt": 140.0},
                "FBt1": {"bqq": 0, "pt": 500.0},
            },
        )
    # 3 one-top events
    for k in range(3):
        toys.add(
            plant_top(phi0=0.4 + 0.2 * k) + JUNK_LIGHT,
            vfjs=[(450.0, 0.0, 1.0, TOP_MASS)],
            truth={
                "FRt1": {"b": 0, "q1": 1, "q2": 2, "pt": 150.0},
                "FBt1": {"bqq": 0, "pt": 450.0},
            },
        )
    # 2 sparse events (no reconstructible top)
    toys.add([(30.0, 0.0, 0.0, 5.0, False), (25.0, 0.5, 1.0, 4.0, False)])
    toys.add([(40.0, 0.2, 0.6, 6.0, True)])
    return toys, toys.write(tmp_path / "toy_test.h5")
