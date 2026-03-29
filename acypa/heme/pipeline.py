import os
import math
import numpy as np
import logging
from ..utils.system import run_wsl, win_to_wsl, write_file

logger = logging.getLogger(__name__)

def kabsch_superpose(P, Q):
    """
    The Kabsch algorithm to find the optimal rotation matrix that minimizes the RMSD.
    P: (N, 3) matrix of coordinates.
    Q: (N, 3) matrix of reference coordinates.
    Returns: Rotation matrix R, and RMSD.
    """
    P = np.array(P)
    Q = np.array(Q)
    # 1. Translate to origin
    centroid_P = np.mean(P, axis=0)
    centroid_Q = np.mean(Q, axis=0)
    P_c = P - centroid_P
    Q_c = Q - centroid_Q
    
    # 2. Compute covariance matrix
    H = np.dot(P_c.T, Q_c)
    
    # 3. SVD
    U, S, Vt = np.linalg.svd(H)
    
    # 4. Rotation matrix
    R = np.dot(Vt.T, U.T)
    
    # Special case for reflection
    if np.linalg.det(R) < 0:
        Vt[-1,:] *= -1
        R = np.dot(Vt.T, U.T)
        
    # Calculate RMSD
    P_rotated = np.dot(P_c, R)
    rmsd = np.sqrt(np.mean(np.sum((P_rotated - Q_c)**2, axis=1)))
    
    return R, centroid_P, centroid_Q, rmsd

