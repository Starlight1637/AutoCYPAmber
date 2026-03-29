import json
import os
import shutil

from ..analysis import analyze_md_stability, load_case_config
from ..deploy.environment import validate_runtime_environment
from ..reporting import render_markdown_bundle
from ..simulation.amber_md import AmberMDRunner
from ..skills.amber_skills import (
    skill_build_complex_and_solvate,
    skill_parameterize_ligand,
    skill_prepare_cyp_heme,
)


def _stage_dirs(output_root):
    return {
        "prep_heme": os.path.join(output_root, "prep_heme"),
        "prep_lig": os.path.join(output_root, "prep_lig"),
        "complex": os.path.join(output_root, "complex"),
        "md_run": os.path.join(output_root, "md_run"),
        "analysis": os.path.join(output_root, "analysis"),
        "report": os.path.join(output_root, "report"),
    }


def _write_json(path, payload):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def prepare_local_smoke_case(config_path):
    config = load_case_config(config_path)
    output_root = config["paths"]["output_root"]
    os.makedirs(output_root, exist_ok=True)
    dirs = _stage_dirs(output_root)
    for path in dirs.values():
        os.makedirs(path, exist_ok=True)

    missing = []
    if not config.get("protein_pdb") or not os.path.exists(config["protein_pdb"]):
        missing.append(f"protein_pdb -> {config.get('protein_pdb', '')}")
    if not config.get("ligand_path") or not os.path.exists(config["ligand_path"]):
        missing.append(f"ligand_path -> {config.get('ligand_path', '')}")
    if not config.get("axial_cys_resid"):
        missing.append("axial_cys_resid")

    resolved_config_path = os.path.join(output_root, "case_config.json")
    _write_json(resolved_config_path, config)

    manifest = {
        "status": "error" if missing else "success",
        "config_path": resolved_config_path,
        "case_name": config["case_name"],
        "output_root": output_root,
        "stage_dirs": dirs,
        "missing": missing,
    }
    _write_json(os.path.join(output_root, "case_manifest.json"), manifest)
    return manifest


def _failure(stage, message, artifacts=None, warnings=None):
    return {
        "status": "error",
        "failed_stage": stage,
        "message": message,
        "artifacts": artifacts or {},
        "warnings": warnings or [],
    }


def _write_server_handoff(output_root, config, artifacts):
    handoff = {
        "mode": "server-production",
        "case_name": config["case_name"],
        "artifacts": {
            "prmtop": artifacts.get("prmtop", ""),
            "inpcrd": artifacts.get("inpcrd", ""),
            "restart": artifacts.get("restart", ""),
            "trajectory": artifacts.get("trajectory", ""),
            "analysis_config": os.path.join(output_root, "case_config.json"),
            "md_input_dir": os.path.join(output_root, "md_run", "md_input"),
        },
        "notes": [
            "Use the local-smoke topology and restart as the server production starting point.",
            "For long production MD, switch back to the full production protocol rather than the shortened smoke profile.",
            "Reuse the same analysis config for post-production heme stability analysis.",
        ],
    }
    handoff_path = os.path.join(output_root, "server_handoff.json")
    _write_json(handoff_path, handoff)
    return handoff_path


