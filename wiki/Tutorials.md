# Tutorials: End-to-End CYP450 Simulation (双语教程)

This tutorial demonstrates how to use **AutoCYPAmber (ACYPA)** to set up and run a Cytochrome P450 MD simulation starting from a raw PDB structure and a ligand file.

本教程演示如何使用 **AutoCYPAmber (ACYPA)**，从原始 PDB 结构和小分子文件开始，完成细胞色素 P450 的全自动 MD 模拟。

---

## 1. Prerequisites (前置准备)

Before starting, ensure you have:
1.  **A PDB file** containing the CYP450 protein and Heme (e.g., `2CPP.pdb`).
2.  **A Ligand file** in `.sdf` or `.mol2` format (e.g., `camphor.sdf`).
3.  **Residue ID** of the axial Cysteine (e.g., CYS 357).

开始前，请准备好：
1.  包含 CYP450 蛋白和 Heme 的 **PDB 文件**（如 `2CPP.pdb`）。
2.  `.sdf` 或 `.mol2` 格式的 **小分子配体文件**（如 `camphor.sdf`）。
3.  轴向半胱氨酸的 **残基编号**（如 CYS 357）。

---

## 2. Step-by-Step Execution (分步执行)

### Phase 1: High-Level Orchestration (高级调度)
The easiest way is to use our provided pipeline script in `examples/setup_cyp_md.py`.

最简单的方法是使用 `examples/setup_cyp_md.py` 中提供的管线脚本。

```python
from acypa.skills.amber_skills import (
    skill_prepare_cyp_heme,
    skill_parameterize_ligand,
    skill_build_complex_and_solvate,
    skill_run_amber_md
)

# 1. Prepare Heme & Protein (准备 Heme 和蛋白)
# ACYPA automatically detects oxidation state (e.g., CPDI)
heme_res = skill_prepare_cyp_heme("2CPP.pdb", "output/prep", axial_cys_resid=357)

# 2. Parameterize Ligand (配体参数化)
# Powered by PySCF RESP charges
lig_res = skill_parameterize_ligand("ligand.sdf", "output/lig", charge=0)

# 3. Assemble Complex (构建复合物)
# Automatically builds Fe-S bond and solvates system
build_res = skill_build_complex_and_solvate(
    cyp_pdb=heme_res['pdb'],
    lig_mol2=lig_res['mol2'],
    lig_frcmod=lig_res['frcmod'],
    heme_state=heme_res['state'],
    cys_resid=357,
    output_dir="output/complex"
)

# 4. Run Progressive MD (运行渐进式 MD)
# Executes 8-stage PRR protocol via pmemd.cuda
md_res = skill_run_amber_md("output/md", build_res['prmtop'], build_res['inpcrd'])
```

---

## 3. Interpreting Results (结果分析)

### Structural Integrity (结构完整性)
Check the `output/md/md_output/08.out` (Production MD). Ensure the **Fe-S bond** distance remains stable around **2.32 Å**.

检查生产阶段的输出文件。确保 **Fe-S 键** 距离在 **2.32 Å** 左右保持稳定。

### Trajectory Analysis (轨迹分析)
Use `cpptraj` to analyze the generated `08.nc` file.
使用 `cpptraj` 分析生成的轨迹文件。

```bash
cpptraj -p complex.prmtop -y 08.nc
> rmsd first :1-450@CA out rmsd.dat
> go
```

---

## 4. Troubleshooting (常见问题)

*   **PySCF Convergence**: If the QM calculation fails to converge, try refining the initial ligand geometry using RDKit or OpenBabel.
*   **PySCF 收敛问题**：如果量子力学计算不收敛，请尝试先用 RDKit 或 OpenBabel 优化配体的初始构象。

*   **WSL Paths**: Ensure your AMBER and Multiwfn paths are correctly exported in your `~/.bashrc` as Linux-style paths.
*   **WSL 路径问题**：请确保你的 `~/.bashrc` 中导出的 AMBER 和 Multiwfn 路径是正确的 Linux 风格路径。
