# CYP450 Experiment Report

## Objective

We compared three candidate protocols for ligand-bound CYP equilibration and production readiness.

## Experimental Setup

- System: CYP450 with heme and one ligand
- Replicates: 3
- Production readiness criterion: stable Fe-S region and acceptable RMSD

## Results

| Protocol | Accuracy (%) | RMSD | Runtime (min) |
| --- | --- | --- | --- |
| Baseline | 82.4 | 2.31 | 47 |
| PRR-8 | 88.9 | 1.92 | 53 |
| PRR-10 | 90.1 | 1.85 | 61 |

The PRR-10 setting achieved 90.1% readiness accuracy and reduced RMSD to 1.85.
PRR-8 was slightly faster and still improved quality relative to the baseline.

## Conclusion

PRR-10 appears to be the best default when quality is prioritized over runtime.
