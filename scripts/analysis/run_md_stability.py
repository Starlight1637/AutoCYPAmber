#!/usr/bin/env python
import argparse
import json
import os
import sys


def _bootstrap_repo():
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


def main():
    _bootstrap_repo()
    from acypa.analysis import analyze_md_stability

    parser = argparse.ArgumentParser(description="Run heme-centered MD stability analysis.")
    parser.add_argument("run_dir", help="Directory containing the local smoke outputs.")
    parser.add_argument("--config", default=None, help="Optional config file.")
    parser.add_argument("--prmtop", default=None, help="Override the topology path.")
    parser.add_argument("--traj", default=None, help="Override the trajectory path.")
    parser.add_argument("--restart", default=None, help="Override the restart path.")
    parser.add_argument("--output-dir", default=None, help="Analysis output directory.")
    args = parser.parse_args()

    result = analyze_md_stability(
        run_dir=args.run_dir,
        config_path=args.config,
        prmtop_path=args.prmtop,
        traj_path=args.traj,
        restart_path=args.restart,
        output_dir=args.output_dir,
    )
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
