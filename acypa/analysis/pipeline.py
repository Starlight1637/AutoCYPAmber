import json
import os

from ..utils.system import write_file
from .config import load_case_config
from .cpptraj import run_cpptraj_analysis, run_optional_mmpbsa
from .plots import (
    plot_free_energy_landscape,
    plot_key_residue_distances,
    plot_rmsf,
    plot_series,
    summarize_mmpbsa,
    summarize_series,
)


def _default_artifact_paths(run_dir):
    candidates = {
        "prmtop": [
            os.path.join(run_dir, "complex", "complex.prmtop"),
            os.path.join(run_dir, "prep_heme", "complex.prmtop"),
        ],
        "trajectory": [
            os.path.join(run_dir, "md_run", "md_output", "08.nc"),
            os.path.join(run_dir, "md_run", "md_output", "02.nc"),
        ],
        "restart": [
            os.path.join(run_dir, "md_run", "md_output", "08.rst7"),
            os.path.join(run_dir, "md_run", "md_output", "02.rst7"),
        ],
    }
    resolved = {}
    for key, paths in candidates.items():
        resolved[key] = next((path for path in paths if os.path.exists(path)), "")
    return resolved


def _relative(path, base_dir):
    return os.path.relpath(path, base_dir).replace("\\", "/")


def _build_findings(stats):
    findings = []
    heme_rmsd = stats.get("heme_rmsd")
    if heme_rmsd:
        findings.append(
            f"Heme RMSD averaged {heme_rmsd['mean']:.2f} A and ended at {heme_rmsd['last']:.2f} A across {heme_rmsd['n_points']} frames."
        )
    fe_s = stats.get("fe_s_distance")
    if fe_s:
        findings.append(
            f"Fe-S(Cys) distance averaged {fe_s['mean']:.2f} A with a range of {fe_s['min']:.2f}-{fe_s['max']:.2f} A."
        )
    fe_sub = stats.get("fe_substrate_distance")
    if fe_sub:
        verdict = "close enough to monitor for near-attack frames" if fe_sub["mean"] <= 6.0 else "still relatively distant from the catalytic iron"
        findings.append(
            f"Fe-substrate reactive-atom distance averaged {fe_sub['mean']:.2f} A and remains {verdict}."
        )
    heme_sasa = stats.get("heme_sasa")
    if heme_sasa:
        findings.append(
            f"Heme local SASA averaged {heme_sasa['mean']:.2f} A^2, which helps contextualize pocket exposure during the short smoke run."
        )
    return findings


def _write_markdown_report(report_path, config, plot_paths, stats, warnings, findings, mmpbsa_result):
    lines = [
        f"# {config['case_name']} Stability Report",
        "",
        "## System Summary",
        f"- Mode: `{config.get('mode', 'local-smoke')}`",
        f"- Protein PDB: `{config.get('protein_pdb', '')}`",
        f"- Ligand input: `{config.get('ligand_path', '')}`",
        f"- Axial Cys residue: `{config.get('axial_cys_resid', '')}`",
        f"- MD profile: `{config.get('md', {}).get('profile', 'local_smoke')}`",
        "",
        "## Heme-Centered Conclusions",
    ]
    if findings:
        lines.extend(f"- {item}" for item in findings)
    else:
        lines.append("- No quantitative heme findings could be summarized from the available outputs.")

    lines.extend(["", "## Core Plots"])
    ordered_plot_names = [
        "rmsd",
        "rmsf",
        "sasa",
        "heme_sasa",
        "rg",
        "hbond_count",
        "heme_rmsd",
        "fe_s_distance",
        "fe_substrate_distance",
        "fe_o_distance",
        "distance_pairs",
        "free_energy_landscape",
    ]
    for key in ordered_plot_names:
        path = plot_paths.get(key)
        if path:
            title = key.replace("_", " ").title()
            lines.extend([f"### {title}", f"![{title}]({_relative(path, os.path.dirname(report_path))})", ""])

    lines.extend(["## Metric Summary"])
    for key, values in stats.items():
        lines.append(
            f"- `{key}`: mean `{values['mean']:.3f}`, min `{values['min']:.3f}`, max `{values['max']:.3f}`, final `{values['last']:.3f}`"
        )

    lines.extend(["", "## MM/PBSA"])
    if mmpbsa_result and mmpbsa_result.get("summary"):
        lines.append(f"- Estimated Delta G: `{mmpbsa_result['summary']['delta_total_kcal_mol']:.3f}` kcal/mol")
    else:
        lines.append("- MM/PBSA not available for this run or topology triplet was not provided.")

    lines.extend(
        [
            "",
            "## Caveats",
            "- This phase-1 local smoke profile uses a shortened MD protocol and is intended for pipeline validation, not final scientific claims.",
            "- Heme-centered geometry trends are useful for screening obvious failures, but long production trajectories are still recommended before mechanistic interpretation.",
        ]
    )
    if warnings:
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {warning}" for warning in warnings)

    write_file(report_path, "\n".join(lines) + "\n")


