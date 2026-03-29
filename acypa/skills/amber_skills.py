import os
from acypa.heme.pipeline import HemePipeline
from acypa.deploy.environment import (
    validate_runtime_environment,
    write_runtime_activation_script as write_runtime_activation_script_file,
)
from acypa.ligand.parameterize import LigandParameterizer
from acypa.simulation.amber_md import AmberMDRunner
from acypa.utils.resources import resolve_heme_params_dir
from acypa.utils.system import run_wsl, summarize_process_output, win_to_wsl, write_file

# These functions represent reusable, generalized "Agent Skills" that can be mapped
# to an LLM tool-calling framework (like Zhuangzhou or LangChain)

def skill_prepare_cyp_heme(pdb_path: str, output_dir: str, axial_cys_resid: int, state: str = None) -> dict:
    """
    Skill: Prepares a CYP450 + Heme PDB structure using the Shahrokh protocol.
    
    Args:
        pdb_path (str): Path to the input PDB file containing CYP450 and Heme.
        output_dir (str): Working directory for the output files.
        axial_cys_resid (int): Residue ID of the axial Cysteine coordinating the Fe atom.
        state (str, optional): Heme state ('CPDI', 'DIOXY', 'IC6'). If None, auto-detected.
        
    Returns:
        dict: Path to the prepared PDB and generated state information.
    """
    pipeline = HemePipeline()
    result = pipeline.run(
        pdb_path=pdb_path,
        output_dir=output_dir,
        axial_cys_resid=axial_cys_resid,
        state=state
    )
    return result

def skill_parameterize_ligand(ligand_path: str, output_dir: str, charge: int = 0, spin: int = 1, res_name: str = 'LIG') -> dict:
    """
    Skill: Parameterizes a small molecule ligand using PySCF RESP charges and GAFF2.
    
    Args:
        ligand_path (str): Path to the ligand structure (SDF, MOL2, PDB).
        output_dir (str): Directory to save GAFF2 parameters and RESP charges.
        charge (int): Net charge of the ligand (default: 0).
        spin (int): Spin multiplicity of the ligand (default: 1 for singlet).
        res_name (str): 3-letter residue name for the ligand (default: 'LIG').
        
    Returns:
        dict: Path to the final parameter files (.mol2 and .frcmod) or error details.
    """
    parameterizer = LigandParameterizer()
    result = parameterizer.run(
        ligand_path=ligand_path,
        output_dir=output_dir,
        charge=charge,
        spin=spin,
        res_name=res_name
    )
    return result

def skill_run_amber_md(work_dir: str, top_file: str, crd_file: str, engine: str = "pmemd.cuda") -> dict:
    """
    Skill: Executes a fully automated multi-stage AMBER MD protocol (Minimization -> Heating -> Equilibration -> Production).
    
    Args:
        work_dir (str): The working directory where input/output will be saved.
        top_file (str): Path to the AMBER topology file (.prmtop).
        crd_file (str): Path to the AMBER coordinate file (.inpcrd).
        engine (str): The MD engine to use ('pmemd.cuda' or 'sander').
        
    Returns:
        dict: Status and paths to the generated trajectory (.nc) and restart files.
    """
    runner = AmberMDRunner(
        work_dir=work_dir,
        top_file=top_file,
        crd_file=crd_file,
        engine=engine
    )
    result = runner.run_protocol()
    return result

