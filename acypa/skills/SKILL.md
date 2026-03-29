# Skill: AutoCYPAmber (ACYPA) - Autonomous CYP450 MD Setup

## 1. Metadata
- **Name**: ACYPA
- **Description**: Specialized workflow for automated parameterization and MD simulation of cytochrome P450 systems.
- **Protocol**: Shahrokh Protocol (2011) + PySCF-driven RESP + AMBER PRR equilibration.

## 2. Standard Operating Procedure (SOP)

### Phase 0: Runtime Validation & Bootstrap
1. **Environment Check**: Validate `python3`, `obabel`, `antechamber`, `parmchk2`, `tleap`, `pmemd.cuda`, `Multiwfn_noGUI`, and `pyscf`.
2. **Activation Script**: Generate or source a reusable WSL activation script that exports `AMBER_SH_PATH`, `MULTIWFN_BIN`, `CUDA_HOME`, and pmemd/AmberTools Python paths.
3. **WSL Discipline**: Prefer ASCII-only WSL paths for Amber, PySCF, ligand inputs, and MD working directories.

### Phase 1: Structural Preparation
1. **State Detection**: Analyze the Fe environment to identify the heme redox/ligation state.
2. **Kabsch Mapping**: Force-map PDB coordinates to Shahrokh-standard mol2 naming.
3. **CYS Neutralization**: Rename the axial cysteine to `CYP` (deprotonated) and ensure Fe-S linkage consistency.

### Phase 2: Ligand Parameterization
1. **Atom Typing**: Assign GAFF2 atom types via `antechamber`.
2. **QM Calculation**: Run HF/6-31G* single-point energy via PySCF inside WSL.
3. **RESP Fitting**: Perform RESP fitting via Multiwfn and inject charges back into the mol2 file.

### Phase 3: Progressive MD Simulation
1. **Solvent Relaxation**: Minimize solvent with strong solute restraints.
2. **Isobaric Heating**: Heat from 0 K to 300 K in NVT.
3. **Restraint Release (PRR)**: Run 5 NPT equilibration stages with force constants 10.0 -> 5.0 -> 2.0 -> 1.0 -> 0.5 kcal/mol.
4. **Production**: Run unrestrained NPT production.

## 3. Verification Guidelines
- **Structural**: Verify Fe-S distance remains chemically reasonable in the production-ready structure.
- **Charge**: Ensure ligand net charge matches the intended chemical state.
- **QM Quality**: Reject unconverged PySCF calculations and inspect the generated `.molden` and `.chg` files.
- **MD Stability**: Monitor RMSD, density, and basic pressure/temperature stability through the PRR protocol.

## 4. Runtime Skills
- `skill_validate_runtime_environment()`: Check whether the active WSL runtime is actually ready for ACYPA.
- `skill_write_runtime_activation_script()`: Generate a reusable shell script that exports Amber, CUDA, Multiwfn, and pmemd paths.

## 5. Reporting Skills
- `skill_analyze_markdown_results(markdown_path, output_dir=None)`: Extract metric-oriented findings from a Markdown experiment report and write `analysis_summary.md`.
- `skill_render_markdown_bundle(markdown_path, output_dir=None, include_analysis=True, metadata_title=None)`: Render Markdown into `DOCX` and `PDF` through `pandoc` + `xelatex`, optionally appending the generated analysis section first.

## 6. Local Smoke And Stability Skills
- `skill_prepare_local_smoke_case(config_path)`: Validate inputs, create the standard output layout, and materialize a resolved local-smoke config.
- `skill_run_local_smoke_pipeline(config_path)`: Execute heme prep, ligand parameterization, complex build, shortened MD, heme-centered analysis, and report rendering.
- `skill_analyze_md_stability(run_dir, config_path=None)`: Run `cpptraj`-driven RMSD/RMSF/SASA/Rg/H-bond/heme geometry analysis and write `report.md`.
  The phase-1 config should prefer `hbond_mask` for active-site H-bond analysis and `distance_pairs` for residue/heme/substrate distance tracking.
- `skill_render_md_report(report_md_path, output_dir=None)`: Convert the generated Markdown report into `DOCX` and `PDF`.
