import os
import logging
from _bootstrap import bootstrap_repo

bootstrap_repo()

from acypa.skills.amber_skills import (
    skill_prepare_cyp_heme,
    skill_parameterize_ligand,
    skill_build_complex_and_solvate,
    skill_run_amber_md
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def full_auto_cyp_md_pipeline(pdb_path, ligand_path, axial_cys_resid, output_dir):
    """
    Complete end-to-end setup and MD run for a Cytochrome P450 system with a ligand.
    """
    logger = logging.getLogger("AutoCYPAmber")
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Parameterize Heme and Protein
    logger.info("--- Phase 1: Heme & Protein Preparation ---")
    heme_dir = os.path.join(output_dir, "prep_heme")
    heme_res = skill_prepare_cyp_heme(pdb_path, heme_dir, axial_cys_resid)
    logger.info(f"Heme preparation complete. State detected: {heme_res.get('state')}")

    # 2. Parameterize Ligand with PySCF RESP
    logger.info("--- Phase 2: Ligand RESP Parameterization ---")
    lig_dir = os.path.join(output_dir, "prep_lig")
    lig_res = skill_parameterize_ligand(ligand_path, lig_dir, charge=0)
    
    if "error" in lig_res:
        logger.error(f"Ligand setup failed: {lig_res['error']}")
        return

    # 3. Build Complex via tleap
    logger.info("--- Phase 3: Final System Assembly & Solvation ---")
    complex_dir = os.path.join(output_dir, "complex")
    build_res = skill_build_complex_and_solvate(
        cyp_pdb=heme_res['pdb'],
        lig_mol2=lig_res['mol2'],
        lig_frcmod=lig_res['frcmod'],
        heme_state=heme_res['state'],
        cys_resid=axial_cys_resid,
        output_dir=complex_dir
    )

    if build_res.get("status") != "success":
        logger.error("Complex building failed.")
        return
        
    logger.info(f"Complex topologies generated: {build_res['prmtop']}")

    # 4. Run MD Protocol
    logger.info("--- Phase 4: Automated AMBER MD Run ---")
    md_dir = os.path.join(output_dir, "md_run")
    os.makedirs(md_dir, exist_ok=True)
    
    md_res = skill_run_amber_md(
        work_dir=md_dir,
        top_file=build_res['prmtop'],
        crd_file=build_res['inpcrd'],
        engine="pmemd.cuda"
    )
    
    if md_res.get("status") == "success":
        logger.info(f"MD Simulation Pipeline Completed Successfully!")
        if md_res.get("trajectory"):
            logger.info(f"Trajectory: {md_res['trajectory']}")
        if md_res.get("restart"):
            logger.info(f"Restart: {md_res['restart']}")
    else:
        logger.error(f"MD Simulation Pipeline Failed: {md_res}")

if __name__ == "__main__":
    # Example usage (placeholders)
    # full_auto_cyp_md_pipeline("2CPP.pdb", "camphor.sdf", 357, "./auto_cyp_run")
    print("AutoCYPAmber Example: Call full_auto_cyp_md_pipeline with your inputs.")
