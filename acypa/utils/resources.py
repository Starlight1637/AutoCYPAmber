import os


def resolve_heme_params_dir(state: str) -> str:
    """Resolve the heme parameter directory from packaged data or source-tree data."""
    acypa_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [
        os.path.join(acypa_root, "data", "heme_params", state),
        os.path.join(acypa_root, "..", "data", "heme_params", state),
    ]

    for candidate in candidates:
        frcmod = os.path.join(candidate, f"{state}.frcmod")
        hem = os.path.join(candidate, "HEM.mol2")
        cyp = os.path.join(candidate, "CYP.mol2")
        if os.path.isdir(candidate) and os.path.exists(frcmod) and os.path.exists(hem) and os.path.exists(cyp):
            return os.path.abspath(candidate)

    searched = ", ".join(os.path.abspath(path) for path in candidates)
    raise FileNotFoundError(
        f"Could not locate packaged heme parameters for state '{state}'. "
        f"Searched: {searched}"
    )
