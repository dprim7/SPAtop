#!/usr/bin/env python3
"""Render the pT-regression fine-tune Job with the data scripts spliced in.

The pod has no checkout of this repo, and copying the scripts by hand into the
YAML would let them drift from the tested versions under src/data/delphes/.
So the job is generated: the scripts are embedded verbatim at render time.

    python kube/render_massreg_job.py        # writes kube/spatop-massreg-pt-axol1tl.yml
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(HERE, "spatop-massreg-pt-axol1tl.yml")

SCRIPTS = {
    "add_regression_targets.py": "src/data/delphes/add_regression_targets.py",
    "add_regression_block.py": "src/data/delphes/add_regression_block.py",
}


def embed(rel, indent):
    """Inline a file, indented into the YAML block scalar."""
    with open(os.path.join(REPO, rel)) as f:
        body = f.read().rstrip("\n")
    pad = " " * indent
    return "\n".join(pad + line if line else "" for line in body.split("\n"))


HEADER = open(os.path.join(HERE, "_massreg_header.txt")).read()
FOOTER = open(os.path.join(HERE, "_massreg_footer.txt")).read()


def main():
    parts = [HEADER]
    for name, rel in SCRIPTS.items():
        parts.append(f"          cat > $SCRIPTS/{name} <<'SCRIPT_EOF'\n")
        parts.append(embed(rel, 10))
        parts.append("\n          SCRIPT_EOF\n")
    parts.append(FOOTER)

    with open(OUT, "w") as f:
        f.write("".join(parts))
    print(f"wrote {OUT}")
    for name, rel in SCRIPTS.items():
        print(f"  embedded {rel}")


if __name__ == "__main__":
    main()
