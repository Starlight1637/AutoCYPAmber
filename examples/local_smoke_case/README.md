# Local Smoke Case Skeleton

Replace the placeholder input paths in `case_config.template.json` with a real CYP450 protein PDB and ligand file.

Recommended layout:

- `inputs/protein.pdb`
- `inputs/ligand.sdf`
- `outputs/`

Important config fields to adjust for a real project:

- `axial_cys_resid`
- `substrate_reactive_atom_mask`
- `hbond_mask`
- `distance_pairs`

Run from the repository root:

```bash
python examples/run_local_smoke.py examples/local_smoke_case/case_config.json
```

The pipeline writes:

- `prep_heme/`
- `prep_lig/`
- `complex/`
- `md_run/`
- `analysis/`
- `report/`
