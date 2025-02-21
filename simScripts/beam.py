import time
import epics  # Use EPICS caget/caput for PV access
from datetime import datetime

def monitor_beam_status():
    """ Monitors laser phase error and triggers a beam dump if phase lock is lost. """
    while True:
        if epics.caget("SIM:START") == 0:
            time.sleep(1)
            continue

        phase_error = epics.caget("SIM:LASER:PH_ERROR") or 0.0
        phase_error_limit = epics.caget("SIM:LASER:PH_ERR_WIN") or 45.0  # Beam dump threshold

        # Check if beam dump was manually set
        manual_dump = epics.caget("SIM:BEAM:DUMP") == 1

        if phase_error > phase_error_limit or manual_dump:
            print(f"🚨 Beam Dump Triggered at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Phase Error: {phase_error}°")
            epics.caput("SIM:BEAM:DUMP", 1)  # Set beam dump PV
            epics.caput("SIM:STATUS:1", "Beam Dump Triggered")
            epics.caput("SIM:STATUS:2", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            reset_phases()  # Ensure phases reset when beam dumps
        
        time.sleep(1)  # Check at 1 Hz

def reset_beam():
    """ Resets the beam if the system stabilizes and resets phase values. """
    if epics.caget("SIM:BEAM:DUMP") == 1:
        mo_lock = epics.caget("SIM:MO:LOCK_STATUS") or 0
        pll_lock = epics.caget("SIM:PLL:LOCK_STATUS") or 0

        # Only reset if both MO and PLL are locked
        if mo_lock == 1 and pll_lock == 1:
            print("✅ Beam Reset: Phase lock restored.")
            epics.caput("SIM:BEAM:DUMP", 0)  # Clear beam dump PV
            epics.caput("SIM:STATUS:1", "Beam Restored")
            epics.caput("SIM:STATUS:2", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            reset_phases()  # Reset phases during beam restoration

if __name__ == "__main__":
    print("✅ Beam Monitoring Started...")

    while True:
        monitor_beam_status()
        time.sleep(1)
