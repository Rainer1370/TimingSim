from pcaspy import Driver, SimpleServer
import os
import subprocess
import signal
import sys
import time

# Define IOC Control PVs
prefix = "IOC:"
pvdb = {
    "START": {"type": "enum", "enums": ["Off", "On"], "value": 0},  # Controls IOC scripts
    "SIM:START": {"type": "enum", "enums": ["Off", "On"], "value": 0},  # Controls laser simulation scripts
    "STATUS": {"type": "string", "value": "IOC Ready"},
}

# Paths to scripts
# Paths to scripts (fixing the directory issue)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Go one directory up

IOC_SCRIPT = os.path.join(os.path.dirname(__file__), "iocPhaseDriftSim.py")
ENV_SCRIPT = os.path.join(os.path.dirname(__file__), "envSim.py")
MO_SCRIPT = os.path.join(os.path.dirname(__file__), "moSim.py")

PHASE_SIM_SCRIPT = os.path.join(BASE_DIR, "phase_sim.py")  # Now correctly references the parent directory
PID_CONTROL_SCRIPT = os.path.join(BASE_DIR, "pid_control.py")
SIM_MANAGER_SCRIPT = os.path.join(BASE_DIR, "simulation_manager.py")

class IOCStarter(Driver):
    def __init__(self):
        super().__init__()
        self.processes = []  # Store process references for IOC scripts
        self.laser_processes = []  # Store process references for laser simulation scripts
        self.setParam("STATUS", "IOC Ready")
        self.updatePVs()

    def start_ioc(self):
        """Start all IOC-related scripts if not already running."""
        self.stop_ioc()  # Ensure old processes are stopped before starting new ones

        print("🚀 Starting IOC processes...")
        self.processes = [
            subprocess.Popen(["python3", IOC_SCRIPT], stdout=subprocess.PIPE, stderr=subprocess.PIPE),
            subprocess.Popen(["python3", ENV_SCRIPT], stdout=subprocess.PIPE, stderr=subprocess.PIPE),
            subprocess.Popen(["python3", MO_SCRIPT], stdout=subprocess.PIPE, stderr=subprocess.PIPE),
        ]

        self.setParam("STATUS", "IOC Running")
        self.setParam("START", 1)
        self.updatePVs()

    def stop_ioc(self):
        """Stop all running IOC processes."""
        print("🛑 Stopping IOC processes...")
        for process in self.processes:
            if process and process.poll() is None:  # If process is still running
                process.terminate()
                process.wait()  # Ensure it fully exits

        self.processes.clear()  # Remove references after stopping
        self.setParam("STATUS", "IOC Stopped")
        self.setParam("START", 0)
        self.updatePVs()

    def start_laser_simulation(self):
        """Start the laser simulation scripts (phase_sim.py, pid_control.py, simulation_manager.py)."""
        self.stop_laser_simulation()  # Ensure old processes are stopped before starting new ones

#        print("🚀 Starting Laser Simulation...")
        self.laser_processes = [
            subprocess.Popen(["python3", PHASE_SIM_SCRIPT], stdout=subprocess.PIPE, stderr=subprocess.PIPE),
            subprocess.Popen(["python3", PID_CONTROL_SCRIPT], stdout=subprocess.PIPE, stderr=subprocess.PIPE),
#            subprocess.Popen(["python3", SIM_MANAGER_SCRIPT], stdout=subprocess.PIPE, stderr=subprocess.PIPE),
        ]

        self.setParam("SIM:START", 1)
        self.updatePVs()
#        print("✅ Laser Simulation Started.")

    def stop_laser_simulation(self):
        """Stop all running laser simulation processes."""
        print("🛑 Stopping Laser Simulation...")
        for process in self.laser_processes:
            if process and process.poll() is None:  # If process is still running
                process.terminate()
                process.wait()  # Ensure it fully exits

        self.laser_processes.clear()  # Remove references after stopping
        self.setParam("SIM:START", 0)
        self.updatePVs()
        print("✅ Laser Simulation Stopped.")

    def write(self, reason, value):
        print(f"🔹 Received PV Write: {reason} = {value}")  # Debug print

        if reason == "START":
            if value == 1:
                self.start_ioc()
            else:
                self.stop_ioc()
        elif reason == "SIM:START":
            if value == 1:
#                print("🚀 Attempting to start laser simulation...")  # Debug
                self.start_laser_simulation()
            else:
#                print("🛑 Attempting to stop laser simulation...")  # Debug
                self.stop_laser_simulation()

        self.updatePVs()
        return True

def main():
    """Main function to start the IOC control server."""
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    server = SimpleServer()
    server.createPV(prefix, pvdb)
    driver = IOCStarter()
    print("✅ IOC Start/Stop Controller Running. Press Ctrl+C to stop.")
    
    while True:
        server.process(1.0)

if __name__ == "__main__":
    main()
