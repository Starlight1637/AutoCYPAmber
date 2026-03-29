# Installation & Environment Guide

ACYPA is designed around a **Windows + WSL2** workflow. The Python package can live on Windows, but Amber, PySCF, OpenBabel, and Multiwfn should be available from a WSL login shell.

## 1. Recommended Layout

Use ASCII-only paths inside WSL. Avoid Chinese characters, spaces, and parentheses in scientific input/output paths whenever possible.

Recommended layout:

```bash
$HOME/src/autocypamber-builds/current/
  ambertools25/
  pmemd24/
```

## 2. Fast Bootstrap

If you already have `ambertools25.tar.bz2` and `pmemd24.tar.bz2`, the repo now ships a bootstrap script:

```bash
git clone https://github.com/ZiyanZhuang/AutoCYPAmber.git
cd AutoCYPAmber

export AMBERTOOLS_TARBALL=/mnt/c/Users/<you>/Downloads/ambertools25.tar.bz2
export PMEMD_TARBALL=/mnt/c/Users/<you>/Downloads/pmemd24.tar.bz2
export ACYPA_INSTALL_ROOT=$HOME/src/autocypamber-builds/current

# Optional: recommended for RTX 5070 / Blackwell
export ACYPA_CUDA_ARCH=sm_120

# Optional if your default WSL distro is not Ubuntu-24.04
export ACYPA_WSL_DISTRO=Ubuntu-24.04

bash scripts/wsl/bootstrap_autocypamber_runtime.sh
source scripts/wsl/activate_autocypamber_runtime.sh
```

The bootstrap script installs the core Ubuntu build dependencies, compiles AmberTools, installs `pyscf` into AmberTools' bundled Python, updates `pmemd24`, and compiles `pmemd.cuda`.

## 3. Package Installation

Install the ACYPA Python package locally:

```bash
pip install -e .
```

## 4. Runtime Validation

Validate the current WSL runtime from Python:

```python
from acypa.skills import skill_validate_runtime_environment
report = skill_validate_runtime_environment()
print(report)
```

Or use the example entrypoint:

```bash
python3 examples/validate_runtime.py
```

## 5. Manual Environment Variables

If you prefer not to source the provided activation script, make sure your WSL login shell exports:

```bash
export AMBER_SH_PATH="/path/to/amber.sh"
export MULTIWFN_BIN="/path/to/Multiwfn_noGUI"
export CUDA_HOME="/usr/local/cuda-12.8"
export PATH="/path/to/pmemd24/bin:/path/to/ambertools25/miniconda/bin:$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"
source "$AMBER_SH_PATH"
```

## 6. Notes

- `skill_build_complex_and_solvate()` now resolves packaged heme parameter files from `acypa/data/heme_params/`, so editable installs and packaged installs use the same data path.
- `run_wsl()` now honors `AMBER_SH_PATH` even if it is provided as a Windows path.
- `run_wsl()` prefers `ACYPA_WSL_DISTRO`, then `WSL_DISTRO_NAME`, then falls back to `Ubuntu-24.04`.
- For Blackwell GPUs, see [wiki/Deployment-Guide.md](C:/Users/eos/Desktop/101/AutoCYPAmber-main/wiki/Deployment-Guide.md) for the single-architecture `sm_120` recommendation.
