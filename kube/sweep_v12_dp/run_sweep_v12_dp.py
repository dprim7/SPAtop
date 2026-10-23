#!/usr/bin/env python3
"""W&B sweep wrapper for the v12 ttbar pairwise sweep (dp, 2026-10-23).

Adapted from kube/sweep_fixed_dp/run_sweep_fixed_dp.py. Differences:
  - pairwise arm only (the pairwise keys are fixed in BASE_CONFIG)
  - training_file -> ttbar_hadronic_train_v12, validation_file -> the separate
    ttbar_hadronic_val_v12 file (no 5% split off the training set)
  - dataset_limit / epochs come from the sweep yaml (subsample sweep first,
    full-data validation of the winners afterwards)
  - checkpoint_eff_at_purity 0.5: SPANet saves a third checkpoint, the epoch
    with the best efficiency at 50% purity (needs the eff_at_purity patch, see
    the agent Job)
Inherited unchanged: num_dataloader_workers 0, logs to node-local /scratch
(agent rsyncs to the PVC), WANDB_ENTITY passed through so the resumed run stays
in the team entity.
"""
import json, os, subprocess, sys
import wandb

BASE_CONFIG = {
    "num_encoder_layers": 4,
    "num_branch_embedding_layers": 3,
    "num_branch_encoder_layers": 3,
    "num_jet_embedding_layers": 0,
    "num_jet_encoder_layers": 2,
    "num_detector_layers": 2,
    "num_regression_layers": 3,
    "num_classification_layers": 3,
    "split_symmetric_attention": True,
    "num_attention_heads": 8,
    "transformer_activation": "gelu",
    "linear_block_type": "GRU",
    "transformer_type": "Gated",
    "linear_activation": "gelu",
    "normalization": "LayerNorm",
    "masking": "Filling",
    "skip_connections": True,
    "initial_embedding_skip_connections": True,
    "event_info_file": "/data/spatop/event_files/v11/tt_hadronic_v7_full.yaml",
    "training_file": "/data/spatop/ttbar_hadronic_train_v12/all_merged.h5",
    "validation_file": "/data/spatop/ttbar_hadronic_val_v12/all_merged.h5",
    "normalize_features": True,
    "limit_to_num_jets": 0,
    "balance_jets": False,
    "partial_events": True,
    "balance_particles": False,
    "balance_particles_weighted": None,
    "dataset_limit": 0.2,
    "limit_val_batches": 0.25,
    "num_dataloader_workers": 0,
    "mask_sequence_vectors": True,
    "combine_pair_loss": "min",
    "optimizer": "AdamW",
    "focal_gamma": 0.0,
    "learning_rate_cycles": 1,
    "learning_rate_warmup_epochs": 1.0,
    "assignment_loss_scale": 1.0,
    "detection_loss_scale": 1.0,
    "kl_loss_scale": 0.0,
    "regression_loss_scale": 0.0,
    "classification_loss_scale": 0.0,
    "l2_penalty": 0.0002,
    "gradient_clip": 10.0,
    "epochs": 30,
    "num_gpu": 1,
    "verbose_output": True,
    "use_pairwise_interactions": True,
    "pairwise_input_source": "all",
    "num_pairwise_features": 4,
    "pairwise_embedding_dim": 8,
    "pairwise_block_embeddings": True,
    "checkpoint_eff_at_purity": 0.5,
}

run = wandb.init()  # bare: inherits the sweep's entity/project (team!)
config = dict(wandb.config)
run_id = run.id
run_project = run.project
run_entity = run.entity

hidden_dim = config.get("hidden_dim", 64)
full_config = {
    **BASE_CONFIG,
    **config,
    "hidden_dim": hidden_dim,
    "transformer_dim": hidden_dim,
    "initial_embedding_dim": hidden_dim,
    "position_embedding_dim": hidden_dim,
}

os.makedirs("/data/spatop/options_files/sweep_v12_dp", exist_ok=True)
os.makedirs("/scratch/logs", exist_ok=True)

config_path = f"/data/spatop/options_files/sweep_v12_dp/config_{run_id}.json"
with open(config_path, "w") as f:
    json.dump(full_config, f, indent=2)

run_name = f"dpv12_pairwise_{run_id}"
log_dir = "/scratch/logs"

print(f"=== Trial {run.name} | swept: {json.dumps(config, indent=2)}")

# Release the wrapper's hold; SPANet's WandbLogger resumes the SAME run via
# WANDB_RUN_ID so metrics stream live (single active client at a time).
wandb.finish()

proc = subprocess.run(
    ["python", "-m", "spanet.train", "-of", config_path, "-l", log_dir, "-n", run_name],
    env={
        **os.environ,
        "WANDB_ENTITY": run_entity,
        "WANDB_PROJECT": run_project,
        "WANDB_RUN_ID": run_id,
        "WANDB_RESUME": "allow",
    },
)

if proc.returncode != 0:
    print(f"Training failed (exit code {proc.returncode})")
    sys.exit(1)
