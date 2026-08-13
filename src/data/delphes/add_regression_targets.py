#!/usr/bin/env python3
"""Add SPANet regression targets to an existing SPAtop h5 file.

The converter already stores the parton-level top pT once per topology
particle as ``TARGETS/<particle>/pt``, but SPANet reads regression truth from a
separate group, ``REGRESSIONS/<particle>/PARTICLE/<name>``. That is the only
thing standing between the files we have and a regression run, so this copies
the values across in place rather than reprocessing 15M events through Delphes.

Masking follows SPANet's own convention: a NaN target means "skip this event"
(``jet_reconstruction_training.py``, ``current_mask = ~torch.isnan(target)``).
An event only contributes to a particle's regression loss if that particle is
actually present, i.e. ``TARGETS/<particle>/mask`` is set. Regressing a top's
pT off the FRt1 vector in an event with no resolved top would be asking the
head to predict a quantity from a slot that reconstructs nothing.

The write is additive and idempotent: existing datasets are untouched, and
re-running replaces only the REGRESSIONS group. SPANet ignores the group unless
the event file declares it, so an augmented file still works for every existing
training. h5py has no concurrent-write protection, so do not run this while a
job is reading the file.

    python add_regression_targets.py FILE.h5 [FILE2.h5 ...] [--targets pt]
    python add_regression_targets.py FILE.h5 --dry-run
"""
import argparse
import sys

import h5py
import numpy as np

TARGETS = "TARGETS"
REGRESSIONS = "REGRESSIONS"
PARTICLE = "PARTICLE"


def particles_with(h5, name):
    """Topology particles carrying a truth field of this name."""
    if TARGETS not in h5:
        return []
    return [p for p in h5[TARGETS] if name in h5[TARGETS][p]]


def augment(path, names, dry_run=False):
    mode = "r" if dry_run else "r+"
    with h5py.File(path, mode) as h5:
        n_written = 0
        for name in names:
            particles = particles_with(h5, name)
            if not particles:
                print(f"  no particle carries TARGETS/*/{name}, skipping")
                continue

            for p in particles:
                source = h5[f"{TARGETS}/{p}/{name}"]
                values = np.asarray(source[:], dtype=np.float32)

                mask_path = f"{TARGETS}/{p}/mask"
                if mask_path in h5:
                    mask = np.asarray(h5[mask_path][:]).astype(bool)
                    values = np.where(mask, values, np.nan).astype(np.float32)
                    kept = int(mask.sum())
                else:
                    kept = values.size
                    print(f"  WARNING {p}: no mask, using every event")

                key = f"{REGRESSIONS}/{p}/{PARTICLE}/{name}"
                finite = values[np.isfinite(values)]
                frac = kept / max(1, values.size)
                summary = (f"  {key:34} {kept:>10,}/{values.size:,} events "
                           f"({frac:5.1%})  mean {finite.mean():7.1f} "
                           f"std {finite.std():6.1f}")
                if dry_run:
                    print("  [dry-run]" + summary)
                    continue

                if key in h5:
                    del h5[key]
                h5.create_dataset(key, data=values, dtype="float32",
                                  compression="gzip", compression_opts=4)
                print(summary)
                n_written += 1
        return n_written


def verify(path, names):
    """Re-open and confirm the group reads back with sane content."""
    problems = []
    with h5py.File(path, "r") as h5:
        for name in names:
            for p in particles_with(h5, name):
                key = f"{REGRESSIONS}/{p}/{PARTICLE}/{name}"
                if key not in h5:
                    problems.append(f"{key} missing")
                    continue
                values = h5[key][:]
                truth = h5[f"{TARGETS}/{p}/{name}"][:]
                if values.shape != truth.shape:
                    problems.append(f"{key} shape {values.shape} != {truth.shape}")
                finite = np.isfinite(values)
                if not finite.any():
                    problems.append(f"{key} is entirely NaN")
                    continue
                # Every kept value must equal the source it was copied from.
                if not np.allclose(values[finite], truth[finite], rtol=0, atol=0):
                    problems.append(f"{key} values differ from {TARGETS}/{p}/{name}")
                if f"{TARGETS}/{p}/mask" in h5:
                    mask = np.asarray(h5[f"{TARGETS}/{p}/mask"][:]).astype(bool)
                    if not np.array_equal(finite, mask):
                        problems.append(f"{key} finite pattern != particle mask")
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", help="h5 files to augment in place")
    ap.add_argument("--targets", nargs="+", default=["pt"],
                    help="TARGETS field names to expose as regressions")
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would be written, change nothing")
    args = ap.parse_args()

    failed = False
    for path in args.files:
        print(f"\n{path}")
        augment(path, args.targets, dry_run=args.dry_run)
        if args.dry_run:
            continue
        problems = verify(path, args.targets)
        if problems:
            failed = True
            for p in problems:
                print(f"  PROBLEM: {p}")
        else:
            print("  verified")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
