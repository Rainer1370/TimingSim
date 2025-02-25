from pcaspy import Driver, SimpleServer
import time
import threading
import signal
import sys
import os
import json
import datetime
import subprocess

# Define EPICS PVs prefix
PREFIX = "SIM:"

# Load PVs from external JSON file
PVDB_PATH = os.path.join(os.path.dirname(__file__), "pvdb.json")
with open(PVDB_PATH, "r") as f:
    PVDB = json.load(f)

# Define IOC-specific PVs
IOC_PVDB = {
    "IOC:HEARTBEAT": {"type": "int", "value": 0},
    "IOC:START_TIME": {"type": "string", "value": ""},
    "START": {"type": "enum", "enums": ["Stop", "Start"], "value": 0},
}

# Paths to simulation scripts
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LASER_SIM_SCRIPT = os.path.join(BASE_DIR, "laserSim.py")
CONTROL_SCRIPT = os.path.join(BASE_DIR, "control.py")

#========================================================
class PhaseDriftIOC(Driver):
    def __init__(self):
        super().__init__()
        self.simulation_processes = []
        self.initialize_pvs()
        self.write_pv_list()

        # Start the heartbeat PV
        self.heartbeat_thread = threading.Thread(target=self.heartbeat_pv, daemon=True)
        self.heartbeat_thread.start()

        # Store IOC Start Time
        self.setParam("IOC:START_TIME", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.updatePVs()

    #===== PV Functions ===================================================
    def initialize_pvs(self):
        """Ensures all PVs are initialized with default values."""
        for pv_name, properties in {**PVDB, **IOC_PVDB}.items():
            self.setParam(pv_name, properties.get("value", 0.0))
            self.updatePVs()

    def write_pv_list(self):
        """Writes the PV list to dbl.txt with a timestamp."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dbl_path = os.path.join(os.path.dirname(__file__), "dbl.txt")
        with open(dbl_path, "w") as f:
            f.write(f"# PV List Generated on {timestamp}\n\n")
            for pv in {**PVDB, **IOC_PVDB}:
                f.write(f"{PREFIX}{pv}\n")
        print(f"✅ PV list saved to dbl.txt (Timestamp: {timestamp})")

    def heartbeat_pv(self):
        """Toggles the heartbeat PV every second."""
        while True:
            current_heartbeat = self.getParam("IOC:HEARTBEAT")
            self.setParam("IOC:HEARTBEAT", 1 - current_heartbeat)
            self.updatePVs()
            time.sleep(1)

    #===== Simulation Functions ==========================================
    def start_simulation(self):
        """Starts the phase simulation and PID control scripts."""
        self.stop_simulation()
        print("🚀 Starting Phase Simulation and PID Control...")
        self.simulation_processes = [
            subprocess.Popen(["python3", LASER_SIM_SCRIPT], stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp),
            subprocess.Popen(["python3", CONTROL_SCRIPT], stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp),
        ]
        self.setParam("START", 1)
        self.updatePVs()

    def stop_simulation(self):
        """Stops all running phase simulation and PID control processes."""
        print("🛑 Stopping Phase Simulation and PID Control...")
        for process in self.simulation_processes:
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
        os.system("pkill -f 'python3 phase_sim.py'")
        os.system("pkill -f 'python3 pid_control.py'")
        self.simulation_processes.clear()
        self.setParam("START", 0)
        self.updatePVs()

    def write(self, reason, value):
        """Handles writes to control PVs."""
#        print(f"🔹 Received PV Write: {reason} = {value}")
        self.setParam(reason, value)
        if reason == "START":
            if value == 1:
                self.start_simulation()
            else:
                self.stop_simulation()
        self.updatePVs()
        return True

#========================================================
def main():
    """Main function to start the IOC server."""
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    server = SimpleServer()
    server.createPV(PREFIX, PVDB)
    server.createPV("", IOC_PVDB)
    driver = PhaseDriftIOC()
    print("✅ Soft IOC running. Press Ctrl+C to stop.")
    while True:
        server.process(1.0)

if __name__ == "__main__":
    main()