def skill_build_complex_and_solvate(cyp_pdb: str, lig_mol2: str, lig_frcmod: str, heme_state: str, cys_resid: int, output_dir: str) -> dict:
    """
    Skill: Merges the prepared CYP/Heme and Ligand components, generating complex topology via tleap.
    
    Args:
        cyp_pdb (str): Path to the prepared CYP + Heme PDB file.
        lig_mol2 (str): Path to the parameterized Ligand MOL2 file.
        lig_frcmod (str): Path to the Ligand FRCMOD file.
        heme_state (str): The Heme state used (e.g., 'CPDI', 'DIOXY', 'IC6').
        cys_resid (int): Residue ID of the axial Cysteine.
        output_dir (str): Output directory for the final topology.
        
    Returns:
        dict: Path to complex.prmtop and complex.inpcrd.
    """
    os.makedirs(output_dir, exist_ok=True)

    for label, path in {
        "cyp_pdb": cyp_pdb,
        "lig_mol2": lig_mol2,
        "lig_frcmod": lig_frcmod,
    }.items():
        if not os.path.exists(path):
            return {"status": "error", "message": f"Missing required input file: {label} -> {path}"}
    
    # Path setup
    try:
        params_base = resolve_heme_params_dir(heme_state)
    except FileNotFoundError as exc:
        return {"status": "error", "message": str(exc)}

    wsl_params = win_to_wsl(params_base)
    wsl_pdb = win_to_wsl(cyp_pdb)
    wsl_lig_mol2 = win_to_wsl(lig_mol2)
    wsl_lig_frcmod = win_to_wsl(lig_frcmod)
    
    tleap_content = f"""
source leaprc.protein.ff19SB
source leaprc.gaff2
source leaprc.water.tip3p

# Load Heme Params
loadamberparams {wsl_params}/{heme_state}.frcmod
loadmol2 {wsl_params}/HEM.mol2
loadmol2 {wsl_params}/CYP.mol2

# Load Ligand Params
loadamberparams {wsl_lig_frcmod}
LIG = loadmol2 {wsl_lig_mol2}

# Load System
mol = loadpdb {wsl_pdb}
lig = loadmol2 {wsl_lig_mol2}
complex = combine {{mol lig}}

# Setup Bonds
bond complex.{cys_resid}.SG complex.B.1.FE

# Solvate and Save
solvateoct complex TIP3PBOX 12.0
addionsrand complex Na+ 0
addionsrand complex Cl- 0
saveamberparm complex complex.prmtop complex.inpcrd
savepdb complex complex_solv.pdb
quit
"""
    tleap_in = os.path.join(output_dir, "tleap_build.in")
    write_file(tleap_in, tleap_content)
    
    tleap_res = run_wsl("tleap -f tleap_build.in > tleap.out", cwd=output_dir)
    
    prmtop = os.path.join(output_dir, "complex.prmtop")
    inpcrd = os.path.join(output_dir, "complex.inpcrd")
    
    if tleap_res.returncode == 0 and os.path.exists(prmtop) and os.path.exists(inpcrd):
        return {"status": "success", "prmtop": prmtop, "inpcrd": inpcrd}
    return {
        "status": "error",
        "message": f"tleap failed to build complex topology: {summarize_process_output(tleap_res.stdout, tleap_res.stderr)}",
        "tleap_log": os.path.join(output_dir, "tleap.out"),
    }


def skill_validate_runtime_environment(engine: str = "pmemd.cuda", multiwfn_bin: str = None) -> dict:
    """
    Skill: Probe the active WSL runtime and report whether Amber, PySCF, and Multiwfn are ready.

    Args:
        engine (str): AMBER engine to validate, default 'pmemd.cuda'.
        multiwfn_bin (str, optional): Override the Multiwfn binary/path to check.

    Returns:
        dict: Structured environment report with detected tools, env vars, and missing dependencies.
    """
    return validate_runtime_environment(engine=engine, multiwfn_bin=multiwfn_bin)


def skill_write_runtime_activation_script(
    output_path: str,
    amber_sh_path: str,
    multiwfn_bin: str,
    cuda_home: str = "/usr/local/cuda-12.8",
    pmemd_bin_dir: str = None,
    amber_miniconda_bin: str = None,
) -> dict:
    """
    Skill: Generate a reusable WSL activation script for ACYPA runtime dependencies.

    Args:
        output_path (str): Target shell script path.
        amber_sh_path (str): Path to Amber's amber.sh in WSL or Windows format.
        multiwfn_bin (str): Path or command name for Multiwfn_noGUI.
        cuda_home (str): CUDA toolkit root, default '/usr/local/cuda-12.8'.
        pmemd_bin_dir (str, optional): Directory containing pmemd.cuda.
        amber_miniconda_bin (str, optional): AmberTools bundled Python bin directory.

    Returns:
        dict: Status and generated script path.
    """
    return write_runtime_activation_script_file(
        output_path=output_path,
        amber_sh_path=amber_sh_path,
        multiwfn_bin=multiwfn_bin,
        cuda_home=cuda_home,
        pmemd_bin_dir=pmemd_bin_dir,
        amber_miniconda_bin=amber_miniconda_bin,
    )
    