def run_local_smoke_pipeline(config_path):
    config = load_case_config(config_path)
    prep = prepare_local_smoke_case(config_path)
    if prep["status"] != "success":
        return _failure("prepare_local_smoke_case", f"Missing required inputs: {prep['missing']}", warnings=prep["missing"])

    runtime = validate_runtime_environment(engine=config["md"]["engine"])
    warnings = list(runtime.get("recommendations", []))
    analysis_blockers = [name for name in runtime.get("optional_missing", []) if name == "cpptraj"]
    if runtime.get("status") != "success" or analysis_blockers:
        return _failure(
            "runtime_validation",
            runtime.get("message", "Runtime validation failed.") if not analysis_blockers else "Missing required analysis dependency for local smoke execution.",
            warnings=warnings + runtime.get("missing", []) + analysis_blockers,
        )

    dirs = prep["stage_dirs"]
    artifacts = {}

    heme_res = skill_prepare_cyp_heme(
        pdb_path=config["protein_pdb"],
        output_dir=dirs["prep_heme"],
        axial_cys_resid=config["axial_cys_resid"],
        state=config["heme"].get("state"),
    )
    if not heme_res.get("pdb"):
        return _failure("heme_preparation", f"Heme preparation failed: {heme_res}", artifacts=artifacts, warnings=warnings)
    artifacts["prepared_pdb"] = heme_res["pdb"]

    lig_res = skill_parameterize_ligand(
        ligand_path=config["ligand_path"],
        output_dir=dirs["prep_lig"],
        charge=config["ligand"]["charge"],
        spin=config["ligand"]["spin"],
        res_name=config["ligand"]["res_name"],
    )
    if lig_res.get("status") != "success":
        return _failure("ligand_parameterization", lig_res.get("error", str(lig_res)), artifacts=artifacts, warnings=warnings)
    artifacts["ligand_mol2"] = lig_res["mol2"]
    artifacts["ligand_frcmod"] = lig_res["frcmod"]

    complex_res = skill_build_complex_and_solvate(
        cyp_pdb=heme_res["pdb"],
        lig_mol2=lig_res["mol2"],
        lig_frcmod=lig_res["frcmod"],
        heme_state=heme_res["state"],
        cys_resid=config["axial_cys_resid"],
        output_dir=dirs["complex"],
    )
    if complex_res.get("status") != "success":
        return _failure("complex_build", complex_res.get("message", str(complex_res)), artifacts=artifacts, warnings=warnings)
    artifacts["prmtop"] = complex_res["prmtop"]
    artifacts["inpcrd"] = complex_res["inpcrd"]

    stage_overrides = {
        key: value
        for key, value in config["md"].items()
        if key in {"min_maxcyc", "min_ncyc", "heat_nstlim", "equil_nstlim", "prod_nstlim"}
    }
    md_runner = AmberMDRunner(
        work_dir=dirs["md_run"],
        top_file=complex_res["prmtop"],
        crd_file=complex_res["inpcrd"],
        engine=config["md"]["engine"],
        profile=config["md"].get("profile", "local_smoke"),
        stage_overrides=stage_overrides,
    )
    md_res = md_runner.run_protocol()
    if md_res.get("status") != "success":
        return _failure("md_run", md_res.get("error", str(md_res)), artifacts=artifacts, warnings=warnings)
    artifacts["trajectory"] = md_res["trajectory"]
    artifacts["restart"] = md_res["restart"]

    analysis_res = analyze_md_stability(
        run_dir=config["paths"]["output_root"],
        config_path=os.path.join(config["paths"]["output_root"], "case_config.json"),
        prmtop_path=complex_res["prmtop"],
        traj_path=md_res["trajectory"],
        restart_path=md_res["restart"],
        output_dir=dirs["analysis"],
    )
    if analysis_res.get("status") != "success":
        return _failure("analysis", analysis_res.get("message", str(analysis_res)), artifacts=artifacts, warnings=warnings)
    warnings.extend(analysis_res.get("warnings", []))
    artifacts["analysis_dir"] = analysis_res["analysis_dir"]
    artifacts["report_md"] = analysis_res["report_md"]

    report_res = render_markdown_bundle(
        markdown_path=analysis_res["report_md"],
        output_dir=dirs["report"],
        include_analysis=False,
        metadata_title=config["case_name"],
    )
    if report_res.get("status") != "success":
        return _failure("report_render", report_res.get("message", str(report_res)), artifacts=artifacts, warnings=warnings)
    artifacts["report_pdf"] = report_res["pdf"]
    artifacts["report_docx"] = report_res["docx"]

    artifacts["server_handoff"] = _write_server_handoff(config["paths"]["output_root"], config, artifacts)
    if os.path.abspath(config_path) != os.path.abspath(os.path.join(config["paths"]["output_root"], "case_config.json")):
        shutil.copyfile(config_path, os.path.join(config["paths"]["output_root"], "case_config.source"))

    return {
        "status": "success",
        "failed_stage": "",
        "warnings": warnings,
        "artifacts": artifacts,
    }
