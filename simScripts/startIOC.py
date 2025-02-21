from pcaspy import Driver, SimpleServer
import os
import subprocess
import signal
import sys
import time
import threading
import datetime

# Define IOC Control PVs
prefix = "IOC:"
pvdb = {
    "START": {"type": "enum", "enums": ["Off", "On"], "value": 0},  # Controls all IOC-related scripts
    "STATUS": {"type": "string", "value": "IOC Ready"},
    "TOD": {"type": "string", "value": "1970-01-01 00:00:00"},  # ✅ Date & Time PV
}

# Paths to scripts
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Get current script directory
IOC_SCRIPT = os.path.join(BASE_DIR, "ioc.py")
ENV_SCRIPT = os.path.join(BASE_DIR, "envSim.py")
MO_SCRIPT = os.path.join(BASE_DIR, "moSim.py")
BEAM_SCRIPT = os.path.join(BASE_DIR, "beam.py")

class IOCStarter(Driver):
    def __init__(self):
        super().__init__()
        self.processes = {}  # Dictionary to track running processes
        self.setParam("STATUS", "IOC Ready")
        self.updatePVs()

        # Start Time-of-Day (TOD) PV update
        self.tod_thread = threading.Thread(target=self.update_tod_pv, daemon=True)
        self.tod_thread.start()

    def update_tod_pv(self):
        """Updates the Date & Time PV every second."""
        while True:
            current_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.setParam("TOD", current_datetime)
            self.updatePVs()
            time.sleep(1)

    def start_ioc(self):
        """Start all IOC-related scripts if not already running."""
        self.stop_ioc()  # Ensure old processes are stopped before starting new ones

        print("🚀 Starting IOC processes...")
        
        # Start and track processes only if they are not already running
        for name, script in {
            "ioc": IOC_SCRIPT,
            "envSim": ENV_SCRIPT,
            "moSim": MO_SCRIPT,
            "beam": BEAM_SCRIPT
        }.items():
            if name not in self.processes or self.processes[name].poll() is not None:
                self.processes[name] = subprocess.Popen(["python3", script], preexec_fn=os.setpgrp)

        self.setParam("STATUS", "IOC Running")
        self.setParam("START", 1)
        self.updatePVs()

    def stop_ioc(self):
        """Stop all running IOC-related scripts."""
        print("🛑 Stopping IOC processes...")

        # **Terminate all tracked processes cleanly**
        for name, process in list(self.processes.items()):
            if process and process.poll() is None:
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)  # Send termination signal
                    process.wait(timeout=3)  # Allow graceful shutdown
                    print(f"✅ {name} stopped successfully.")
                except (subprocess.TimeoutExpired, ProcessLookupError):
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)  # Force kill if needed
                    print(f"⚠️ {name} required force termination.")
                
        # **Ensure no orphaned processes**
        self._force_kill_processes()

        self.processes.clear()  # Remove references
        self.setParam("STATUS", "IOC Stopped")
        self.setParam("START", 0)
        self.updatePVs()

    def _force_kill_processes(self):
        """Forcefully kills any lingering processes related to the IOC."""
        for script in ["ioc.py", "envSim.py", "moSim.py", "beam.py"]:
            os.system(f"pkill -f 'python3 {script}'")  # Kill process if still running
            os.system(f"pgrep -f 'python3 {script}' | xargs -r kill -9")  # Ensure it's gone
            print(f"🔹 Ensured {script} is terminated.")

    def write(self, reason, value):
        """Handles writes to control PVs."""
        print(f"🔹 Received PV Write: {reason} = {value}")

        if reason == "START":
            if value == 1:
                self.start_ioc()
            else:
                self.stop_ioc()

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
