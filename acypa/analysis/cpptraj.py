import os
import re

from ..utils.system import run_wsl, summarize_process_output, win_to_wsl, write_file


def _sanitize_name(name):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_") or "metric"


def _run_cpptraj_job(prmtop_path, traj_path, output_dir, name, action_lines):
    script_path = os.path.join(output_dir, f"{_sanitize_name(name)}.cpptraj.in")
    content = "\n".join(
        [
            f"parm {win_to_wsl(prmtop_path)}",
            f"trajin {win_to_wsl(traj_path)}",
            "autoimage",
            *action_lines,
            "run",
            "quit",
            "",
        ]
    )
    write_file(script_path, content)
    result = run_wsl(f"cpptraj -i {win_to_wsl(script_path)}", cwd=output_dir)
    return result, script_path


def run_cpptraj_analysis(prmtop_path, traj_path, output_dir, analysis_config):
    os.makedirs(output_dir, exist_ok=True)
    hbond_options = []
    if analysis_config.get("hbond_donor_mask"):
        hbond_options.append(f"donormask {analysis_config['hbond_donor_mask']}")
    if analysis_config.get("hbond_acceptor_mask"):
        hbond_options.append(f"acceptormask {analysis_config['hbond_acceptor_mask']}")
    if analysis_config.get("hbond_include_solvent"):
        hbond_options.append(f"solventdonor {analysis_config['hbond_solvent_donor_mask']}")
        hbond_options.append(f"solventacceptor {analysis_config['hbond_solvent_acceptor_mask']}")

    jobs = [
        (
            "rmsd",
            [
                f"rms protein_rmsd {analysis_config['protein_mask']} first out {win_to_wsl(os.path.join(output_dir, 'rmsd.dat'))}",
            ],
            "rmsd.dat",
        ),
        (
            "rmsf",
            [
                f"atomicfluct out {win_to_wsl(os.path.join(output_dir, 'rmsf.dat'))} {analysis_config['protein_mask']} byres",
            ],
            "rmsf.dat",
        ),
        (
            "sasa",
            [
                f"surf {analysis_config['protein_mask']} out {win_to_wsl(os.path.join(output_dir, 'sasa.dat'))}",
            ],
            "sasa.dat",
        ),
        (
            "heme_sasa",
            [
                f"surf {analysis_config['heme_mask']} out {win_to_wsl(os.path.join(output_dir, 'heme_sasa.dat'))}",
            ],
            "heme_sasa.dat",
        ),
        (
            "rg",
            [
                f"radgyr {analysis_config['protein_mask']} out {win_to_wsl(os.path.join(output_dir, 'rg.dat'))}",
            ],
            "rg.dat",
        ),
        (
            "heme_rmsd",
            [
                f"rms heme_rmsd {analysis_config['heme_mask']} first out {win_to_wsl(os.path.join(output_dir, 'heme_rmsd.dat'))}",
            ],
            "heme_rmsd.dat",
        ),
        (
            "fe_s_distance",
            [
                f"distance fe_s {analysis_config['fe_atom_mask']} {analysis_config['cys_s_mask']} out {win_to_wsl(os.path.join(output_dir, 'fe_s_distance.dat'))}",
            ],
            "fe_s_distance.dat",
        ),
        (
            "hbond_count",
            [
                f"hbond HB {analysis_config['hbond_mask']} out {win_to_wsl(os.path.join(output_dir, 'hbond_count.dat'))} avgout {win_to_wsl(os.path.join(output_dir, 'hbond_avg.dat'))} series {' '.join(hbond_options)}".strip(),
            ],
            "hbond_count.dat",
        ),
    ]

    if analysis_config.get("substrate_reactive_atom_mask"):
        jobs.append(
            (
                "fe_substrate_distance",
                [
                    f"distance fe_substrate {analysis_config['fe_atom_mask']} {analysis_config['substrate_reactive_atom_mask']} out {win_to_wsl(os.path.join(output_dir, 'fe_substrate_distance.dat'))}",
                ],
                "fe_substrate_distance.dat",
            )
        )

    if analysis_config.get("fe_o_mask"):
        jobs.append(
            (
                "fe_o_distance",
                [
                    f"distance fe_o {analysis_config['fe_atom_mask']} {analysis_config['fe_o_mask']} out {win_to_wsl(os.path.join(output_dir, 'fe_o_distance.dat'))}",
                ],
                "fe_o_distance.dat",
            )
        )

    distance_pair_files = {}
    for label, pair in (analysis_config.get("distance_pairs") or {}).items():
        mask1 = pair.get("mask1")
        mask2 = pair.get("mask2")
        if not (mask1 and mask2):
            warnings = f"{label} distance pair is missing mask1 or mask2"
            jobs.append((f"{label}_distance_invalid", [f"# {warnings}"], "__skip__"))
            continue
        filename = f"{_sanitize_name(label)}_distance.dat"
        jobs.append(
            (
                f"{label}_distance",
                [
                    f"distance {_sanitize_name(label)} out {win_to_wsl(os.path.join(output_dir, filename))} {mask1} {mask2}",
                ],
                filename,
            )
        )

    data_files = {}
    warnings = []
    scripts = {}
    for name, action_lines, expected_name in jobs:
        if expected_name == "__skip__":
            warnings.append(action_lines[0].lstrip("# ").strip())
            continue
        result, script_path = _run_cpptraj_job(prmtop_path, traj_path, output_dir, name, action_lines)
        scripts[name] = script_path
        expected_path = os.path.join(output_dir, expected_name)
        if result.returncode != 0 or not os.path.exists(expected_path):
            warnings.append(
                f"{name} analysis failed: {summarize_process_output(result.stdout, result.stderr)}"
            )
            continue
        data_files[name] = expected_path
        if name.endswith("_distance") and name not in {"fe_s_distance", "fe_substrate_distance", "fe_o_distance"}:
            label = name[: -len("_distance")]
            distance_pair_files[label] = expected_path

    return {
        "status": "success",
        "data_files": data_files,
        "distance_pair_files": distance_pair_files,
        "warnings": warnings,
        "scripts": scripts,
    }


