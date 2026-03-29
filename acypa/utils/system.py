import os
import shlex
import subprocess

def win_to_wsl(path: str) -> str:
    """Convert Windows path to WSL path."""
    if not path:
        return path
    path = path.replace("\\", "/")
    if len(path) >= 2 and path[1] == ":":
        drive = path[0].lower()
        return f"/mnt/{drive}/{path[2:].lstrip('/')}"
    return path

def summarize_process_output(stdout: str, stderr: str, limit: int = 1200) -> str:
    """Return a compact, user-friendly summary of subprocess output."""
    chunks = []
    if stdout and stdout.strip():
        chunks.append(stdout.strip())
    if stderr and stderr.strip():
        chunks.append(stderr.strip())
    merged = "\n".join(chunks).strip()
    if not merged:
        return "No stdout/stderr was captured."
    merged = merged.replace("\x00", "")
    if len(merged) <= limit:
        return merged
    return merged[-limit:]

def run_wsl(cmd: str, cwd: str = None, timeout: int = 3600):
    """Run a command in WSL bash with login environment."""
    if not cmd or not cmd.strip():
        raise ValueError("run_wsl() received an empty command.")

    cwd_wsl = win_to_wsl(cwd) if cwd else "/tmp"

    # Try to find AMBERHOME or amber.sh from env, fallback to assuming it's loaded in bashrc
    amber_sh = win_to_wsl(os.environ.get("AMBER_SH_PATH", "").strip())
    source_cmd = f"source {shlex.quote(amber_sh)} && " if amber_sh else ""

    bash_cmd = f"{source_cmd}cd {shlex.quote(cwd_wsl)} && {cmd}"
    wsl_args = ["wsl.exe"]
    distro = (
        os.environ.get("ACYPA_WSL_DISTRO", "").strip()
        or os.environ.get("WSL_DISTRO_NAME", "").strip()
        or "Ubuntu-24.04"
    )
    if distro:
        wsl_args.extend(["-d", distro])
    wsl_args.extend(["bash", "-lc", bash_cmd])
    result = subprocess.run(
        wsl_args,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    return result

def write_file(path: str, content: str):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
