import os
import logging
from ..qm.pyscf_bridge import run_pyscf_resp_wsl
from ..utils.system import run_wsl, summarize_process_output, win_to_wsl
from .utils import inject_resp_to_mol2

logger = logging.getLogger(__name__)

class LigandParameterizer:
    """Handles ligand parameterization with GAFF2 and PySCF/Multiwfn RESP charges."""
    
    def __init__(self, multiwfn_bin=None):
        self.multiwfn_bin = win_to_wsl(multiwfn_bin or os.environ.get("MULTIWFN_BIN", "Multiwfn_noGUI"))

    def run(self, ligand_path, output_dir, charge=0, spin=1, res_name='LIG'):
        """Full parameterization pipeline."""
        os.makedirs(output_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(ligand_path))[0]
        
        abs_ligand = os.path.abspath(ligand_path)
        wsl_ligand = win_to_wsl(abs_ligand)
        
        # Determine input format for antechamber
        ext = os.path.splitext(ligand_path)[1].lower()[1:]
        if ext == 'sdf': fi = 'sdf'
        elif ext == 'mol2': fi = 'mol2'
        elif ext == 'pdb': fi = 'pdb'
        else: fi = 'mol2' # Default

        # 1. Antechamber for Initial GAFF2 Typing
        logger.info("[1] Antechamber: GAFF2 atom typing...")
        mol2_gaff2 = f"{base_name}_gaff2.mol2"
        cmd_ant = (f"antechamber -i '{wsl_ligand}' -fi {fi} -o '{mol2_gaff2}' -fo mol2 "
                   f"-c bcc -s 2 -at gaff2 -nc {charge} -rn {res_name} -pf y")
        ant_res = run_wsl(cmd_ant, cwd=output_dir)
        mol2_gaff2_path = os.path.join(output_dir, mol2_gaff2)
        if ant_res.returncode != 0 or not os.path.exists(mol2_gaff2_path):
            return {"error": f"Antechamber failed: {summarize_process_output(ant_res.stdout, ant_res.stderr)}"}
        
        # 2. RESP via PySCF + Multiwfn
        logger.info("[2] PySCF + Multiwfn: High-precision RESP charges...")
        p_res = run_pyscf_resp_wsl(wsl_ligand, output_dir, charge, spin)
        if "error" in p_res:
            logger.error(f"QM calculation failed: {p_res['error']}")
            return p_res
        
        # Multiwfn RESP Fitting command
        # Input sequence: 7 (population) -> 18 (RESP) -> 1 (Standard fitting) -> y (save) -> 0 (finish) -> 0 (finish) -> q (quit)
        m_cmd = f"printf '7\\n18\\n1\\ny\\n0\\n0\\nq\\n' | '{self.multiwfn_bin}' {p_res['molden']}"
        m_res = run_wsl(m_cmd, cwd=output_dir)
        if m_res.returncode != 0:
            return {"error": f"Multiwfn RESP fitting failed: {summarize_process_output(m_res.stdout, m_res.stderr)}"}
        
        # Multiwfn usually outputs a file with same base name + .chg
        chg_file = os.path.join(output_dir, p_res['molden'].replace('.molden', '.chg'))
        if not os.path.exists(chg_file):
            # Fallback search for any .chg file in output dir
            chgs = [f for f in os.listdir(output_dir) if f.endswith('.chg')]
            if chgs: chg_file = os.path.join(output_dir, chgs[0])
            else: return {"error": "Multiwfn RESP fitting failed to produce .chg file."}

        # Merge RESP charges into MOL2
        logger.info("[3] Injecting RESP charges into MOL2...")
        mol2_resp = f"{base_name}_resp.mol2"
        n_injected = inject_resp_to_mol2(mol2_gaff2_path, 
                                        chg_file, 
                                        os.path.join(output_dir, mol2_resp))
        if n_injected <= 0:
            return {"error": "RESP charge injection failed: no atoms were updated."}
        logger.info(f"Successfully injected {n_injected} RESP charges.")
            
        # 4. parmchk2 for frcmod
        logger.info("[4] parmchk2: generating frcmod...")
        frcmod = f"{base_name}.frcmod"
        cmd_parm = f"parmchk2 -i '{mol2_resp}' -f mol2 -o '{frcmod}' -s gaff2"
        parm_res = run_wsl(cmd_parm, cwd=output_dir)
        frcmod_path = os.path.join(output_dir, frcmod)
        if parm_res.returncode != 0 or not os.path.exists(frcmod_path):
            return {"error": f"parmchk2 failed: {summarize_process_output(parm_res.stdout, parm_res.stderr)}"}
        
        return {
            "status": "success",
            "mol2": os.path.join(output_dir, mol2_resp), 
            "frcmod": frcmod_path,
            "res_name": res_name
        }
