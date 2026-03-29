import os
import logging
from ..utils.system import run_wsl, win_to_wsl, write_file

logger = logging.getLogger(__name__)

class AmberMDRunner:
    """
    Automated runner for CYP450 AMBER MD following Shahrokh et al. (2011) protocol.
    Implements an 8-stage progressive restraint release (PRR) strategy.
    """

    def __init__(self, work_dir, top_file, crd_file, engine="pmemd.cuda", profile="production", stage_overrides=None):
        self.work_dir = os.path.abspath(work_dir)
        self.top_file = os.path.abspath(top_file)
        self.crd_file = os.path.abspath(crd_file)
        self.engine = engine
        self.profile = profile
        self.stage_overrides = stage_overrides or {}
        
        self.wsl_top = win_to_wsl(self.top_file)
        self.wsl_crd = win_to_wsl(self.crd_file)

        self.input_dir = os.path.join(self.work_dir, "md_input")
        self.output_dir = os.path.join(self.work_dir, "md_output")
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

    def _protocol_defaults(self):
        if self.profile == "local_smoke":
            return {
                "min_maxcyc": 500,
                "min_ncyc": 250,
                "heat_nstlim": 2500,
                "equil_nstlim": 2500,
                "prod_nstlim": 5000,
            }
        return {
            "min_maxcyc": 2000,
            "min_ncyc": 1000,
            "heat_nstlim": 50000,
            "equil_nstlim": 50000,
            "prod_nstlim": 5000000,
        }

    def _generate_inputs(self):
        """Generates academic-standard MD input files."""
        settings = self._protocol_defaults()
        settings.update(self.stage_overrides)

        # Common mask for CYP450 systems
        restraint_mask = "':HEM,LIG,@CA | (:CYP & !@H=)'"

        # Stage 1: Solvent Minimization (Solute Restrained 500 kcal)
        s1 = (
            f"&cntrl imin=1, maxcyc={int(settings['min_maxcyc'])}, ncyc={int(settings['min_ncyc'])}, "
            "ntb=1, ntr=1, restraintmask='!(:WAT,Na+,Cl-)', restraint_wt=500.0, cut=9.0, ntpr=100 /"
        )
        write_file(os.path.join(self.input_dir, "01_min_solv.in"), s1)

        # Stage 2: Thermalization (NVT Heating 0-300K, 100ps)
        s2 = f"""&cntrl
  imin=0, irest=0, ntx=1, nstlim={int(settings['heat_nstlim'])}, dt=0.002,
  ntc=2, ntf=2, ntt=3, gamma_ln=2.0, tempi=0.0, temp0=300.0,
  ntb=1, ntp=0, ntr=1, restraintmask={restraint_mask}, restraint_wt=10.0,
  cut=9.0, ntpr=500, ntwx=500, ig=-1, nmropt=1, ioutfm=1, ntxo=2, /
&wt type='TEMP0', istep1=0, istep2={int(settings['heat_nstlim'])}, value1=0.0, value2=300.0 /
&wt type='END' /"""
        write_file(os.path.join(self.input_dir, "02_heat.in"), s2)

        # Stages 3-7: Progressive NPT Equilibration (10.0 -> 1.0 kcal)
        forces = [10.0, 5.0, 2.0, 1.0, 0.5]
        for i, force in enumerate(forces):
            stage_num = i + 3
            s_npt = f"""&cntrl
  imin=0, irest=1, ntx=5, nstlim={int(settings['equil_nstlim'])}, dt=0.002,
  ntc=2, ntf=2, ntt=3, gamma_ln=2.0, temp0=300.0,
  ntb=2, ntp=1, barostat=2, pres0=1.0, taup=2.0,
  ntr=1, restraintmask={restraint_mask}, restraint_wt={force},
  cut=9.0, ntpr=500, ntwx=500, ig=-1, ioutfm=1, ntxo=2, /"""
            write_file(os.path.join(self.input_dir, f"0{stage_num}_equil_{force}.in"), s_npt)

        # Stage 8: Production NPT (No Restraints)
        s_prod = f"""&cntrl
  imin=0, irest=1, ntx=5, nstlim={int(settings['prod_nstlim'])}, dt=0.002,
  ntc=2, ntf=2, ntt=3, gamma_ln=1.0, temp0=300.0,
  ntb=2, ntp=1, barostat=2, pres0=1.0, taup=2.0,
  ntr=0, cut=9.0, ntpr=5000, ntwx=5000, ig=-1, ioutfm=1, ntxo=2, /"""
        write_file(os.path.join(self.input_dir, "08_prod.in"), s_prod)

    def run_protocol(self):
        """Orchestrates the PRR MD protocol."""
        self._generate_inputs()
        wsl_out = win_to_wsl(self.output_dir)
        wsl_in = win_to_wsl(self.input_dir)
        
        # Build multi-stage execution script
        script = "set -euo pipefail\n"
        script += f"cd '{wsl_out}'\n"
        # 1. Min
        script += f"{self.engine} -O -i {wsl_in}/01_min_solv.in -o 01.out -p {self.wsl_top} -c {self.wsl_crd} -ref {self.wsl_crd} -r 01.rst7\n"
        # 2. Heat
        script += f"{self.engine} -O -i {wsl_in}/02_heat.in -o 02.out -p {self.wsl_top} -c 01.rst7 -ref {self.wsl_crd} -r 02.rst7 -x 02.nc\n"
        # 3-7. Equil
        prev = "02"
        for i, force in enumerate([10.0, 5.0, 2.0, 1.0, 0.5]):
            curr = f"0{i+3}"
            script += f"{self.engine} -O -i {wsl_in}/{curr}_equil_{force}.in -o {curr}.out -p {self.wsl_top} -c {prev}.rst7 -ref {self.wsl_crd} -r {curr}.rst7 -x {curr}.nc\n"
            prev = curr
        # 8. Prod
        script += f"{self.engine} -O -i {wsl_in}/08_prod.in -o 08.out -p {self.wsl_top} -c {prev}.rst7 -r 08.rst7 -x 08.nc\n"
        script += "echo 'ACYPA_FINISHED'\n"

        write_file(os.path.join(self.work_dir, "run_md_prr.sh"), script)
        logger.info("Executing Progressive Restraint Release (PRR) Protocol...")
        res = run_wsl("bash run_md_prr.sh", cwd=self.work_dir)
        trajectory = os.path.join(self.output_dir, "08.nc")
        restart = os.path.join(self.output_dir, "08.rst7")

        if res.returncode != 0:
            return {
                "status": "failed",
                "error": f"MD protocol failed: {(res.stderr or res.stdout).strip()}",
            }

        if "ACYPA_FINISHED" not in res.stdout or not os.path.exists(trajectory):
            return {
                "status": "failed",
                "error": "MD protocol finished without expected output files.",
            }

        if not os.path.exists(restart):
            return {
                "status": "failed",
                "error": "MD protocol did not produce the expected restart file.",
            }

        return {"status": "success", "trajectory": trajectory, "restart": restart}
