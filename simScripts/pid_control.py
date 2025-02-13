from epics import PV
import time
from simple_pid import PID
import numpy as np

# Read/Write PVs for Laser Phase Control
laser_phase_error_pv = PV("SIM:LASER:PH_ERROR")
laser_phase_setpoint_pv = PV("SIM:LASER:PH_SP")
laser_phase_readback_pv = PV("SIM:LASER:PH_RB")
laser_phase_corrected_pv = PV("SIM:LASER:PH_CORR")
piezo_output_pv = PV("SIM:PIEZO:OUTPUT")
pll_center_pv = PV("SIM:PLL:CENTER")
pll_output_pv = PV("SIM:PLL:OUTPUT")
pll_range_pv = PV("SIM:PLL:RANGE")
pll_lock_status_pv = PV("SIM:PLL:LOCK_STATUS")
beam_dump_pv = PV("SIM:BEAM:DUMP")
sim_start_pv = PV("SIM:START")

# Master Oscillator PVs
mo_phase_pv = PV("SIM:MO:PHASE")
mo_phase_correction_pv = PV("SIM:MO:PHASE_CORRECTION")
mo_freq_pv = PV("SIM:MO:FREQ")
mo_freq_drift_pv = PV("SIM:MO:FREQ_DRIFT")
mo_lock_status_pv = PV("SIM:MO:LOCK_STATUS")

# PID Gains
kp_pv = PV("SIM:PID:Kp")
ki_pv = PV("SIM:PID:Ki")
kd_pv = PV("SIM:PID:Kd")

# PID Gain Modes (0 = Auto, 1 = Manual Override)
kp_mode_pv = PV("SIM:PID:Kp_MODE")
ki_mode_pv = PV("SIM:PID:Ki_MODE")
kd_mode_pv = PV("SIM:PID:Kd_MODE")

# Message PV
message4_pv = PV("SIM:STATUS:4")

# Initialize PID controller
pid = PID(0.1, 0.01, 0.01, setpoint=0.0)
pid.sample_time = 1.0  # Run every second

#=======================================================
def update_pid_gains(laser_phase_error, piezo_output):
    """
    Dynamically adjusts PID gains based on laser phase error and piezo response, unless overridden.
    The function ensures that Kp, Ki, and Kd adaptively adjust unless a manual override is enabled.
    """
    kp_mode = kp_mode_pv.get() or 0
    ki_mode = ki_mode_pv.get() or 0
    kd_mode = kd_mode_pv.get() or 0

    kp = kp_pv.get() or 0.1
    ki = ki_pv.get() or 0.01
    kd = kd_pv.get() or 0.01

    if kp_mode == 1 or ki_mode == 1 or kd_mode == 1:
        message4_pv.put("PID Control Inactive", wait=True)
    else:
        message4_pv.put("PID Control Active", wait=True)

    if kp_mode == 0:
        if abs(laser_phase_error) > 1.0:
            kp += 0.01
        else:
            kp -= 0.005
        kp = max(0.05, min(kp, 5.0))
        kp_pv.put(kp, wait=True)

    if ki_mode == 0:
        if abs(piezo_output) > 0.5:
            ki += 0.001
        else:
            ki -= 0.0005
        ki = max(0.001, min(ki, 1.0))
        ki_pv.put(ki, wait=True)

    if kd_mode == 0:
        if abs(laser_phase_error) > 2.0:
            kd += 0.002
        else:
            kd -= 0.001
        kd = max(0.001, min(kd, 1.0))
        kd_pv.put(kd, wait=True)

    pid.tunings = (kp, ki, kd)

#=======================================================
def monitor_phase_lock():
    """
    Monitors laser phase error and applies corrections dynamically using PID control.

    - Retrieves the current laser phase error.
    - Computes a PID correction using the Piezo system.
    - Adjusts the laser phase error to stabilize the system.
    - Updates PLL and MO lock status.
    - Dumps the beam if the error exceeds the PLL range.
    """
    while True:
        if sim_start_pv.get() == 0:
            print("🛑 Simulation Stopped.")
            time.sleep(1)
            continue

        if beam_dump_pv.get() == 1:
            print("🚨 Beam Dumped: Holding Values.")
            time.sleep(1)
            continue

        # Get current laser phase error and setpoint
        laser_phase_error = laser_phase_error_pv.get() or 0.0
        laser_phase_setpoint = laser_phase_setpoint_pv.get() or 0.0
        pll_range = pll_range_pv.get() or 50.0

        # Compute PID correction
        correction = pid(laser_phase_error)

        # Simulate piezo response (lag effect)
        piezo_response = piezo_output_pv.get() or 0.0
        piezo_response += (correction - piezo_response) * 0.2  # Smooth response
        piezo_output_pv.put(piezo_response, wait=True)

        # Adjust phase error based on Piezo feedback
        new_laser_phase_error = laser_phase_error - (piezo_response * 0.1)
        laser_phase_error_pv.put(new_laser_phase_error)
        laser_phase_readback_pv.put(new_laser_phase_error)

        # Adjust PLL and corrected phase outputs
        pll_output_pv.put(new_laser_phase_error / 2)
        laser_phase_corrected_pv.put(new_laser_phase_error / 3)

        # Ensure MO and PLL Lock Status are correctly updated
        lock_threshold = 50.0  # Lock threshold in fs
        if abs(new_laser_phase_error) < lock_threshold:
            pll_lock_status_pv.put(1)  # Locked
            mo_lock_status_pv.put(1)   # Locked
        else:
            pll_lock_status_pv.put(0)  # Unlocked
            mo_lock_status_pv.put(0)   # Unlocked

        # Adaptive tuning for PID
        update_pid_gains(new_laser_phase_error, piezo_response)

        # Beam Dump Condition
        if abs(new_laser_phase_error) > pll_range:
            print(f"🚨 Beam Dumped: Laser Phase Error ({new_laser_phase_error} fs) Exceeded {pll_range} fs!")
            beam_dump_pv.put(1)

        time.sleep(1)

#=======================================================
if __name__ == "__main__":
    print("✅ Laser PID Control Waiting for Start Signal...")

    while True:
        if sim_start_pv.get() == 1:
            print("🚀 Laser PID Control Started.")
            monitor_phase_lock()
        time.sleep(1)  # Prevent CPU overuse
