import os

def inject_resp_to_mol2(mol2_in, chg_file, mol2_out):
    """
    Replace BCC/other charges in a MOL2 file with RESP charges from a .chg file (Multiwfn format).
    """
    # 1. Read RESP charges
    resp_charges = []
    with open(chg_file, 'r') as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 5:
                # Multiwfn RESP files can vary slightly; the last field is the charge.
                try:
                    resp_charges.append(float(parts[-1]))
                except ValueError:
                    continue

    # 2. Process MOL2
    with open(mol2_in, 'r') as f:
        lines = f.readlines()

    in_atoms = False
    atom_idx = 0
    output = []

    for line in lines:
        if '@<TRIPOS>ATOM' in line:
            in_atoms = True
            output.append(line)
            continue
        if '@<TRIPOS>' in line and in_atoms:
            in_atoms = False
            output.append(line)
            continue

        if in_atoms and line.strip():
            parts = line.split()
            if atom_idx < len(resp_charges):
                charge = resp_charges[atom_idx]
                # Reconstruct line: ID NAME X Y Z TYPE RESID RESNAME CHARGE
                # Standard MOL2 format (approximated spacing)
                new_line = (f"{int(parts[0]):>7d} {parts[1]:<4s}    "
                           f"{float(parts[2]):>10.4f}{float(parts[3]):>10.4f}{float(parts[4]):>10.4f} "
                           f"{parts[5]:<10s}{int(parts[6]):>1d} {parts[7]:<8s}"
                           f"{charge:>10.6f}\n")
                output.append(new_line)
                atom_idx += 1
            else:
                output.append(line)
        else:
            # Optionally update charge method header
            if line.strip() in ['bcc', 'gas', 'am1']:
                output.append('resp\n')
            else:
                output.append(line)

    with open(mol2_out, 'w') as f:
        f.writelines(output)
    
    return atom_idx
