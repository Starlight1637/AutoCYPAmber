# Scientific Protocol & MD Strategy

ACYPA is built on the rigorous **Shahrokh et al. (J. Comp. Chem. 2011)** force field protocol.

## 1. Heme Oxidation States
Unlike generic force fields, ACYPA specifically identifies and parameterizes:
- **CPDI**: Compound I (Fe=O ferryl-oxo species).
- **DIOXY**: Dioxy-heme (Fe-O2).
- **IC6**: Ferric resting state (Fe-H2O or vacant).

The framework uses **Kabsch Superposition** to map any input PDB (e.g., from AlphaFold or RSCB) to the Shahrokh standard.

## 2. Progressive Restraint Release (PRR)
To handle the delicate Fe-S bond in CYP450 systems, ACYPA executes an 8-stage equilibration:
1. **Solvent Min**: Solute constrained at 500 kcal/mol.
2. **NVT Heating**: 0 -> 300K over 100 ps.
3. **NPT Equil (Stages 3-7)**: Restraints on `@CA | :HEM | :LIG` decrease linearly: `10.0 -> 5.0 -> 2.0 -> 1.0 -> 0.5`.
4. **Production**: Free NPT run.

This PRR strategy ensures that the heme active site does not "explode" during the initial density adjustment phase.
