from pcaspy import Driver, SimpleServer
import time
import signal
import sys
import os
import json
import datetime
import threading  # ✅ Added threading import

# Define EPICS PVs
prefix = "SIM:"

# Load PVs from external JSON file
pvdb_path = os.path.join(os.path.dirname(__file__), "pvdb.json")
with open(pvdb_path, "r") as f:
    pvdb = json.load(f)

# Define IOC-specific PVs
ioc_pvdb = {
    "IOC:HEARTBEAT": {"type": "int", "value": 0},
    "IOC:START_TIME": {"type": "string", "value": ""}
}

#========================================================
class PhaseDriftIOC(Driver):
    """Handles IOC initialization, heartbeat, and timestamping."""
    def __init__(self):
        super().__init__()
        self.initialize_pvs()
        self.write_pv_list()

        # Start the heartbeat PV
        self.heartbeat_thread = threading.Thread(target=self.heartbeat_pv, daemon=True)
        self.heartbeat_thread.start()

        # Store IOC Start Time
        self.setParam("IOC:START_TIME", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.updatePVs()

    def initialize_pvs(self):
        """Ensures all PVs are initialized with default values."""
        for pv_name, properties in {**pvdb, **ioc_pvdb}.items():
            self.setParam(pv_name, properties.get("value", 0.0))
        self.updatePVs()

    def write_pv_list(self):
        """Writes the PV list to `dbl.txt` with a timestamp."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dbl_path = os.path.join(os.path.dirname(__file__), "dbl.txt")
        with open(dbl_path, "w") as f:
            f.write(f"# PV List Generated on {timestamp}\n\n")
            for pv in {**pvdb, **ioc_pvdb}:
                f.write(f"{prefix}{pv}\n")
        print(f"✅ PV list saved to dbl.txt (Timestamp: {timestamp})")

    def heartbeat_pv(self):
        """Toggles the heartbeat PV every second to indicate the IOC is running."""
        while True:
            current_heartbeat = self.getParam("IOC:HEARTBEAT")
            self.setParam("IOC:HEARTBEAT", 1 - current_heartbeat)  # Toggle between 0 and 1
            self.updatePVs()
            time.sleep(1)

#========================================================
def main():
    """Main function to start the IOC server."""
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    server = SimpleServer()
    server.createPV(prefix, pvdb)
    server.createPV("", ioc_pvdb)
    driver = PhaseDriftIOC()
    print("✅ Soft IOC running. Press Ctrl+C to stop.")
    while True:
        server.process(1.0)

if __name__ == "__main__":
    main()
