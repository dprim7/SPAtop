# v12 ttbar pairwise sweep (dp)

W&B team `escheuller-uc-san-diego`, project `spatop-v12-sweep`. Pairwise arm only, Tommy's
SPANet master plus the efficiency-at-purity checkpoint patch. Train on
`ttbar_hadronic_train_v12` (20% subsample for the sweep), validate on the
separate `ttbar_hadronic_val_v12` file.

Files:

- `run_sweep_v12_dp.py`: trial wrapper (writes the options JSON, runs `spanet.train`)
- `sweep_pairwise.yaml`: search space, Bayes + hyperband
- `spanet_eff_at_purity.patch`: adds `checkpoint_eff_at_purity` to SPANet
  (metric `validation_eff_at_purity` + third ModelCheckpoint); PR
  dprim7:feat/eff-at-purity-checkpoint -> tcoulvert/SPANet master. Once
  merged, drop the patch step from the agent Job
- `../dp-sweepagents-v12-pairwise-axol1tl.yml`: two agent Jobs

## 1. Stage runner and patch on the PVC

```bash
kubectl apply -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata: {name: dp-pvc-helper, namespace: axol1tl}
spec:
  restartPolicy: Never
  containers:
  - name: helper
    image: busybox
    command: ["sleep", "7200"]
    resources:
      limits:   {cpu: "1", memory: 2Gi}
      requests: {cpu: "1", memory: 2Gi}
    volumeMounts: [{mountPath: /data, name: vol}]
  volumes:
  - name: vol
    persistentVolumeClaim: {claimName: traindatavol}
YAML
kubectl wait --for=condition=Ready pod/dp-pvc-helper -n axol1tl --timeout=300s
kubectl exec -n axol1tl dp-pvc-helper -- mkdir -p /data/spatop/sweep/v12_dp
kubectl cp kube/sweep_v12_dp/run_sweep_v12_dp.py axol1tl/dp-pvc-helper:/data/spatop/sweep/v12_dp/
kubectl cp kube/sweep_v12_dp/spanet_eff_at_purity.patch axol1tl/dp-pvc-helper:/data/spatop/sweep/v12_dp/
kubectl exec -n axol1tl dp-pvc-helper -- ls -la /data/spatop/sweep/v12_dp/
kubectl delete pod dp-pvc-helper -n axol1tl
```

Re-copy after every edit: agents read the PVC copy.

## 2. Create the sweep

```bash
pip install wandb && wandb login
wandb sweep kube/sweep_v12_dp/sweep_pairwise.yaml
```

Entity and project are in the yaml. Copy the printed sweep ID into `SWEEP`
in `kube/dp-sweepagents-v12-pairwise-axol1tl.yml` (both Jobs).

## 3. Launch and watch

```bash
kubectl apply -f kube/dp-sweepagents-v12-pairwise-axol1tl.yml
kubectl get pods -n axol1tl -l jobgroup=spatop-sweep-agent
kubectl logs -n axol1tl -l job-name=dp-sweepagent-v12-pairwise-1 --tail=50 -f
```

Each trial leaves four checkpoints under
`/data/spatop/logs/sweep_v12_dp/dpv12_pairwise_<id>/version_0/checkpoints/`:
top-3 `validation_average_jet_accuracy`, `last.ckpt`, and the best
`validation_eff_at_purity` epoch (filename carries the value).

## Metric definition (`validation_eff_at_purity`)

Candidates = predicted particles with detection probability >= 0.5, ranked by
that probability. Purity = correct / selected, efficiency = correct / truth
particles. The metric is the efficiency at the loosest cut whose purity is
still >= 0.5; NaN when no cut reaches 0.5. A candidate is correct when all
its jets match the truth particle in that slot under the best event
permutation. Also logged: `validation_purity`, `validation_efficiency`,
`validation_eff_at_purity/<FR|SRqq|FB>`, `validation_balanced_eff_at_purity`
(nanmean over topologies). Mirrors the fields in Melissa's
`/traindatavol/collide2v/ckpt_scan/*/*.json`; her ranking score and overlap
handling are not published, so numbers may differ in detail.
