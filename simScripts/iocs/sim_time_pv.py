from pcaspy import Driver, SimpleServer
import time
import signal
import sys

# EPICS PV prefix
prefix = "SIM:"

# Store the initial Unix time reference
start_time = time.time()

# Define new time PVs
pvdb = {
    "UNIX:TIME": {"type": "float", "value": start_time},  # Absolute Unix time
    "TIME": {"type": "float", "value": 0.0},  # Relative time since start
    "TOD": {"type": "string", "value": "00:00:00"},  # Time of Day HH:MM:SS
    "DATE": {"type": "string", "value": "1970-01-01 00:00:00"},  # Full Date-Time
}

class TimeIOC(Driver):
    def __init__(self):
        super().__init__()

    def update_time(self):
        """Update TIME PVs."""
        current_time = time.time()
        elapsed_time = current_time - start_time  # Convert to relative time
        
        # Format time of day as HH:MM:SS
        tod = time.strftime("%H:%M:%S", time.localtime(current_time))
        
        # Format full date-time as YYYY-MM-DD HH:MM:SS
        date_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(current_time))

        self.setParam("UNIX:TIME", current_time)  # Unix timestamp
        self.setParam("TIME", elapsed_time)  # Relative seconds
        self.setParam("TOD", tod)  # HH:MM:SS format
        self.setParam("DATE", date_time)  # Full date-time
        self.updatePVs()

def signal_handler(sig, frame):
    """Handles graceful shutdown on Ctrl+C."""
    print("\n🔴 Shutting down gracefully...")
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    
    server = SimpleServer()
    server.createPV(prefix, pvdb)
    driver = TimeIOC()

    print("✅ SIM:TIME, SIM:UNIX:TIME, SIM:TOD & SIM:DATE Soft IOC running. Press Ctrl+C to stop.")

    try:
        while True:
            driver.update_time()  # Update all time PVs
            server.process(1.0)  # Ensure the server runs properly
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()
