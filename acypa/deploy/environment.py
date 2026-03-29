import json
import os
import textwrap

from ..utils.system import run_wsl, summarize_process_output, write_file, win_to_wsl


def validate_runtime_environment(engine: str = "pmemd.cuda", multiwfn_bin: str = None) -> dict:
    """Probe the active WSL runtime and report whether ACYPA dependencies are usable."""
    multiwfn_candidate = multiwfn_bin or os.environ.get("MULTIWFN_BIN", "Multiwfn_noGUI")
    multiwfn_candidate = win_to_wsl(multiwfn_candidate)

    probe_script = f"""
python3 - <<'PY'
import importlib
import json
import os
import shutil
import subprocess
import sys

engine = {engine!r}
multiwfn = {multiwfn_candidate!r}
required_tools = {{
    "python3": "python3",
    "obabel": "obabel",
    "antechamber": "antechamber",
    "parmchk2": "parmchk2",
    "tleap": "tleap",
    "engine": engine,
    "multiwfn": multiwfn,
}}
optional_tools = {{
    "cpptraj": "cpptraj",
    "mmpbsa": "MMPBSA.py",
}}

def resolve_candidate(candidate):
    if not candidate:
        return None
    if "/" in candidate:
        return candidate if os.path.exists(candidate) else None
    return shutil.which(candidate)

report = {{
    "env": {{
        "AMBERHOME": os.environ.get("AMBERHOME", ""),
        "MULTIWFN_BIN": os.environ.get("MULTIWFN_BIN", ""),
        "AMBER_SH_PATH": os.environ.get("AMBER_SH_PATH", ""),
        "CUDA_HOME": os.environ.get("CUDA_HOME", ""),
    }},
    "required_tools": {{}},
    "optional_tools": {{}},
    "python": {{"version": sys.version.split()[0]}},
    "warnings": [],
    "recommendations": [],
}}

for key, candidate in required_tools.items():
    report["required_tools"][key] = resolve_candidate(candidate)
for key, candidate in optional_tools.items():
    report["optional_tools"][key] = resolve_candidate(candidate)

try:
    pyscf = importlib.import_module("pyscf")
    report["python"]["pyscf"] = getattr(pyscf, "__version__", "unknown")
except Exception as exc:
    report["python"]["pyscf_error"] = str(exc)

if report["required_tools"]["python3"]:
    try:
        out = subprocess.check_output(["python3", "--version"], text=True).strip()
        report["python"]["python3_cmd"] = out
    except Exception as exc:
        report["warnings"].append(f"python3 --version failed: {{exc}}")

print(json.dumps(report))
PY
"""
    res = run_wsl(probe_script, timeout=120)
    if res.returncode != 0:
        return {
            "status": "error",
            "message": "Failed to probe the WSL runtime environment.",
            "details": summarize_process_output(res.stdout, res.stderr),
        }

    try:
        report = json.loads(res.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError) as exc:
        return {
            "status": "error",
            "message": f"Could not parse the runtime probe output: {exc}",
            "details": summarize_process_output(res.stdout, res.stderr),
        }

    required_missing = [
        name
        for name in ("python3", "obabel", "antechamber", "parmchk2", "tleap", "engine", "multiwfn")
        if not report["required_tools"].get(name)
    ]
    if "pyscf" not in report["python"]:
        required_missing.append("pyscf")

    optional_missing = [
        name
        for name in ("cpptraj", "mmpbsa")
        if not report["optional_tools"].get(name)
    ]
    if "obabel" in required_missing:
        report["recommendations"].append("Install OpenBabel in WSL, for example: sudo apt-get install -y openbabel")
    if "multiwfn" in required_missing:
        report["recommendations"].append(
            "Expose Multiwfn_noGUI through PATH or MULTIWFN_BIN, or provide MULTIWFN_TARBALL/MULTIWFN_DIR to the WSL bootstrap flow."
        )
    if "cpptraj" in optional_missing:
        report["recommendations"].append("cpptraj is optional but recommended for trajectory analysis and heme stability plots.")
    if "mmpbsa" in optional_missing:
        report["recommendations"].append("MMPBSA.py is optional and only required for MM/PBSA post-analysis.")

    report["tools"] = report["required_tools"]
    report["status"] = "success" if not required_missing else "error"
    report["missing"] = required_missing
    report["required_missing"] = required_missing
    report["optional_missing"] = optional_missing
    if required_missing:
        report["message"] = "Missing required runtime dependencies for local smoke execution."
    else:
        report["message"] = "All required runtime dependencies were detected for local smoke execution."
    return report


def write_runtime_activation_script(
    output_path: str,
    amber_sh_path: str,
    multiwfn_bin: str,
    cuda_home: str = "/usr/local/cuda-12.8",
    pmemd_bin_dir: str = None,
    amber_miniconda_bin: str = None,
) -> dict:
    """Write a reusable WSL activation script for AutoCYPAmber users."""
    amber_sh_path = win_to_wsl(amber_sh_path)
    multiwfn_bin = win_to_wsl(multiwfn_bin)
    pmemd_bin_dir = win_to_wsl(pmemd_bin_dir) if pmemd_bin_dir else ""
    amber_miniconda_bin = win_to_wsl(amber_miniconda_bin) if amber_miniconda_bin else ""
    cuda_home = win_to_wsl(cuda_home)

    path_parts = [part for part in (pmemd_bin_dir, amber_miniconda_bin, f"{cuda_home}/bin") if part]
    multiwfn_dir = os.path.dirname(multiwfn_bin) if "/" in multiwfn_bin else ""
    if multiwfn_dir:
        path_parts.insert(0, multiwfn_dir)
    path_prefix = ":".join(path_parts)
    if path_prefix:
        path_prefix += ":"

    script = textwrap.dedent(
        f"""\
        #!/usr/bin/env bash
        set -euo pipefail

        export LANG=C.UTF-8
        export LC_ALL=C.UTF-8
        export CUDA_HOME="{cuda_home}"
        export MULTIWFN_BIN="{multiwfn_bin}"
        export AMBER_SH_PATH="{amber_sh_path}"

        if [ -d "$CUDA_HOME/lib64" ]; then
          export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${{LD_LIBRARY_PATH:-}}"
        fi

        export PATH="{path_prefix}$PATH"
        source "{amber_sh_path}"
        """
    )
    write_file(output_path, script)
    return {"status": "success", "script": os.path.abspath(output_path)}
