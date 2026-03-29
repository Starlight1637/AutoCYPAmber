# Multi-Agent & LLM Integration

ACYPA is natively designed to be a **"Skill Provider"** for autonomous scientific agents.

## 1. Standardized Skills (`SKILL.md`)
The repository includes a `acypa/skills/SKILL.md` file which serves as a prompt-manual for LLMs. It defines:
- **Metadata**: Capabilities of the ACYPA toolkit.
- **SOP**: Standard Operating Procedures.
- **Tools**: Direct mapping to `amber_skills.py` functions.

## 2. Usage in Autonomous Frameworks
Agents like **Zhuangzhou** can "read" the ACYPA skills and autonomously execute:
- *"Dock this inhibitor into CYP3A4 and run a 50ns MD to check stability."*
- ACYPA will handle the Heme detection, RESP fitting, and PRR protocol without further human intervention.
