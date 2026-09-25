import json, os, sys, requests
KEY=os.environ["WKEY"]; API="https://api.wandb.ai/graphql"
ENT,PROJ="escheuller-uc-san-diego","spatop-sweep"
def gql(q,v):
    r=requests.post(API,json={"query":q,"variables":v},auth=("api",KEY),timeout=90)
    r.raise_for_status(); j=r.json()
    if j.get("errors"): raise RuntimeError(j["errors"])
    return j["data"]

Q="""query($e:String!,$p:String!,$s:String!){project(name:$p,entityName:$e){sweep(sweepName:$s){
 name config runs(first:100){edges{node{name displayName state summaryMetrics
 sampledHistory(specs:["{\\"keys\\":[\\"validation_average_jet_accuracy\\"],\\"samples\\":500}"])}}}}}}"""

for label,sid in (("vanilla","nqupkqcl"),("blocks","ox8or7c7")):
    d=gql(Q,{"e":ENT,"p":PROJ,"s":sid})["project"]["sweep"]
    cfg=d["config"]
    if isinstance(cfg,str):
        import yaml; cfg=yaml.safe_load(cfg)
    print(f"\n===== sweep {label} ({sid}) =====")
    print("  metric config:", json.dumps(cfg.get("metric"),indent=None))
    rows=[]
    for e in d["runs"]["edges"]:
        n=e["node"]
        sm=n["summaryMetrics"]
        sm=json.loads(sm) if isinstance(sm,str) else (sm or {})
        summary=sm.get("validation_average_jet_accuracy")
        hist=[p.get("validation_average_jet_accuracy") for p in n["sampledHistory"][0]
              if p.get("validation_average_jet_accuracy") is not None]
        if not hist: continue
        rows.append((n["name"],n["state"],summary,max(hist),hist[-1]))
    # rank by each
    by_sum=sorted([r for r in rows if r[2] is not None],key=lambda r:-r[2])
    by_best=sorted(rows,key=lambda r:-r[3])
    print(f"  {'run':10} {'state':9} {'summary':>9} {'best':>9} {'last':>9}  summary==last?")
    for r in by_best:
        same = (r[2] is not None and abs(r[2]-r[4])<1e-9)
        print(f"  {r[0]:10} {r[1]:9} {str(round(r[2],4)) if r[2] is not None else 'None':>9} "
              f"{r[3]:>9.4f} {r[4]:>9.4f}  {'YES' if same else 'no'}")
    if by_sum:
        print(f"  WINNER by summary (what bayes optimised): {by_sum[0][0]}  ({by_sum[0][2]:.4f})")
    print(f"  WINNER by best-of-history (what we reported): {by_best[0][0]}  ({by_best[0][3]:.4f})")
