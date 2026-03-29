import os
import logging
from ..utils.system import run_wsl, summarize_process_output, write_file

logger = logging.getLogger(__name__)

def run_pyscf_resp_wsl(ligand_path_wsl, output_dir, charge=0, spin=1):
    """Run PySCF inside WSL to generate a .molden file for RESP fitting."""
    logger.info("Running PySCF (HF/6-31G*) in WSL for RESP...")
    
    # Extract filename without extension for molden output
    base_name = os.path.splitext(os.path.basename(ligand_path_wsl))[0]
    molden_name = f"{base_name}_hf.molden"
    xyz_name = f"{base_name}_qm.xyz"
    
    # Strategy: convert to XYZ first for robustness
    # We use obabel - but for PySCF we need a clean XYZ
    xyz_cmd = f"obabel '{ligand_path_wsl}' -oxyz -O '{xyz_name}' 2>/dev/null"
    xyz_res = run_wsl(xyz_cmd, cwd=output_dir)
    xyz_path = os.path.join(output_dir, xyz_name)
    if xyz_res.returncode != 0 or not os.path.exists(xyz_path) or os.path.getsize(xyz_path) == 0:
        return {"error": f"OpenBabel XYZ conversion failed: {summarize_process_output(xyz_res.stdout, xyz_res.stderr)}"}
    
    pyscf_script = f"""
import os, sys
from pyscf import gto, scf
from pyscf.tools import molden as molden_tool

def parse_xyz(path):
    atoms = []
    with open(path) as f: lines = f.readlines()
    # Skip potential blank lines at end
    lines = [l for l in lines if l.strip()]
    n_atoms = int(lines[0].strip())
    for i in range(2, 2 + n_atoms):
        p = lines[i].split()
        atoms.append((p[0], float(p[1]), float(p[2]), float(p[3])))
    return atoms

try:
    atoms = parse_xyz("{xyz_name}")
    atom_str = "; ".join(f"{{e}} {{x}} {{y}} {{z}}" for e, x, y, z in atoms)
    mol = gto.Mole()
    mol.atom, mol.basis, mol.charge, mol.spin = atom_str, '6-31g*', {charge}, {spin - 1}
    mol.build()
    mf = scf.UHF(mol) if {spin - 1} > 0 else scf.RHF(mol)
    mf.kernel()
    if not mf.converged:
        raise RuntimeError("SCF did not converge under HF/6-31G*.")
    with open('{molden_name}', 'w') as f:
        molden_tool.header(mol, f)
        molden_tool.orbital_coeff(mol, f, mf.mo_coeff, ene=mf.mo_energy, occ=mf.mo_occ)
    print("MOLDEN_OK")
except Exception as e:
    print(f"PYSCF_ERROR: {{e}}")
    sys.exit(1)
"""
    script_path = os.path.join(output_dir, "run_pyscf.py")
    write_file(script_path, pyscf_script)
    r = run_wsl(f"python3 run_pyscf.py", cwd=output_dir)
    
    if r.returncode != 0 or "MOLDEN_OK" not in r.stdout:
        return {"error": f"PySCF failed: {summarize_process_output(r.stdout, r.stderr)}"}

    molden_path = os.path.join(output_dir, molden_name)
    if not os.path.exists(molden_path) or os.path.getsize(molden_path) == 0:
        return {"error": "PySCF completed but did not produce a valid MOLDEN file."}
        
    return {"status": "success", "molden": molden_name}
