import json
import os
import sys

from _bootstrap import bootstrap_repo

bootstrap_repo()

from acypa.skills import skill_run_local_smoke_pipeline


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python examples/run_local_smoke.py <config.json|yaml>")
    result = skill_run_local_smoke_pipeline(sys.argv[1])
    print(json.dumps(result, indent=2, ensure_ascii=True))
    raise SystemExit(0 if result.get("status") == "success" else 1)


if __name__ == "__main__":
    main()
