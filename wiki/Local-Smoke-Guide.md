# Local Smoke Guide

This guide describes the phase-1 execution model for AutoCYPAmber.

## Goal

Use a local workstation GPU, such as RTX 5070, for:

- heme preparation
- ligand parameterization
- complex construction
- short MD smoke validation
- heme-centered post-analysis
- automated Markdown/PDF/DOCX report generation

Long production MD should still move to a server GPU whenever possible.

## Input Contract

Create a case config from [examples/local_smoke_case/case_config.template.json](C:/Users/eos/Desktop/101/AutoCYPAmber-main/examples/local_smoke_case/case_config.template.json) and provide:

- `protein_pdb`
- `ligand_path`
- `axial_cys_resid`
- optional heme state override
- optional analysis masks for substrate reactive atom, `hbond_mask`, and `distance_pairs`

## Output Layout

The workflow writes:

- `prep_heme/`
- `prep_lig/`
- `complex/`
- `md_run/`
- `analysis/`
- `report/`
- `server_handoff.json`

## Commands

```bash
python examples/run_local_smoke.py examples/local_smoke_case/case_config.json
python scripts/analysis/run_md_stability.py /path/to/output_root --config /path/to/case_config.json
```

## Scientific Boundaries

- The local smoke profile is for integration validation and obvious geometry failures.
- It is not a replacement for long production trajectories.
- Heme-centered distances and RMSD trends are useful early filters, not final catalytic proof.
