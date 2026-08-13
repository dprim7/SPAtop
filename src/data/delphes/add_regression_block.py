#!/usr/bin/env python3
"""Write a copy of a SPANet event file with its REGRESSIONS block filled in.

The particle list is read from the event file itself rather than hard-coded.
That matters: the fine-tuned model has to declare exactly the particles its
checkpoint was trained with, and the event file on the volume does not
necessarily match the one in this repo (v11 dropped the SRbq arm). Deriving the
block from the source file makes the mismatch impossible.

    python add_regression_block.py IN.yaml OUT.yaml [--targets pt] [--type gaussian]
"""
import argparse

import yaml

REGRESSIONS = "REGRESSIONS"
PARTICLE = "PARTICLE"
EVENT = "EVENT"


def build(source, targets, reg_type):
    with open(source) as f:
        info = yaml.safe_load(f)

    particles = list(info.get(EVENT, {}) or {})
    if not particles:
        raise SystemExit(f"{source}: no EVENT particles found")

    # RegressionInfo(name, type): a bare string takes the default gaussian, a
    # [name, type] pair sets it explicitly.
    block = {p: {PARTICLE: [[t, reg_type] for t in targets]} for p in particles}
    info[REGRESSIONS] = block
    return info, particles


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source")
    ap.add_argument("output")
    ap.add_argument("--targets", nargs="+", default=["pt"])
    ap.add_argument("--type", dest="reg_type", default="gaussian",
                    choices=["gaussian", "laplacian", "log_gaussian"])
    args = ap.parse_args()

    info, particles = build(args.source, args.targets, args.reg_type)
    with open(args.output, "w") as f:
        yaml.safe_dump(info, f, default_flow_style=False, sort_keys=False)

    print(f"{args.output}: {len(particles)} particles x {len(args.targets)} target(s)")
    for p in particles:
        for t in args.targets:
            print(f"  REGRESSIONS/{p}/{PARTICLE}/{t}  ({args.reg_type})")


if __name__ == "__main__":
    main()
