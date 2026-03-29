#!/usr/bin/env bash
set -euo pipefail

# Quick-start runtime bootstrap for WSL Ubuntu.
# Example:
#   export AMBERTOOLS_TARBALL=/mnt/c/Users/you/Downloads/ambertools25.tar.bz2
#   export PMEMD_TARBALL=/mnt/c/Users/you/Downloads/pmemd24.tar.bz2
#   export ACYPA_INSTALL_ROOT=$HOME/src/autocypamber-builds/current
#   export ACYPA_CUDA_ARCH=sm_120
#   bash scripts/wsl/bootstrap_autocypamber_runtime.sh

AMBERTOOLS_TARBALL="${AMBERTOOLS_TARBALL:-}"
PMEMD_TARBALL="${PMEMD_TARBALL:-}"
ACYPA_INSTALL_ROOT="${ACYPA_INSTALL_ROOT:-$HOME/src/autocypamber-builds/current}"
ACYPA_CUDA_TOOLKIT_ROOT="${ACYPA_CUDA_TOOLKIT_ROOT:-/usr/local/cuda-12.8}"
ACYPA_CUDA_ARCH="${ACYPA_CUDA_ARCH:-}"
MULTIWFN_TARBALL="${MULTIWFN_TARBALL:-}"
MULTIWFN_DIR="${MULTIWFN_DIR:-}"

if [ -z "$AMBERTOOLS_TARBALL" ] || [ -z "$PMEMD_TARBALL" ]; then
  echo "Set AMBERTOOLS_TARBALL and PMEMD_TARBALL before running this script." >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
sudo apt-get update
sudo apt-get install -y \
  build-essential \
  gfortran \
  cmake \
  flex \
  bison \
  patch \
  openbabel \
  libgomp1 \
  curl \
  xz-utils \
  python3 \
  python3-pip

mkdir -p "$ACYPA_INSTALL_ROOT"
WORK_ROOT="$(dirname "$ACYPA_INSTALL_ROOT")"
AMBERTOOLS_SRC="$WORK_ROOT/ambertools25_src"
PMEMD_SRC="$WORK_ROOT/pmemd24_src"
AMBERTOOLS_HOME="$ACYPA_INSTALL_ROOT/ambertools25"
PMEMD_HOME="$ACYPA_INSTALL_ROOT/pmemd24"

rm -rf "$AMBERTOOLS_SRC" "$PMEMD_SRC"
mkdir -p "$AMBERTOOLS_SRC" "$PMEMD_SRC"
tar -xjf "$AMBERTOOLS_TARBALL" -C "$AMBERTOOLS_SRC" --strip-components=1
tar -xjf "$PMEMD_TARBALL" -C "$PMEMD_SRC" --strip-components=1

pushd "$AMBERTOOLS_SRC" >/dev/null
python3 ./update_amber --update
rm -rf build-fresh
mkdir -p build-fresh
pushd build-fresh >/dev/null
cmake "$AMBERTOOLS_SRC" \
  -DCMAKE_INSTALL_PREFIX="$AMBERTOOLS_HOME" \
  -DCOMPILER=GNU \
  -DMPI=FALSE \
  -DCUDA=FALSE \
  -DINSTALL_TESTS=TRUE \
  -DDOWNLOAD_MINICONDA=TRUE
make install -j1
popd >/dev/null
"$AMBERTOOLS_HOME/miniconda/bin/python" -m pip install --upgrade pip pyscf
popd >/dev/null

pushd "$PMEMD_SRC" >/dev/null
python3 ./update_pmemd --update
if [ "$ACYPA_CUDA_ARCH" = "sm_120" ]; then
  python3 - <<'PY'
from pathlib import Path
path = Path("cmake/CudaConfig.cmake")
text = path.read_text(encoding="utf-8")
old = """       elseif((${CUDA_VERSION} VERSION_GREATER_EQUAL 12.7) AND (${CUDA_VERSION} VERSION_LESS 12.9))
           message(STATUS "Configuring for SM7.0, SM7.5, SM8.0, SM8.6, SM9.0, SM10.0 and SM12.0")
           list(APPEND CUDA_NVCC_FLAGS ${SM70FLAGS} ${SM75FLAGS} ${SM80FLAGS} ${SM86FLAGS} ${SM90FLAGS} ${SM100FLAGS} ${SM120FLAGS} -Wno-deprecated-gpu-targets -Wno-deprecated-declarations)
"""
new = """       elseif((${CUDA_VERSION} VERSION_GREATER_EQUAL 12.7) AND (${CUDA_VERSION} VERSION_LESS 12.9))
           message(STATUS "Configuring for SM12.0 only (native cubin + PTX) on Blackwell")
           list(APPEND CUDA_NVCC_FLAGS
               -gencode arch=compute_120,code=sm_120
               -gencode arch=compute_120,code=compute_120
               -Wno-deprecated-gpu-targets
               -Wno-deprecated-declarations)
"""
if old not in text:
    raise SystemExit("Could not locate the expected CUDA 12.7-12.9 stanza in CudaConfig.cmake")
path.write_text(text.replace(old, new), encoding="utf-8")
PY
fi
rm -rf build-fresh
mkdir -p build-fresh
pushd build-fresh >/dev/null
cmake "$PMEMD_SRC" \
  -DCMAKE_INSTALL_PREFIX="$PMEMD_HOME" \
  -DCOMPILER=GNU \
  -DMPI=FALSE \
  -DCUDA=TRUE \
  -DINSTALL_TESTS=TRUE \
  -DDOWNLOAD_MINICONDA=FALSE \
  -DBUILD_PYTHON=FALSE \
  -DBUILD_PERL=FALSE \
  -DBUILD_GUI=FALSE \
  -DPMEMD_ONLY=TRUE \
  -DCHECK_UPDATES=FALSE \
  -DCUDA_TOOLKIT_ROOT_DIR="$ACYPA_CUDA_TOOLKIT_ROOT"
make install -j1
popd >/dev/null
popd >/dev/null

if [ -n "$MULTIWFN_TARBALL" ] || [ -n "$MULTIWFN_DIR" ]; then
  bash scripts/wsl/install_multiwfn.sh
fi

cat <<EOF
Bootstrap finished.

Next steps:
1. export ACYPA_INSTALL_ROOT="$ACYPA_INSTALL_ROOT"
2. Optional: export MULTIWFN_TARBALL=/path/to/Multiwfn.tar.gz and run scripts/wsl/install_multiwfn.sh
3. source scripts/wsl/activate_autocypamber_runtime.sh
4. python3 -c "from acypa.skills import skill_validate_runtime_environment; print(skill_validate_runtime_environment())"
EOF
