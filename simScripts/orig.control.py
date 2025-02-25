import time
import numpy as np
import epics  # Use EPICS caget/caput for PV access
from simple_pid import PID

# Initialize PID controller for phase correction
pid = PID(0.1, 0.01, 0.01, setpoint=0.0)
pid.sample_time = 1.0  # Run every second

# Rolling average buffer for PLL Output Voltage
pll_output_history = []

def update_pid_gains(laser_phase_error, piezo_output):
    """Dynamically adjusts PID gains based on laser phase error and piezo response, unless overridden."""
    kp_mode = epics.caget("SIM:PID:Kp_MODE") or 0
    ki_mode = epics.caget("SIM:PID:Ki_MODE") or 0
    kd_mode = epics.caget("SIM:PID:Kd_MODE") or 0

    kp = epics.caget("SIM:PID:Kp") or 0.1
    ki = epics.caget("SIM:PID:Ki") or 0.01
    kd = epics.caget("SIM:PID:Kd") or 0.01

    if kp_mode == 0:
        kp += 0.01 if abs(laser_phase_error) > 1.0 else -0.005
        kp = max(0.05, min(kp, 5.0))
        epics.caput("SIM:PID:Kp", kp)

    if ki_mode == 0:
        ki += 0.001 if abs(piezo_output) > 0.5 else -0.0005
        ki = max(0.001, min(ki, 1.0))
        epics.caput("SIM:PID:Ki", ki)

    if kd_mode == 0:
        kd += 0.002 if abs(laser_phase_error) > 2.0 else -0.001
        kd = max(0.001, min(kd, 1.0))
        epics.caput("SIM:PID:Kd", kd)

    pid.tunings = (kp, ki, kd)

def apply_pll_pid_control():
    """Locks Laser Phase to MO Phase using PID and PLL control."""
    global pll_output_history

    while True:
        if epics.caget("SIM:START") == 0:
            time.sleep(1)
            continue

        if epics.caget("SIM:BEAM:DUMP") == 1:
            time.sleep(1)  # Do nothing while beam is dumped
            continue  

        # Get MO Phase and Laser Phase
        mo_phase = epics.caget("SIM:MO:PHASE") or 0.0
        laser_phase = epics.caget("SIM:LASER:PH_RB") or 0.0
        pll_range = epics.caget("SIM:PLL:RANGE") or 50.0  # Lock range in fs

        # Calculate Phase Error
        phase_error = laser_phase - mo_phase
        epics.caput("SIM:LASER:PH_ERROR", phase_error)

        # Convert Voltage to fs
        pll_fs_per_volt = epics.caget("SIM:PLL:FS_PER_VOLT") or 10.0
        piezo_fs_per_volt = epics.caget("SIM:PIEZO:FS_PER_VOLT") or 5.0

        # Get Current Correction Values
        piezo_voltage = epics.caget("SIM:PIEZO:OUTPUT") or 0.0
        pll_voltage = epics.caget("SIM:PLL:OUTPUT") or 0.0

        piezo_correction_fs = piezo_voltage * piezo_fs_per_volt
        pll_correction_fs = pll_voltage * pll_fs_per_volt

        # Compute PID Correction
        correction = pid(phase_error)
        epics.caput("SIM:PIEZO:OUTPUT", correction)
        epics.caput("SIM:PLL:OUTPUT", correction)

        # Track PLL Output Voltage for Centering
        pll_output_history.append(correction)
        if len(pll_output_history) > 20:  # Track last 20 values
            pll_output_history.pop(0)

        # Compute Rolling Average of PLL Output
        pll_output_avg = sum(pll_output_history) / len(pll_output_history)
        epics.caput("SIM:PLL:OUTPUT_AVG", pll_output_avg)

        # Update Lock Statuses
        if abs(phase_error) < pll_range:
            epics.caput("SIM:PLL:LOCK_STATUS", 1)  # PLL Locked
            epics.caput("SIM:MO:LOCK_STATUS", 1)  # MO Locked
            epics.caput("SIM:LASER:LOCK_STATUS", 1)  # Laser Locked
        else:
            epics.caput("SIM:PLL:LOCK_STATUS", 0)  # PLL Unlocked
            epics.caput("SIM:MO:LOCK_STATUS", 0)  # MO Unlocked
            epics.caput("SIM:LASER:LOCK_STATUS", 0)  # Laser Unlocked
            # No beam dump logic here! Beam.py handles this.

        time.sleep(1)

if __name__ == "__main__":
    print("✅ Control System Waiting for Start Signal...")

    while True:
        if epics.caget("SIM:START") == 1:
            print("🚀 Control System Activated.")
            apply_pll_pid_control()
        time.sleep(1)  # Prevent CPU overuse
