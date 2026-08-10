# tttt pilot (2026-08-10): 100k events, end-to-end on k8s

Full chain, run on axol1tl with the `jmduarte/mapyde` image:
MadGraph (`tttt_hadronic.txt`, ~0.15 s/ev steady) -> LHE (20 x 5000, saved) ->
`DelphesPythia8` (built in-image from the Delphes 3.5.0 source against its
/usr/local Pythia8; binary cached at `/data/spatop/tttt_pilot/bin/`) ->
ROOT (`root_v2/`) -> group converter **unmodified** with `--n-tops 4`
(`kube/spatop-tttt-convert-axol1tl.yml`) -> h5
(`/data/spatop/tttt_pilot/h5/tttt_{training,testing}.h5`: 10,934 + 2,735 events,
16 jet / 5 fat-jet slots; ~11% acceptance from the >=12-jet cut).

## Label-validation gate (tttt_label_gate.py) -- PASS
- Structural: 0 dup-daughter targets, 0 masked/out-of-range targets.
- Double-booking (SRqq b shared with an FR target): **29.4%** -- below the
  fixed-tt set's 36% and far from v6's fatal 100%; decoder contention at the
  known-workable level.
- Label physics (windows, vs fixed-tt reference): FR m(bqq) 94.4% (86.8),
  FR m(q1q2) 100.0% (80.8), SRqq m(b+fj) 84.2% (83.9), FB sdmass 86.1% (83.7).
  Figure: `reports/plots_dp_fixed/tttt_pilot_labels.png`.
- Composition: FR 55% / SRqq 60% / FB 34% of events, up to 4 labeled tops/event.

## Production gotchas discovered (also relevant to the tt pipeline)
1. The image's `DelphesPythia8` must be built from source (readers dir ships
   without it); binary reusable from the PVC.
2. `cards/LHE_condor.cmnd` has NO trailing newline -- appends without a leading
   `\n` are silently swallowed by the last comment line (cost a 5x event
   deficit until diagnosed). The condor scripts' `echo -e "\n..."` is
   load-bearing.
3. DelphesPythia8 arms its MadGraph MLM matching hook automatically (warnings
   about missing xqcut/maxjetflavor are benign for unmatched LO samples).

## Next steps
- Smoke trainings (vanilla + blocks small configs) on the pilot h5.
- Scale decision: same chain, more shards (MG ~0.15 s/ev => 10M events ~ 17k
  CPU-hours; condor and/or k8s). Revisit the >=12-jet selection with the group
  (11% acceptance; partial-events training may justify loosening).
- The pairwise-vs-vanilla sample-efficiency study on tttt: the go/no-go
  measurement for the attention-bias line at 4-top combinatorics.