def analyze_md_stability(run_dir, config_path=None, prmtop_path=None, traj_path=None, restart_path=None, output_dir=None):
    run_dir = os.path.abspath(run_dir)
    if config_path:
        config = load_case_config(config_path)
    else:
        config = load_case_config(os.path.join(run_dir, "case_config.json"))

    defaults = _default_artifact_paths(run_dir)
    prmtop_candidate = prmtop_path or defaults["prmtop"]
    traj_candidate = traj_path or defaults["trajectory"]
    restart_candidate = restart_path or defaults["restart"]

    if not prmtop_candidate:
        return {"status": "error", "message": "Topology file not found in the run directory and no override was provided."}
    if not traj_candidate:
        return {"status": "error", "message": "Trajectory file not found in the run directory and no override was provided."}

    prmtop_path = os.path.abspath(prmtop_candidate)
    traj_path = os.path.abspath(traj_candidate)
    restart_path = os.path.abspath(restart_candidate) if restart_candidate else ""

    if not os.path.exists(prmtop_path):
        return {"status": "error", "message": f"Topology file not found: {prmtop_path}"}
    if not os.path.exists(traj_path):
        return {"status": "error", "message": f"Trajectory file not found: {traj_path}"}

    output_dir = os.path.abspath(output_dir or os.path.join(run_dir, "analysis"))
    os.makedirs(output_dir, exist_ok=True)

    cpptraj_res = run_cpptraj_analysis(prmtop_path, traj_path, output_dir, config["analysis"])
    warnings = list(cpptraj_res.get("warnings", []))
    data_files = dict(cpptraj_res.get("data_files", {}))
    distance_pair_files = dict(cpptraj_res.get("distance_pair_files", {}))

    plot_paths = {}
    stats = {}

    metric_plot_specs = {
        "rmsd": ("rmsd.png", "Protein RMSD", "Frame", "RMSD (A)", "second"),
        "sasa": ("sasa.png", "Protein SASA", "Frame", "SASA (A^2)", "second"),
        "heme_sasa": ("heme_sasa.png", "Heme SASA", "Frame", "SASA (A^2)", "second"),
        "rg": ("rg.png", "Radius of Gyration", "Frame", "Rg (A)", "second"),
        "hbond_count": ("hbond_count.png", "Hydrogen Bond Count", "Frame", "Count", "sum_rest"),
        "heme_rmsd": ("heme_rmsd.png", "Heme RMSD", "Frame", "RMSD (A)", "second"),
        "fe_s_distance": ("fe_s_distance.png", "Fe-S(Cys) Distance", "Frame", "Distance (A)", "second"),
        "fe_substrate_distance": ("fe_substrate_distance.png", "Fe-Substrate Distance", "Frame", "Distance (A)", "second"),
        "fe_o_distance": ("fe_o_distance.png", "Fe-O Distance", "Frame", "Distance (A)", "second"),
    }

    for key, spec in metric_plot_specs.items():
        data_path = data_files.get(key)
        if not data_path:
            continue
        filename, title, xlabel, ylabel, mode = spec
        plot_path = plot_series(data_path, os.path.join(output_dir, filename), title, xlabel, ylabel, mode=mode)
        if plot_path:
            plot_paths[key] = plot_path
        summary = summarize_series(data_path, mode=mode)
        if summary:
            stats[key] = summary

    if data_files.get("rmsf"):
        plot_path = plot_rmsf(data_files["rmsf"], os.path.join(output_dir, "rmsf.png"))
        if plot_path:
            plot_paths["rmsf"] = plot_path
        summary = summarize_series(data_files["rmsf"])
        if summary:
            stats["rmsf"] = summary

    if distance_pair_files:
        plot_path = plot_key_residue_distances(distance_pair_files, os.path.join(output_dir, "distance_pairs.png"))
        if plot_path:
            plot_paths["distance_pairs"] = plot_path

    if data_files.get("rmsd") and data_files.get("rg"):
        plot_path = plot_free_energy_landscape(
            data_files["rmsd"],
            data_files["rg"],
            os.path.join(output_dir, "free_energy_landscape.png"),
        )
        if plot_path:
            plot_paths["free_energy_landscape"] = plot_path

    mmpbsa_res = run_optional_mmpbsa(traj_path, output_dir, config["analysis"])
    if mmpbsa_res.get("status") == "error":
        warnings.append(f"MM/PBSA failed: {mmpbsa_res['message']}")
    elif mmpbsa_res.get("status") == "skipped" and config["analysis"].get("run_mmpbsa"):
        warnings.append(mmpbsa_res["message"])
    if mmpbsa_res.get("result"):
        mmpbsa_res["summary"] = summarize_mmpbsa(mmpbsa_res["result"])

    required_metrics = ["rmsd", "rmsf", "sasa", "rg", "hbond_count", "heme_rmsd", "fe_s_distance"]
    required_plots = ["rmsd", "rmsf", "sasa", "rg", "hbond_count", "heme_rmsd", "fe_s_distance", "free_energy_landscape"]
    if config["analysis"].get("substrate_reactive_atom_mask"):
        required_metrics.append("fe_substrate_distance")
        required_plots.append("fe_substrate_distance")
    if config["analysis"].get("fe_o_mask"):
        required_metrics.append("fe_o_distance")
        required_plots.append("fe_o_distance")

    missing_metrics = [name for name in required_metrics if not data_files.get(name)]
    missing_plots = [name for name in required_plots if not plot_paths.get(name)]
    if config["analysis"].get("distance_pairs") and not plot_paths.get("distance_pairs"):
        missing_plots.append("distance_pairs")

    summary_json = os.path.join(output_dir, "analysis_summary.json")
    if missing_metrics or missing_plots:
        with open(summary_json, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "status": "error",
                    "data_files": data_files,
                    "distance_pair_files": distance_pair_files,
                    "plot_paths": plot_paths,
                    "warnings": warnings,
                    "missing_metrics": missing_metrics,
                    "missing_plots": missing_plots,
                },
                handle,
                indent=2,
                ensure_ascii=False,
            )
        missing_bits = []
        if missing_metrics:
            missing_bits.append(f"metrics={missing_metrics}")
        if missing_plots:
            missing_bits.append(f"plots={missing_plots}")
        return {
            "status": "error",
            "message": "Core analysis outputs were not generated: " + "; ".join(missing_bits),
            "analysis_dir": output_dir,
            "data_files": data_files,
            "distance_pair_files": distance_pair_files,
            "plot_paths": plot_paths,
            "warnings": warnings,
            "summary_json": summary_json,
        }

    findings = _build_findings(stats)
    report_path = os.path.join(output_dir, "report.md")
    _write_markdown_report(report_path, config, plot_paths, stats, warnings, findings, mmpbsa_res)

    with open(summary_json, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "status": "success",
                "data_files": data_files,
                "distance_pair_files": distance_pair_files,
                "plot_paths": plot_paths,
                "stats": stats,
                "warnings": warnings,
                "findings": findings,
                "mmpbsa": mmpbsa_res,
            },
            handle,
            indent=2,
            ensure_ascii=False,
        )

    return {
        "status": "success",
        "analysis_dir": output_dir,
        "data_files": data_files,
        "distance_pair_files": distance_pair_files,
        "plot_paths": plot_paths,
        "stats": stats,
        "warnings": warnings,
        "findings": findings,
        "report_md": report_path,
        "summary_json": summary_json,
        "mmpbsa": mmpbsa_res,
        "trajectory": traj_path,
        "restart": restart_path,
        "prmtop": prmtop_path,
    }
