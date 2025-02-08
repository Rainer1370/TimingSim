from pcaspy import Driver, SimpleServer
import numpy as np
import time
import signal
import sys
import subprocess
import os
import json
import threading
from datetime import datetime  # For timestamp logging

# Define EPICS PVs
prefix = "SIM:"

# Load PVs from external JSON file
pvdb_path = os.path.join(os.path.dirname(__file__), "pvdb.json")
with open(pvdb_path, "r") as f:
    pvdb = json.load(f)

class PhaseDriftIOC(Driver):
    def __init__(self):
        super().__init__()
        self.simulation_running = False
        self.initialize_pvs()
        self.write_pv_list()
        
        # Start the environmental factor update loop
        self.env_thread = threading.Thread(target=self.update_environmental_factors, daemon=True)
        self.env_thread.start()

    def initialize_pvs(self):
        """Ensures all PVs are initialized with their default values to prevent disconnections."""
        for pv_name, properties in pvdb.items():
            self.setParam(pv_name, properties["value"])
        self.updatePVs()

    def write_pv_list(self):
        """Writes the current PV list to `dbl.txt` with a timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dbl_path = os.path.join(os.path.dirname(__file__), "dbl.txt")
        with open(dbl_path, "w") as f:
            f.write(f"# PV List Generated on {timestamp}\n\n")
            for pv_name in pvdb.keys():
                f.write(f"{prefix}{pv_name}\n")
        print(f"✅ PV list saved to dbl.txt (Timestamp: {timestamp})")

    def update_environmental_factors(self):
        """Continuously updates environmental PVs to simulate real-world fluctuations."""
        while True:
            temp_fiber = self.getParam("TEMP:FIBER")
            vibration_ext = self.getParam("VIBRATION:EXT")
            power_stability = self.getParam("POWER:STABILITY")

            # Introduce small fluctuations to simulate environmental changes
            temp_fiber += np.random.uniform(-0.05, 0.05)
            vibration_ext = max(0, vibration_ext + np.random.uniform(-0.02, 0.02))
            power_stability = max(0.95, min(1.05, power_stability + np.random.uniform(-0.01, 0.01)))

            self.setParam("TEMP:FIBER", temp_fiber)
            self.setParam("VIBRATION:EXT", vibration_ext)
            self.setParam("POWER:STABILITY", power_stability)

            self.updatePVs()
            time.sleep(5)  # Update every 5 seconds

    def write(self, reason, value):
        """Handles PV updates including simulation control, beam reset, and IOC reboot."""
        if reason == "BEAM:RESET" and value == 1:
            self.reset_beam()

        elif reason == "SIMULATION:START":
            if value == 1 and not self.simulation_running:
                self.start_simulation()
            elif value == 0 and self.simulation_running:
                self.stop_simulation()

        elif reason == "IOC:REBOOT" and value == 1:
            self.reboot_ioc()

        return super().write(reason, value)

    def reset_beam(self):
        """Handles resetting the beam to restore normal operation."""
        self.setParam("BEAM:DUMP", 0)
        self.setParam("BEAM:RESET", 0)

        self.setParam("PHASE:ERROR", 0.0)
        self.setParam("PLL:OUTPUT", 0.0)
        self.setParam("PIEZO:OUTPUT", 0.0)
        self.setParam("PHASE:CORRECTED", 0.0)
        self.setParam("PID:Kp", 0.0)
        self.setParam("PID:Ki", 0.0)
        self.setParam("PID:Kd", 0.0)

        print("✅ Beam Reset Complete.")
        self.updatePVs()

    def start_simulation(self):
        """Starts the Timing System Simulation using the central manager."""
        script_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

        subprocess.Popen(["python", os.path.join(script_dir, "simulation_manager.py")])

        self.simulation_running = True
        self.setParam("SIMULATION:START", 1)
        print("🚀 Simulation Manager Started.")
        self.updatePVs()

    def stop_simulation(self):
        """Stops the Timing System Simulation using the central manager."""
        subprocess.call(["pkill", "-f", "simulation_manager.py"])

        self.simulation_running = False
        self.setParam("SIMULATION:START", 0)
        self.setParam("BEAM:DUMP", 1)
        print("🛑 Simulation Stopped. Beam Dumped.")
        self.updatePVs()

    def reboot_ioc(self):
        """Restarts the IOC script by executing itself again."""
        print("🔄 Rebooting IOC...")
        self.setParam("IOC:REBOOT", 0)
        os.execv(sys.executable, ['python'] + sys.argv)

def main():
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    server = SimpleServer()
    server.createPV(prefix, pvdb)
    driver = PhaseDriftIOC()

    print("✅ Soft IOC running. Press Ctrl+C to stop.")
    while True:
        server.process(1.0)

if __name__ == "__main__":
    main()
