#!/usr/bin/env bash
set -euo pipefail

# Source this file from WSL:
#   source scripts/wsl/activate_autocypamber_runtime.sh

ACYPA_INSTALL_ROOT="${ACYPA_INSTALL_ROOT:-$HOME/src/autocypamber-builds/current}"
ACYPA_AMBERTOOLS_HOME="${ACYPA_AMBERTOOLS_HOME:-$ACYPA_INSTALL_ROOT/ambertools25}"
ACYPA_PMEMD_HOME="${ACYPA_PMEMD_HOME:-$ACYPA_INSTALL_ROOT/pmemd24}"
ACYPA_AMBER_SH_PATH="${ACYPA_AMBER_SH_PATH:-$ACYPA_AMBERTOOLS_HOME/amber.sh}"
ACYPA_AMBER_MINICONDA_BIN="${ACYPA_AMBER_MINICONDA_BIN:-$ACYPA_AMBERTOOLS_HOME/miniconda/bin}"
ACYPA_CUDA_HOME="${ACYPA_CUDA_HOME:-/usr/local/cuda-12.8}"
ACYPA_BIN_DIR="${ACYPA_BIN_DIR:-$ACYPA_INSTALL_ROOT/bin}"
DEFAULT_MULTIWFN_BIN="$ACYPA_BIN_DIR/Multiwfn_noGUI"
if [ -x "$DEFAULT_MULTIWFN_BIN" ]; then
  MULTIWFN_BIN="${MULTIWFN_BIN:-$DEFAULT_MULTIWFN_BIN}"
else
  MULTIWFN_BIN="${MULTIWFN_BIN:-Multiwfn_noGUI}"
fi

if [ ! -f "$ACYPA_AMBER_SH_PATH" ]; then
  echo "Amber activation file not found: $ACYPA_AMBER_SH_PATH" >&2
  return 1 2>/dev/null || exit 1
fi

export LANG=C.UTF-8
export LC_ALL=C.UTF-8
export CUDA_HOME="$ACYPA_CUDA_HOME"
export MULTIWFN_BIN
export AMBER_SH_PATH="$ACYPA_AMBER_SH_PATH"
export PATH="$ACYPA_BIN_DIR:$ACYPA_PMEMD_HOME/bin:$ACYPA_AMBER_MINICONDA_BIN:$ACYPA_CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$ACYPA_CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"

source "$ACYPA_AMBER_SH_PATH"

echo "AutoCYPAmber runtime activated."
echo "  AMBER_SH_PATH=$AMBER_SH_PATH"
echo "  MULTIWFN_BIN=$MULTIWFN_BIN"
echo "  CUDA_HOME=$CUDA_HOME"
