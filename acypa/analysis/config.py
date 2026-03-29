import copy
import json
import os


DEFAULT_CONFIG = {
    "case_name": "local_smoke_case",
    "mode": "local-smoke",
    "protein_pdb": "",
    "ligand_path": "",
    "axial_cys_resid": None,
    "heme": {
        "resname": "HEM",
        "state": None,
    },
    "ligand": {
        "charge": 0,
        "spin": 1,
        "res_name": "LIG",
    },
    "paths": {
        "output_root": "./local_smoke_run",
    },
    "md": {
        "engine": "pmemd.cuda",
        "profile": "local_smoke",
        "min_maxcyc": 500,
        "min_ncyc": 250,
        "heat_nstlim": 2500,
        "equil_nstlim": 2500,
        "prod_nstlim": 5000,
    },
    "analysis": {
        "protein_mask": "!(:WAT,Na+,Cl-,HEM,LIG)&@CA",
        "heme_mask": ":HEM",
        "cys_s_mask": "",
        "fe_atom_mask": ":HEM@FE",
        "fe_o_mask": "",
        "substrate_reactive_atom_mask": "",
        "ligand_mask": ":LIG",
        "hbond_mask": ":HEM,LIG",
        "hbond_donor_mask": "",
        "hbond_acceptor_mask": "",
        "hbond_include_solvent": False,
        "hbond_solvent_donor_mask": ":WAT@O",
        "hbond_solvent_acceptor_mask": ":WAT",
        "key_residue_masks": {},
        "distance_pairs": {},
        "run_mmpbsa": False,
        "mmpbsa_complex_topology": "",
        "mmpbsa_receptor_topology": "",
        "mmpbsa_ligand_topology": "",
        "mmpbsa_input": "",
    },
}


def _deep_merge(base, override):
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_yaml(path):
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise RuntimeError("PyYAML is required to load YAML configs.") from exc
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _load_raw_config(config_path):
    ext = os.path.splitext(config_path)[1].lower()
    if ext == ".json":
        with open(config_path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    if ext in {".yaml", ".yml"}:
        return _load_yaml(config_path)
    raise ValueError(f"Unsupported config format: {config_path}")


def _resolve_path(base_dir, value):
    if not value or not isinstance(value, str):
        return value
    if os.path.isabs(value):
        return os.path.abspath(value)
    if len(value) >= 2 and value[1] == ":":
        return os.path.abspath(value)
    return os.path.abspath(os.path.join(base_dir, value))


def load_case_config(config_path):
    config_path = os.path.abspath(config_path)
    raw = _load_raw_config(config_path)
    config = _deep_merge(DEFAULT_CONFIG, raw)
    config_dir = os.path.dirname(config_path)

    config["config_path"] = config_path
    config["protein_pdb"] = _resolve_path(config_dir, config.get("protein_pdb"))
    config["ligand_path"] = _resolve_path(config_dir, config.get("ligand_path"))
    config["paths"]["output_root"] = _resolve_path(config_dir, config["paths"]["output_root"])

    analysis = config["analysis"]
    analysis["mmpbsa_complex_topology"] = _resolve_path(config_dir, analysis.get("mmpbsa_complex_topology"))
    analysis["mmpbsa_receptor_topology"] = _resolve_path(config_dir, analysis.get("mmpbsa_receptor_topology"))
    analysis["mmpbsa_ligand_topology"] = _resolve_path(config_dir, analysis.get("mmpbsa_ligand_topology"))
    analysis["mmpbsa_input"] = _resolve_path(config_dir, analysis.get("mmpbsa_input"))

    axial_cys_resid = config.get("axial_cys_resid")
    if axial_cys_resid and not analysis.get("cys_s_mask"):
        analysis["cys_s_mask"] = f":{axial_cys_resid}@SG"

    distance_pairs = analysis.get("distance_pairs") or {}
    if not distance_pairs and analysis.get("key_residue_masks"):
        for label, mask in analysis["key_residue_masks"].items():
            distance_pairs[f"{label}_to_fe"] = {
                "mask1": mask,
                "mask2": analysis["fe_atom_mask"],
            }
            if analysis.get("substrate_reactive_atom_mask"):
                distance_pairs[f"{label}_to_substrate"] = {
                    "mask1": mask,
                    "mask2": analysis["substrate_reactive_atom_mask"],
                }
    analysis["distance_pairs"] = distance_pairs

    return config
