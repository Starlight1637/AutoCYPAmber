# Heme Analysis Guide

The CYP450 catalytic center is heme-driven, so AutoCYPAmber phase 1 emphasizes heme stability rather than only global protein metrics.

## Core Outputs

- `rmsd.png`
  Protein-level drift during the short smoke trajectory.
- `rmsf.png`
  Residue-level flexibility map.
- `sasa.png`
  Global solvent exposure trend.
- `rg.png`
  Compactness trend.
- `hbond_count.png`
  Active-site-centered hydrogen-bond count based on the configured `hbond_mask`.
- `heme_rmsd.png`
  Direct structural stability of the heme group.
- `heme_sasa.png`
  Local solvent exposure of the heme environment.
- `fe_s_distance.png`
  Stability of the axial Fe-S(Cys) coordination.
- `fe_substrate_distance.png`
  Reactivity-oriented distance between Fe and the designated substrate atom.
- `distance_pairs.png`
  Configured residue/heme/substrate distance pairs, for example Thr252-to-substrate.
- `free_energy_landscape.png`
  A short-trajectory RMSD-vs-Rg landscape for quick conformational screening.

## Interpretation Notes

- `heme_rmsd` is more catalytic-site relevant than global RMSD when screening obvious setup failures.
- `Fe-S(Cys)` should remain chemically reasonable; large jumps are usually more concerning than small thermal fluctuations.
- `Fe-substrate` distance trends are only meaningful if the reactive atom mask is chosen correctly.
- `distance_pairs` should be used for key catalytic residue tracking; this is more flexible than a fixed `Fe -> residue` distance.
- Short local-smoke trajectories are enough to catch broken geometries, unstable restraints, or badly placed ligands, but not to claim a production-ready mechanistic ensemble.

## Optional MM/PBSA

`MM/PBSA` is supported as an optional extra. In phase 1 it only runs if receptor and ligand topologies are explicitly provided. A missing MM/PBSA block should not invalidate the rest of the report.
