import json
import sys

from _bootstrap import bootstrap_repo

bootstrap_repo()

from acypa.skills import skill_analyze_md_stability


def main():
    if len(sys.argv) not in (2, 3):
        raise SystemExit("Usage: python examples/analyze_md_run.py <run_dir> [config.json|yaml]")
    result = skill_analyze_md_stability(run_dir=sys.argv[1], config_path=sys.argv[2] if len(sys.argv) == 3 else None)
    print(json.dumps(result, indent=2, ensure_ascii=True))
    raise SystemExit(0 if result.get("status") == "success" else 1)


if __name__ == "__main__":
    main()
