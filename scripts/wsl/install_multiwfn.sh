#!/usr/bin/env bash
set -euo pipefail

ACYPA_INSTALL_ROOT="${ACYPA_INSTALL_ROOT:-$HOME/src/autocypamber-builds/current}"
MULTIWFN_TARBALL="${MULTIWFN_TARBALL:-}"
MULTIWFN_DIR="${MULTIWFN_DIR:-}"

if [ -z "$MULTIWFN_TARBALL" ] && [ -z "$MULTIWFN_DIR" ]; then
  echo "Set MULTIWFN_TARBALL or MULTIWFN_DIR before running this script." >&2
  exit 1
fi

TARGET_ROOT="$ACYPA_INSTALL_ROOT/tools/Multiwfn"
BIN_DIR="$ACYPA_INSTALL_ROOT/bin"
mkdir -p "$TARGET_ROOT" "$BIN_DIR"

if [ -n "$MULTIWFN_TARBALL" ]; then
  rm -rf "$TARGET_ROOT"
  mkdir -p "$TARGET_ROOT"
  tar -xf "$MULTIWFN_TARBALL" -C "$TARGET_ROOT" --strip-components=1
elif [ -n "$MULTIWFN_DIR" ]; then
  TARGET_ROOT="$MULTIWFN_DIR"
fi

MULTIWFN_BIN_PATH="$(find "$TARGET_ROOT" -maxdepth 3 -type f -name 'Multiwfn_noGUI*' | head -n 1)"
if [ -z "$MULTIWFN_BIN_PATH" ]; then
  echo "Could not locate Multiwfn_noGUI under $TARGET_ROOT" >&2
  exit 1
fi

chmod +x "$MULTIWFN_BIN_PATH" || true
ln -sfn "$MULTIWFN_BIN_PATH" "$BIN_DIR/Multiwfn_noGUI"

cat <<EOF
Multiwfn installed for AutoCYPAmber.
  TARGET_ROOT=$TARGET_ROOT
  MULTIWFN_BIN=$MULTIWFN_BIN_PATH

Next:
  export ACYPA_INSTALL_ROOT="$ACYPA_INSTALL_ROOT"
  source scripts/wsl/activate_autocypamber_runtime.sh
EOF
