import time
import epics
from datetime import datetime
import threading
import signal
import sys

print("⏳ Waiting for IOC to initialize...")
time.sleep(2)  # Delay to ensure PVs are initialized
epics.caput("SIM:BEAM:RESET", 0)  # ✅ Added quotes around PV name
print("✅ IOC should be ready. Starting beam monitoring...")

def safe_caget(pv_name, default=None):
    try:
        return epics.caget(pv_name) or default
    except Exception as e:
        print(f"Error reading PV {pv_name}: {e}")
        return default

def safe_caput(pv_name, value):
    try:
        epics.caput(pv_name, value)
    except Exception as e:
        print(f"Error writing to PV {pv_name}: {e}")

def trigger_beam_dump():
    """ Triggers a beam dump and stops the simulation. """
    safe_caput("SIM:START", 0)  # Stop the simulation
    safe_caput("SIM:BEAM:DUMP", 1)  # Set beam dump PV
    safe_caput("SIM:STATUS:3", "Beam Dump Triggered")
    safe_caput("SIM:STATUS:4", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # Lock is lost during beam dumps
    safe_caput("SIM:PLL:LOCK_STATUS", 0)
    safe_caput("SIM:MO:LOCK_STATUS", 0)
    safe_caput("SIM:LASER:LOCK_STATUS", 0)

def monitor_beam_status():
    """ Monitors laser phase error and triggers a beam dump if phase lock is lost. """
    while True:
        phase_error = safe_caget("SIM:LASER:PH_ERROR", 0.0)
        phase_error_limit = safe_caget("SIM:LASER:PH_ERR_WIN", 45.0)  # Beam dump threshold

        # Check if beam dump was manually set
        manual_dump = safe_caget("SIM:BEAM:DUMP") == 1

        if phase_error > phase_error_limit or manual_dump:
            trigger_beam_dump()  # Trigger beam dump

        time.sleep(1)  # Check at 1 Hz

def reset_beam():
    """ Resets the beam and restores all relevant PVs to default values when SIM:BEAM:RESET is set to 1. """
    if safe_caget("SIM:BEAM:RESET") == 1:
        print("✅ Manual Beam Reset Triggered. Restoring defaults...")

        # Clear the beam dump
        safe_caput("SIM:BEAM:DUMP", 0)

        # Restore lock statuses, assuming synchronization is re-established
        safe_caput("SIM:PLL:LOCK_STATUS", 1)
        safe_caput("SIM:MO:LOCK_STATUS", 1)
        safe_caput("SIM:LASER:LOCK_STATUS", 1)

        # Reset phases and outputs
        safe_caput("SIM:LASER:PH_SP", 0.0)  # Default laser phase setpoint
        safe_caput("SIM:LASER:PH_RB", 0.0)  # Default laser phase readback
        safe_caput("SIM:LASER:PH_ERROR", 0.0)  # Default laser phase error
        safe_caput("SIM:MO:PHASE", 0.0)     # Default master oscillator phase
        safe_caput("SIM:MO:PHASE_CORRECTION", 0.0)  # Default phase correction
        safe_caput("SIM:PLL:OUTPUT", 0.0)   # Default PLL output
        safe_caput("SIM:PLL:CENTER", 0.0)   # Default PLL center
        safe_caput("SIM:PIEZO:OUTPUT", 0.0) # Default piezo output

        # Update status PVs
        safe_caput("SIM:STATUS:3", "Beam Restored")
        safe_caput("SIM:STATUS:4", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # Clear the reset request
        safe_caput("SIM:BEAM:RESET", 0)
        print("✅ Beam and system restored to default values.")

def monitor_beam_reset():
    """ Listens for manual beam reset commands via SIM:BEAM:RESET and handles reset. """
    while True:
        reset_beam()
        time.sleep(1)

def shutdown_handler(signum, frame):
    print("\n🛑 Shutting down beam monitoring...")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    print("✅ Beam Monitoring Started...")
    threading.Thread(target=monitor_beam_status, daemon=True).start()
    threading.Thread(target=monitor_beam_reset, daemon=True).start()
    while True:
        time.sleep(1)  # Keep the main thread alive
