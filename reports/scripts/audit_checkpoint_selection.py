import re, sys, urllib.parse, urllib.request

BASE = "https://traindatavol.nrp-nautilus.io/spatop/logs"
RUNS = [
    ("sweep blocks winner gs8pex8v", f"{BASE}/sweep_fixed_dp/spatop-sweep/gs8pex8v/checkpoints/"),
    ("sweep vanilla winner g2vc1w2g", f"{BASE}/sweep_fixed_dp/spatop-sweep/g2vc1w2g/checkpoints/"),
    ("sweep blocks e19osz6f",        f"{BASE}/sweep_fixed_dp/spatop-sweep/e19osz6f/checkpoints/"),
    ("sweep blocks sqjfkudn",        f"{BASE}/sweep_fixed_dp/spatop-sweep/sqjfkudn/checkpoints/"),
    ("v6 blocks 69v6t2vw",           f"{BASE}/spatop/69v6t2vw/checkpoints/"),
    ("v6 vanilla rwlfpx3x",          f"{BASE}/spatop/rwlfpx3x/checkpoints/"),
    ("rewt gqdxggcd",                f"{BASE}/spatop/gqdxggcd/checkpoints/"),
    ("ogref gusmb6vq",               f"{BASE}/spatop/gusmb6vq/checkpoints/"),
]
print(f"{'run':32} {'sorted()[-1] loads':>10}  {'true best':>10}  {'delta':>8}  verdict")
nbad = 0
for label, url in RUNS:
    try:
        html = urllib.request.urlopen(url, timeout=25).read().decode()
    except Exception as e:
        print(f"{label:32} unreachable ({e})"); continue
    names = [urllib.parse.unquote(h) for h in re.findall(r'href="([^"]+\.ckpt)"', html)]
    names = [n for n in names if n.startswith("epoch")]      # same filter as the glob
    if not names:
        print(f"{label:32} no epoch* checkpoints"); continue
    picked = sorted(names)[-1]                                # EXACT load_model behaviour
    def score(n):
        m = re.search(r"validation_average_jet_accuracy=([0-9]+\.[0-9]+)", n)
        return float(m.group(1)) if m else -1.0
    best = max(names, key=score)
    d = score(best) - score(picked)
    nbad += d > 1e-9
    verdict = "MISMATCH" if d > 1e-9 else "ok (same file)"
    print(f"{label:32} {score(picked):>10.3f}  {score(best):>10.3f}  {d:>8.3f}  {verdict}")
    if d > 1e-9:
        print(f"{'':32}   would load: {picked}")
        print(f"{'':32}   should be : {best}")
print(f"\n{nbad}/{len(RUNS)} runs where the default would load a sub-optimal checkpoint")
