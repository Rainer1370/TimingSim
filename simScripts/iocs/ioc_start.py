from pcaspy import Driver, SimpleServer
import os
import subprocess
import signal
import sys
import time

# Define IOC Control PVs
prefix = "IOC:"
pvdb = {
    "START": {"type": "enum", "enums": ["Off", "On"], "value": 0},
    "STATUS": {"type": "string", "value": "IOC Ready"},
}

# Path to the IOC script
IOC_SCRIPT = os.path.join(os.path.dirname(__file__), "iocPhaseDriftSim.py")

class IOCStarter(Driver):
    def __init__(self):
        super().__init__()
        self.ioc_process = None
        self.setParam("STATUS", "IOC Ready")
        self.updatePVs()

    def start_ioc(self):
        """Start iocPhaseDriftSim.py if not already running."""
        if self.ioc_process is None or self.ioc_process.poll() is not None:
            print("🚀 Starting IOC...")
            self.ioc_process = subprocess.Popen(["python3", IOC_SCRIPT])
            self.setParam("STATUS", "IOC Running")
            self.setParam("START", 1)
            self.updatePVs()
        else:
            print("✅ IOC is already running.")

    def stop_ioc(self):
        """Stop iocPhaseDriftSim.py by killing the process."""
#        print("🛑 Stopping IOC...")
        subprocess.call(["pkill", "-f", "iocPhaseDriftSim.py"])
        self.ioc_process = None
        self.setParam("STATUS", "IOC Stopped")
        self.setParam("START", 0)
        self.updatePVs()

    def write(self, reason, value):
        """Handle writes to the IOC PVs."""
#        print(f"📝 Attempting to write: {reason} = {value}", flush=True)

        if reason == "START":
            if value == 1:
                self.start_ioc()
            else:
                self.stop_ioc()

        self.updatePVs()
        return True

def main():
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    server = SimpleServer()
    server.createPV(prefix, pvdb)
    driver = IOCStarter()
    print("✅ IOC Start/Stop Controller Running. Press Ctrl+C to stop.")
    while True:
        server.process(1.0)

if __name__ == "__main__":
    main()
