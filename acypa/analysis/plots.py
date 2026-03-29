import os

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load_numeric_table(path):
    rows = []
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("@"):
                continue
            values = []
            for token in line.replace(",", " ").split():
                try:
                    values.append(float(token))
                except ValueError:
                    continue
            if len(values) >= 2:
                rows.append(values)
    return np.array(rows, dtype=float) if rows else np.empty((0, 0), dtype=float)


def _series_from_table(table, mode="second"):
    if table.size == 0 or table.shape[1] < 2:
        return np.array([]), np.array([])
    x = table[:, 0]
    if mode == "sum_rest" and table.shape[1] > 2:
        y = np.sum(table[:, 1:], axis=1)
    else:
        y = table[:, 1]
    return x, y


def _write_plot(output_path):
    plt.tight_layout()
    plt.savefig(output_path, dpi=180)
    plt.close()
    return output_path


def plot_series(data_path, output_path, title, xlabel, ylabel, mode="second"):
    table = load_numeric_table(data_path)
    x, y = _series_from_table(table, mode=mode)
    if y.size == 0:
        return None
    plt.figure(figsize=(7.2, 4.2))
    plt.plot(x, y, linewidth=1.8)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(alpha=0.25)
    return _write_plot(output_path)


def plot_rmsf(data_path, output_path):
    table = load_numeric_table(data_path)
    x, y = _series_from_table(table)
    if y.size == 0:
        return None
    plt.figure(figsize=(8.0, 4.2))
    plt.bar(x, y, width=1.0, color="#3b82f6")
    plt.title("Residue RMSF")
    plt.xlabel("Residue")
    plt.ylabel("RMSF (A)")
    plt.grid(alpha=0.25, axis="y")
    return _write_plot(output_path)


def plot_key_residue_distances(distance_files, output_path):
    if not distance_files:
        return None
    plt.figure(figsize=(8.0, 4.4))
    plotted = False
    for label, path in distance_files.items():
        table = load_numeric_table(path)
        x, y = _series_from_table(table)
        if y.size == 0:
            continue
        plt.plot(x, y, linewidth=1.6, label=label)
        plotted = True
    if not plotted:
        plt.close()
        return None
    plt.title("Key Residue Distances")
    plt.xlabel("Frame")
    plt.ylabel("Distance (A)")
    plt.grid(alpha=0.25)
    plt.legend()
    return _write_plot(output_path)


def plot_free_energy_landscape(rmsd_path, rg_path, output_path, temperature=300.0):
    rmsd_table = load_numeric_table(rmsd_path)
    rg_table = load_numeric_table(rg_path)
    _, rmsd = _series_from_table(rmsd_table)
    _, rg = _series_from_table(rg_table)
    if rmsd.size == 0 or rg.size == 0:
        return None
    n = min(len(rmsd), len(rg))
    rmsd = rmsd[:n]
    rg = rg[:n]

    hist, xedges, yedges = np.histogram2d(rmsd, rg, bins=40)
    prob = hist / np.maximum(hist.sum(), 1.0)
    with np.errstate(divide="ignore"):
        kbt = 0.0019872041 * temperature
        energy = -kbt * np.log(prob)
    finite = np.isfinite(energy)
    if not finite.any():
        return None
    energy[finite] -= energy[finite].min()
    energy[~finite] = np.nan

    plt.figure(figsize=(6.4, 5.2))
    mesh = plt.pcolormesh(xedges, yedges, energy.T, shading="auto", cmap="viridis")
    plt.colorbar(mesh, label="Free Energy (kcal/mol)")
    plt.title("Free Energy Landscape (RMSD vs Rg)")
    plt.xlabel("RMSD (A)")
    plt.ylabel("Radius of Gyration (A)")
    return _write_plot(output_path)


def summarize_series(data_path, mode="second"):
    table = load_numeric_table(data_path)
    _, y = _series_from_table(table, mode=mode)
    if y.size == 0:
        return None
    return {
        "n_points": int(y.size),
        "min": float(np.min(y)),
        "max": float(np.max(y)),
        "mean": float(np.mean(y)),
        "std": float(np.std(y)),
        "last": float(y[-1]),
    }


def summarize_mmpbsa(result_path):
    if not result_path or not os.path.exists(result_path):
        return None
    delta_g = None
    with open(result_path, "r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if "DELTA TOTAL" in line.upper():
                values = [token for token in line.replace("=", " ").split() if token]
                for token in reversed(values):
                    try:
                        delta_g = float(token)
                        break
                    except ValueError:
                        continue
                if delta_g is not None:
                    break
    if delta_g is None:
        return None
    return {"delta_total_kcal_mol": delta_g}