class HemePipeline:
    """Automates Heme parameterization and PDB preparation using Shahrokh protocol."""
    
    # Default atom mapping from common Heme residue (e.g., HEM/L01) to Shahrokh HEM.mol2
    # This is a fallback if spatial mapping fails
    HEM_ATOM_DATA = {
        'NC': (2.870, -0.982, -0.754), 'C1C': (4.206, -0.781, -0.528), 'C4C': (2.714, -2.307, -1.022),
        'C2C': (4.934, -2.026, -0.645), 'C3C': (3.998, -2.997, -0.943), 'CHD': (1.504, -2.923, -1.333),
        'C1D': (0.275, -2.292, -1.459), 'ND': (0.033, -0.964, -1.253), 'C4D': (-1.296, -0.768, -1.518),
        'C3D': (-1.935, -2.029, -1.895), 'C2D': (-0.948, -2.976, -1.850), 'CHA': (-1.955, 0.450, -1.421),
        'C1A': (-1.380, 1.648, -1.011), 'C2A': (-2.100, 2.914, -0.894), 'C4A': (0.084, 3.125, -0.329),
        'NA': (-0.069, 1.806, -0.659), 'C3A': (-1.181, 3.829, -0.460), 'CHB': (1.271, 3.739, 0.037),
        'C1B': (2.526, 3.138, 0.092), 'C2B': (3.750, 3.834, 0.427), 'NB': (2.778, 1.824, -0.184),
        'C4B': (4.122, 1.646, -0.047), 'CHC': (4.792, 0.439, -0.209), 'FE': (1.406, 0.441, -0.796),
        'C3B': (4.763, 2.899, 0.343), 'CAB': (6.194, 3.060, 0.540), 'CBB': (6.836, 3.995, 1.265),
        'CAC': (4.181, -4.419, -1.186), 'CBC': (5.182, -5.213, -0.760), 'CMB': (3.863, 5.294, 0.744),
        'CMC': (6.418, -2.183, -0.508), 'CMD': (-1.057, -4.446, -2.127), 'CMA': (-1.392, 5.286, -0.173),
        'CAA': (-3.554, 3.168, -1.187), 'CAD': (-3.395, -2.247, -2.184), 'CBA': (-4.444, 3.191, 0.074),
        'CBD': (-4.217, -2.482, -0.900), 'CGD': (-5.729, -2.615, -1.120), 'CGA': (-5.891, 3.581, -0.216),
        'O1A': (-6.681, 3.739, 0.763), 'O1D': (-6.463, -2.631, -0.087), 'O2A': (-6.295, 3.767, -1.392),
        'O2D': (-6.192, -2.733, -2.281), 'O1': (1.689, 0.783, -2.374),
    }

    def __init__(self, params_base=None):
        self.params_base = params_base or os.path.join(os.path.dirname(__file__), "..", "..", "data", "heme_params")
        self.params_base = os.path.abspath(self.params_base)

    def detect_state(self, fe_coord, protein_atoms, heme_res_atoms):
        """Auto-detect Heme state based on oxygen presence and distance."""
        # Simple detection: look for oxygen bound to Fe
        # 1. CPDI: Fe=O (~1.6 A)
        # 2. DIOXY: Fe-O-O (~1.8-2.0 A)
        # 3. IC6: Fe-H2O (~2.1 A) or Nothing axial
        
        # In a real pipeline, we'd search all residues near Fe
        # For simplicity, we assume the user provides a PDB where Heme state is already "modeled"
        # We search within 2.5 A of Fe
        found_o = False
        o_count = 0
        min_dist = 999
        
        for name, coord in heme_res_atoms.items():
            if name.startswith('O') and name != 'FE':
                dist = np.linalg.norm(np.array(coord) - np.array(fe_coord))
                if dist < 2.5:
                    found_o = True
                    o_count += 1
                    min_dist = min(min_dist, dist)
        
        if found_o:
            if o_count >= 2: return "DIOXY"
            if min_dist < 1.7: return "CPDI"
            return "IC6"
        return "IC6"

    def run(self, pdb_path, output_dir, axial_cys_resid, heme_resname="HEM", state=None):
        """Full preparation pipeline."""
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Processing PDB: {pdb_path} to {output_dir}")
        
        # 1. Parse PDB
        protein_lines = []
        heme_lines = []
        with open(pdb_path, 'r') as f:
            for line in f:
                if line.startswith(("ATOM", "HETATM")):
                    resname = line[17:20].strip()
                    if resname == heme_resname:
                        heme_lines.append(line)
                    else:
                        protein_lines.append(line)
        
        # 2. Heme Mapping logic
        l01_atoms = {}
        for line in heme_lines:
            name = line[12:16].strip()
            coord = (float(line[30:38]), float(line[38:46]), float(line[46:54]))
            l01_atoms[name] = coord
        
        fe_name = [k for k in l01_atoms.keys() if 'FE' in k.upper()][0]
        fe_coord = l01_atoms[fe_name]
        
        if state is None:
            state = self.detect_state(fe_coord, None, l01_atoms)
            logger.info(f"Auto-detected Heme State: {state}")
        
        # Spatial Mapping (L01 -> HEM protocol)
        mapping = self._map_atoms(l01_atoms)
        
        # 3. Write Prepared PDB
        clean_pdb = os.path.join(output_dir, "cyp_prepared.pdb")
        cys_resid_new = None
        hem_resid_new = None
        
        with open(clean_pdb, 'w') as f:
            atom_serial = 1
            # Write Protein (rename CYS -> CYP)
            for line in protein_lines:
                resname = line[17:20].strip()
                resid = int(line[22:26])
                atom_name = line[12:16].strip()
                if resid == axial_cys_resid:
                    line = line[:17] + "CYP" + line[20:]
                    cys_resid_new = resid
                    if atom_name == "HG": continue # Shahrokh protocol uses S- anion
                
                new_line = line[:6] + f"{atom_serial:5d}" + line[11:]
                f.write(new_line)
                atom_serial += 1
            f.write("TER\n")
            
            # Write Heme
            hem_resid_new = 1 # We'll just put it as residue 1 in its chain
            for line in heme_lines:
                old_name = line[12:16].strip()
                if old_name in mapping:
                    new_name = mapping[old_name]
                    formatted_name = f" {new_name:<3s}" if len(new_name) < 4 else f"{new_name:<4s}"
                    new_line = (f"HETATM{atom_serial:5d} {formatted_name} HEM B   1    "
                               f"{line[30:54]}  1.00  0.00\n")
                    f.write(new_line)
                    atom_serial += 1
            f.write("TER\nEND\n")
            
        # 4. Generate TLeap
        self.generate_tleap(output_dir, "cyp_prepared.pdb", state, cys_resid_new, "1")
        
        return {"state": state, "pdb": clean_pdb, "output_dir": output_dir}

    def _map_atoms(self, source_atoms):
        """Map source PDB atom names to Shahrokh convention using Kabsch and spatial distance."""
        # 1. Align using Fe and Nitrogen atoms (N pyrrole)
        fe_src_name = [k for k in source_atoms.keys() if 'FE' in k.upper()][0]
        n_src_names = [k for k in source_atoms.keys() if k.startswith('N')][:4]
        
        src_subset = [source_atoms[fe_src_name]] + [source_atoms[n] for n in n_src_names]
        ref_subset = [self.HEM_ATOM_DATA['FE']] + [self.HEM_ATOM_DATA[n] for n in ['NA', 'NB', 'NC', 'ND']]
        
        R, cP, cQ, rmsd = kabsch_superpose(src_subset, ref_subset)
        
        # Map all
        mapping = {}
        used_ref = set()
        for src_name, src_coord in source_atoms.items():
            # Rotate and translate src_coord to ref frame
            src_c = np.array(src_coord) - cP
            src_rot = np.dot(src_c, R) + cQ
            
            # Find nearest in HEM_ATOM_DATA
            best_dist = 999
            best_ref = None
            for ref_name, ref_coord in self.HEM_ATOM_DATA.items():
                dist = np.linalg.norm(src_rot - np.array(ref_coord))
                if dist < best_dist:
                    best_dist = dist
                    best_ref = ref_name
            if best_ref:
                mapping[src_name] = best_ref
                used_ref.add(best_ref)
        return mapping

    def generate_tleap(self, output_dir, pdb_name, state, cys_resid, hem_resid):
        """Generates tleap input with Fe-S bonding."""
        params_dir = os.path.join(self.params_base, state)
        wsl_params = win_to_wsl(params_dir)
        content = f"""
source leaprc.protein.ff19SB
source leaprc.gaff2
source leaprc.water.tip3p
loadamberparams {wsl_params}/{state}.frcmod
loadmol2 {wsl_params}/HEM.mol2
loadmol2 {wsl_params}/CYP.mol2
mol = loadpdb {pdb_name}
# Bond axial CYS (CYP) SG to HEM FE
bond mol.{cys_resid}.SG mol.B.{hem_resid}.FE
solvateoct mol TIP3PBOX 12.0
addionsrand mol Na+ 0
addionsrand mol Cl- 0
saveamberparm mol complex.prmtop complex.inpcrd
savepdb mol complex_solv.pdb
quit
"""
        write_file(os.path.join(output_dir, "tleap.in"), content)
