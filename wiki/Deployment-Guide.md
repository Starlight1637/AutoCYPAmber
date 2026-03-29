# Deployment Guide

This page documents the repository's deployment workflow for **AmberTools + pmemd24 + PySCF + Multiwfn**.

## 1. What ACYPA Expects

At runtime, ACYPA expects the following tools to be discoverable from a WSL login shell:

- `python3`
- `obabel`
- `antechamber`
- `parmchk2`
- `tleap`
- `pmemd.cuda` or your selected engine
- `Multiwfn_noGUI`
- `pyscf` importable from `python3`

For post-processing and production-grade analysis, the following are optional but recommended:

- `cpptraj`
- `MMPBSA.py`

You can validate all of the above with:

```python
from acypa.skills import skill_validate_runtime_environment
print(skill_validate_runtime_environment())
```

## 2. Deployment Assets Shipped in the Repo

- `scripts/wsl/bootstrap_autocypamber_runtime.sh`
  Purpose: install Ubuntu build dependencies, build AmberTools, install PySCF, update/build `pmemd24`.
- `scripts/wsl/install_multiwfn.sh`
  Purpose: register `Multiwfn_noGUI` from a tarball or an existing directory into the ACYPA runtime.
- `scripts/wsl/activate_autocypamber_runtime.sh`
  Purpose: source a reusable WSL runtime activation shell.
- `examples/validate_runtime.py`
  Purpose: quick runtime validation example.

## 3. Blackwell / RTX 5070 Recommendation

For `CUDA 12.7 <= version < 12.9`, ACYPA's deployment script supports a focused Blackwell build:

```bash
export ACYPA_CUDA_ARCH=sm_120
```

This applies a local `pmemd24` build patch so the CUDA 12.8 branch uses:

```text
-gencode arch=compute_120,code=sm_120
-gencode arch=compute_120,code=compute_120
```

That keeps a native cubin for RTX 5070-class hardware and preserves PTX for compatibility checks.

## 4. Generating a Reusable Activation Script

You can generate a machine-specific activation script from Python:

```python
from acypa.skills import skill_write_runtime_activation_script

skill_write_runtime_activation_script(
    output_path="activate_acypa.sh",
    amber_sh_path="/home/user/src/autocypamber-builds/current/ambertools25/amber.sh",
    multiwfn_bin="/home/user/apps/Multiwfn/Multiwfn_noGUI",
    pmemd_bin_dir="/home/user/src/autocypamber-builds/current/pmemd24/bin",
    amber_miniconda_bin="/home/user/src/autocypamber-builds/current/ambertools25/miniconda/bin",
)
```

## 5. Operational Notes

- Prefer WSL-native paths such as `/home/user/...` or `/mnt/c/...` over raw Windows paths inside scientific tool invocations.
- Keep ligand inputs, PDB files, and output directories on ASCII-only paths when possible.
- If your preferred distro is not the Windows default, set `ACYPA_WSL_DISTRO` before calling ACYPA from Python.
- If `PySCF` fails to converge, ACYPA now reports that explicitly instead of silently writing a bad `.molden` file.
- If `tleap` fails during complex construction, ACYPA now returns the path to `tleap.out` and includes the command output summary in the error payload.
- `skill_validate_runtime_environment()` now separates `required_missing` and `optional_missing` so you can distinguish local smoke blockers from optional analysis extras.
- `activate_autocypamber_runtime.sh` now prefers `$ACYPA_INSTALL_ROOT/bin/Multiwfn_noGUI` when present, which matches the output of `install_multiwfn.sh`.
