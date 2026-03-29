# AutoCYPAmber (ACYPA)

**Autonomous Orchestration for High-Fidelity Cytochrome P450 and Ligand MD Simulations.**

**Authors**: Ziyan Zhuang, Qianyu Zhao

<p align="center">
  <img src="https://api.visitorbadge.io/api/combined?path=https%3A%2F%2Fgithub.com%2FZiyanZhuang%2FAutoCYPAmber&labelColor=%232ccce4&countColor=%23263759&style=flat-square&graphic=line-chart" alt="Visitor Chart" />
</p>

[![Stars](https://img.shields.io/github/stars/ZiyanZhuang/AutoCYPAmber?style=flat-square&logo=github)](https://github.com/ZiyanZhuang/AutoCYPAmber/stargazers)
[![Issues](https://img.shields.io/github/issues/ZiyanZhuang/AutoCYPAmber?style=flat-square&logo=github)](https://github.com/ZiyanZhuang/AutoCYPAmber/issues)
[![License](https://img.shields.io/badge/License-Academic%20Non--Commercial-orange.svg?style=flat-square)](./LICENSE)

---

## 1. Scientific Protocol
ACYPA implements the **Shahrokh-Protocol (J. Comp. Chem. 2011)** for heme metalloproteins, featuring:
- **Heme States**: Automated detection and parameterization for CPDI, DIOXY, and IC6.
- **QM/RESP**: High-precision ligand charges via PySCF/Multiwfn (HF/6-31G*).
- **PRR Equil**: 8-stage **Progressive Restraint Release** strategy for robust system relaxation.

## 2. Multi-Agent Architecture
This project is designed as a **Skill-Provider** for Multi-Agent Systems (MAS):
- **QM-Agent**: Handles first-principles parameterization.
- **Topology-Agent**: Manages Fe-S covalent bonding and solvent assembly.
- **HPC-Agent**: Orchestrates GPU-accelerated production runs.

## 3. Installation
```bash
git clone https://github.com/ZiyanZhuang/AutoCYPAmber.git
cd AutoCYPAmber
pip install -e .
```
ACYPA expects the scientific runtime to live in **WSL2** on Windows. The fastest path is:

```bash
# Inside WSL
export AMBERTOOLS_TARBALL=/mnt/c/Users/<you>/Downloads/ambertools25.tar.bz2
export PMEMD_TARBALL=/mnt/c/Users/<you>/Downloads/pmemd24.tar.bz2
export ACYPA_INSTALL_ROOT=$HOME/src/autocypamber-builds/current

# Optional for RTX 5070 / Blackwell
export ACYPA_CUDA_ARCH=sm_120

# Optional if your default WSL distro is not Ubuntu-24.04
export ACYPA_WSL_DISTRO=Ubuntu-24.04

bash scripts/wsl/bootstrap_autocypamber_runtime.sh
source scripts/wsl/activate_autocypamber_runtime.sh
python3 examples/validate_runtime.py
```

Detailed setup is documented in [wiki/Installation-Guide.md](C:/Users/eos/Desktop/101/AutoCYPAmber-main/wiki/Installation-Guide.md) and [wiki/Deployment-Guide.md](C:/Users/eos/Desktop/101/AutoCYPAmber-main/wiki/Deployment-Guide.md).

## 4. Skills Definition
Standardized Skill files are located in `acypa/skills/`:
- `SKILL.md`: English (Primary)
- `SKILL_ZH.md`: Chinese (Secondary, if applicable)

Runtime/bootstrap-related skills are also available from Python:

```python
from acypa.skills import (
    skill_validate_runtime_environment,
    skill_write_runtime_activation_script,
)

report = skill_validate_runtime_environment()
print(report["status"], report["missing"])
```

Additional workflow skills are available for the phase-1 local smoke pipeline:

```python
from acypa.skills import (
    skill_prepare_local_smoke_case,
    skill_run_local_smoke_pipeline,
    skill_analyze_md_stability,
    skill_render_md_report,
)
```

## 5. Local Report Automation

This repository also ships a local-only Markdown reporting pipeline:

```bash
python scripts/reporting/report_pipeline.py examples/sample_experiment_report.md
```

That pipeline can:

- analyze experiment results from Markdown
- generate `DOCX`
- generate `PDF` through LaTeX/XeLaTeX

If you want MCP-style local tool access without touching global config, see [wiki/Office-Latex-MCP.md](C:/Users/eos/Desktop/101/AutoCYPAmber-main/wiki/Office-Latex-MCP.md).

## 6. Local Smoke Pipeline And Heme Analysis

Phase 1 now targets a **local smoke** workflow on a workstation GPU such as RTX 5070:

- local preprocessing
- short restrained MD for pipeline validation
- heme-centered trajectory analysis
- automatic `Markdown -> DOCX/PDF` reporting

The repository ships a sample skeleton under [examples/local_smoke_case/README.md](C:/Users/eos/Desktop/101/AutoCYPAmber-main/examples/local_smoke_case/README.md).

Typical usage:

```bash
python examples/run_local_smoke.py examples/local_smoke_case/case_config.json
python scripts/analysis/run_md_stability.py /path/to/local_smoke_run --config /path/to/case_config.json
```

Recommended model:

- local workstation: heme prep, ligand parameterization, short smoke MD, heme stability analysis
- server GPU: long production MD and final scientific interpretation

## 7. References & Academic Ethics

ACYPA is an orchestration framework that automates the integration of several high-impact scientific tools and force field parameters. If you use this toolkit in your research, please cite the following original works:

### Heme & Protein Force Field (Shahrokh Protocol)
*   **Shahrokh, K., Otyepka, M., & Baron, R. (2011).** *Development of Amber force field parameters for heme-containing proteins.* **Journal of Computational Chemistry**, 33(2), 119–133. [DOI: 10.1002/jcc.21922](https://doi.org/10.1002/jcc.21922)
    *(This project utilizes the CPDI, DIOXY, and IC6 parameters derived from this protocol.)*

### Molecular Dynamics Engine (AMBER)
*   **Case, D. A., et al. (2025).** *AMBER 2025.* University of California, San Francisco.
    *(The simulation logic drives `pmemd.cuda` and `tleap` from the AmberTools suite.)*

### Quantum Chemistry & RESP Charges (PySCF & Multiwfn)
*   **Sun, Q., et al. (2018).** *PySCF: the Python-based simulations of chemistry framework.* **WIREs Comput Mol Sci**, 8:e1340. [DOI: 10.1002/wcms.1340](https://doi.org/10.1002/wcms.1340)
*   **Lu, T., & Chen, F. (2012).** *Multiwfn: A multifunctional wavefunction analyzer.* **Journal of Computational Chemistry**, 33, 580-592. [DOI: 10.1002/jcc.22882](https://doi.org/10.1002/jcc.22882)
    *(The ligand parameterization pipeline replaces traditional Gaussian calls with PySCF for wavefunction generation and Multiwfn for RESP fitting.)*

### Ligand Force Field (GAFF2 & Antechamber)
*   **Wang, J., Wolf, R. M., Caldwell, J. W., Kollman, P. A., & Case, D. A. (2004).** *Development and testing of a general amber force field.* **Journal of Computational Chemistry**, 25(9), 1157-1174. [DOI: 10.1002/jcc.20035](https://doi.org/10.1002/jcc.20035)

## 8. Star History

[![Star History Chart](https://api.star-history.com/svg?repos=ZiyanZhuang/AutoCYPAmber&type=Date)](https://star-history.com/#ZiyanZhuang/AutoCYPAmber&Date)

## 9. Geographic Visitor Distribution

<p align="center">
  <a href="https://info.flagcounter.com/Z8Xn"><img src="https://s11.flagcounter.com/count2/Z8Xn/bg_FFFFFF/txt_000000/border_CCCCCC/columns_5/maxflags_10/viewers_0/labels_0/pageviews_0/flags_0/percent_0/" alt="Flag Counter" border="0"></a>
</p>

## 10. License
This framework is provided under an **Academic Non-Commercial Use License**. See the `LICENSE` file for details.
The **Heme Parameters** included in `./data/heme_params` remain the intellectual property of the original authors (Shahrokh et al.) and are distributed here for convenience in accordance with academic non-commercial usage.
