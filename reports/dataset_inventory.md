# Bigger-FR training set: dataset inventory & recommendation (WS6, 2026-07-30)

Scan of every `*.h5` ≥ 100 MB on both volumes, checked against the v11 schema
(`tt_hadronic_v7_full.yaml`: Jets `pt,eta,sinphi,cosphi,btag,mass,matchedfj,deltaRfj`;
BoostedJets `fj_pt,…,fj_sdmass,fj_Ttag,fj_Wtag,fj_tau21,fj_tau32,fj_ncharged`;
targets FRt/SRqqt/FBt). Composition = % of events with ≥1 valid target of that
topology. Jobs: `dp-spatop-inventory-{cmsml,axol1tl}`
(`kube/spatop-inventory-datasets.yml`).

## Candidates on cms-ml/spatopvol (old delphes production)

| dataset | events | size | v11 columns | composition FR/SRqq/FB | mtime |
|---|---|---|---|---|---|
| **v6 `training2k_clean`** | **15.36 M** | 10.1 GiB | **complete** | 30.0 / 33.8 / 7.5 % | 2026-02-24 |
| **v6 `training2k_clean_noSRoverlap`** | **15.36 M** | 10.1 GiB | **complete** | 30.0 / 33.8 / 7.5 % | 2026-02-26 |
| v6 `testing2k_clean(_noSRoverlap)` | 3.84 M | 2.5 GiB | complete | 30.0 / 33.8 / 7.5 % | 2026-02 |
| v8 `training2k_clean_jetmask_corr` | 15.36 M | 9.9 GiB | missing `deltaRfj` | 30.0 / 33.8 / 7.5 % | 2026-03-03 |
| v7 `…valid_targets_jetmask_clean` | 8.79 M | 6.2 GiB | missing `deltaRfj` | 52.4 / 59.1 / 13.1 % | 2026-02-26 |
| v8 `…jetmask_corr_valid_targets` | 3.41 M | 2.1 GiB | missing `deltaRfj` | 75.5 / 42.8 / 26.4 % | 2026-03-03 |
| irvine `ttbar_training.h5` | – | 4.3 GiB | UNREADABLE (corrupt symbol table) | – | 2026-02-27 |
| v2 `training_FRw{2,10}` | 1.18 M | 2.0 GiB | different era (precomputed ATTENTION_BIAS + VeryBoostedJets) | 19.6 / 16.6 / 35.4 % | 2025-08 |

All sets carry the extra SRbq targets and extra input columns — harmless, SPANet
only reads what the event file lists.

Reference (axol1tl/traindatavol): current fixed training set = 864 k events
(FR 67.0 / SRqq 44.0 / FB 7.1 %); old May-29 set = 1.02 M (FR 19.8 %). Nothing
larger exists on traindatavol.

## Verdict

**Candidate: delphes v6 `tt_hadronic_training2k_clean.h5`** (or the
`_noSRoverlap` twin — ask Thomas which is preferred). It is the only
column-complete large set: **17.8× the events of the fixed set, ~8× the FR
targets** (≈4.6 M vs ≈0.58 M), with a matching 3.84 M-event test file.
v7/v8 are out as-is (no `deltaRfj`); irvine file is corrupt.

**Blocking question (label provenance):** every candidate predates Thomas's
Jul-8 label fix, and the v6 composition (FR 30 %) matches neither the pre-fix
May set (FR 20 %) nor the fixed set (FR 67 %) — it is a different pipeline
generation. Before training on it we need Thomas to confirm whether the v6
labels carry the bug his fix corrected. If they do, the path is re-conversion
of the v6 ROOT sources through the fixed pipeline, not direct use.

**Recommended sequence:** (1) ask Thomas about v6 label provenance;
(2) if clean → copy to traindatavol (~10 GiB) and launch a blocks-winner
config run with `dataset_limit` staged (the saturation study says FR is the
unsaturated topology — this is exactly where the extra events should pay off);
(3) if not clean → request a fixed-pipeline re-conversion; do not spend GPU
time on known-bad labels.
