import json

from _bootstrap import bootstrap_repo

bootstrap_repo()

from acypa.skills import skill_validate_runtime_environment


if __name__ == "__main__":
    print(json.dumps(skill_validate_runtime_environment(), indent=2, ensure_ascii=True))
