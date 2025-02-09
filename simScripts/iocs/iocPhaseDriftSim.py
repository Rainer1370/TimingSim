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

# Define IOC-specific PVs outside of the "SIM:" namespace
ioc_pvdb = {
    "IOC:HEARTBEAT": {"type": "int", "value": 0},
    "IOC:START_TIME": {"type": "string", "value": ""}
}

class PhaseDriftIOC(Driver):
    def __init__(self):
        super().__init__()
        self.simulation_running = False
        self.initialize_pvs()
        self.write_pv_list()

        # Start environmental factor updates
        self.env_thread = threading.Thread(target=self.update_environmental_factors, daemon=True)
        self.env_thread.start()

        # Start the heartbeat PV
        self.heartbeat_thread = threading.Thread(target=self.heartbeat_pv, daemon=True)
        self.heartbeat_thread.start()

        # Store IOC Start Time
        self.setParam("IOC:START_TIME", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.updatePVs()

    def initialize_pvs(self):
        """Ensures all PVs are initialized with their default values to prevent disconnections."""
        for pv_name, properties in pvdb.items():
            if "type" in properties and properties["type"] == "enum":
                properties["value"] = int(properties["value"])  # Ensure enum values are integers
            elif pv_name.startswith("PID:"):
                properties["value"] = 0.0  # Ensure PID gains start at 0

            self.setParam(pv_name, properties["value"])

        # Initialize IOC-specific PVs
        for pv_name, properties in ioc_pvdb.items():
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
            for pv_name in ioc_pvdb.keys():
                f.write(f"{pv_name}\n")  # Include IOC PVs
        print(f"✅ PV list saved to dbl.txt (Timestamp: {timestamp})")

    def update_environmental_factors(self):
        """Continuously updates environmental PVs to simulate real-world fluctuations."""
        while True:
            temp_lab = self.getParam("TEMP:LAB")
            temp_fiber = self.getParam("TEMP:FIBER")
            vibration_ext = self.getParam("VIBRATION:EXT")
            power_stability = self.getParam("POWER:STABILITY")

            # Introduce small fluctuations to simulate environmental changes
            temp_lab += np.random.uniform(-0.05, 0.05)  # Fluctuations in lab temp
            temp_fiber += np.random.uniform(-0.05, 0.05)  # Fluctuations in fiber temp
            vibration_ext = max(0, vibration_ext + np.random.uniform(-0.02, 0.02))
            power_stability = max(0.95, min(1.05, power_stability + np.random.uniform(-0.01, 0.01)))

            # Update PV values
            self.setParam("TEMP:LAB", temp_lab)
            self.setParam("TEMP:FIBER", temp_fiber)
            self.setParam("VIBRATION:EXT", vibration_ext)
            self.setParam("POWER:STABILITY", power_stability)

            self.updatePVs()
            time.sleep(5)  # Update every 5 seconds

    def heartbeat_pv(self):
        """Updates the heartbeat PV every second, toggling between 0 and 1."""
        while True:
            current_heartbeat = self.getParam("IOC:HEARTBEAT")
            self.setParam("IOC:HEARTBEAT", 1 - current_heartbeat)  # Toggle between 0 and 1
            self.updatePVs()
            time.sleep(1)  # 1Hz update rate

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

        script_path = os.path.abspath(__file__)  # Get absolute path to the script
        os.execv(sys.executable, ['python3', script_path])  # Restart with the correct path


def main():
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    server = SimpleServer()

    # Create PVs with prefix
    server.createPV(prefix, pvdb)

    # Create IOC-specific PVs without prefix
    server.createPV("", ioc_pvdb)  # No prefix, direct IOC PVs

    driver = PhaseDriftIOC()

    print("✅ Soft IOC running. Press Ctrl+C to stop.")
    while True:
        server.process(1.0)


if __name__ == "__main__":
    main()