def run_optional_mmpbsa(traj_path, output_dir, analysis_config):
    if not analysis_config.get("run_mmpbsa"):
        return {"status": "skipped", "message": "MM/PBSA disabled in config."}

    complex_top = analysis_config.get("mmpbsa_complex_topology")
    receptor_top = analysis_config.get("mmpbsa_receptor_topology")
    ligand_top = analysis_config.get("mmpbsa_ligand_topology")
    if not (complex_top and receptor_top and ligand_top):
        return {
            "status": "skipped",
            "message": "MM/PBSA requested but receptor/ligand topologies were not provided.",
        }

    mmpbsa_input = analysis_config.get("mmpbsa_input")
    if not mmpbsa_input:
        mmpbsa_input = os.path.join(output_dir, "mmpbsa.in")
        write_file(
            mmpbsa_input,
            "&general\n  startframe=1, interval=1,\n/\n&gb\n  igb=5, saltcon=0.150,\n/\n",
        )

    result_path = os.path.join(output_dir, "FINAL_RESULTS_MMPBSA.dat")
    command = (
        f"MMPBSA.py -O -i {win_to_wsl(mmpbsa_input)} "
        f"-cp {win_to_wsl(complex_top)} "
        f"-rp {win_to_wsl(receptor_top)} "
        f"-lp {win_to_wsl(ligand_top)} "
        f"-y {win_to_wsl(traj_path)} "
        f"-o {win_to_wsl(result_path)}"
    )
    res = run_wsl(command, cwd=output_dir, timeout=7200)
    if res.returncode != 0 or not os.path.exists(result_path):
        return {
            "status": "error",
            "message": summarize_process_output(res.stdout, res.stderr),
        }
    return {
        "status": "success",
        "result": result_path,
    }
