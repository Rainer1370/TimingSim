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
pll_range_pv = PV("SIM:PLL:RANGE")
pll_lock_status_pv = PV("SIM:PLL:LOCK_STATUS")
pll_output_pv = PV("SIM:PLL:OUTPUT")
pll_output_avg_pv = PV("SIM:PLL:OUTPUT_AVG")
beam_dump_pv = PV("SIM:BEAM:DUMP")
sim_start_pv = PV("SIM:START")

# Read fs-per-volt conversion factors
pll_fs_per_volt_pv = PV("SIM:PLL:FS_PER_VOLT")
piezo_fs_per_volt_pv = PV("SIM:PIEZO:FS_PER_VOLT")

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

# Status Message PVs
message1_pv = PV("SIM:STATUS:1")
message2_pv = PV("SIM:STATUS:2")
message3_pv = PV("SIM:STATUS:3")
message4_pv = PV("SIM:STATUS:4")

# Initialize PID controller
pid = PID(0.1, 0.01, 0.01, setpoint=0.0)
pid.sample_time = 1.0  # Run every second

# Initialize Rolling Average Buffer
pll_output_history = []

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

    # Check if any gain is in manual mode
    if kp_mode == 1 or ki_mode == 1 or kd_mode == 1:
        message4_pv.put("PID in manual mode", wait=True)
    else:
        message4_pv.put("PID running", wait=True)

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

def monitor_phase_lock():
    """
    Locks Laser Phase to MO Phase.
    - Applies PID correction via Piezo to minimize Phase Error.
    - Dumps the beam if the phase error exceeds PLL limits.
    - Uses a slow correction to keep PLL centered.
    """
    global pll_output_history

    while True:
        if sim_start_pv.get() == 0:
            time.sleep(1)
            continue

        if beam_dump_pv.get() == 1:
            time.sleep(1)
            continue

        # Get MO Phase and Laser Phase
        mo_phase = mo_phase_pv.get() or 0.0
        laser_phase = laser_phase_readback_pv.get() or 0.0
        pll_range = pll_range_pv.get() or 50.0  # Lock range in fs

        # Calculate Phase Error
        phase_error = laser_phase - mo_phase
        laser_phase_error_pv.put(phase_error)

        # **Convert Voltage to fs**
        pll_fs_per_volt = pll_fs_per_volt_pv.get() or 10.0
        piezo_fs_per_volt = piezo_fs_per_volt_pv.get() or 5.0

        piezo_voltage = piezo_output_pv.get() or 0.0
        pll_voltage = pll_output_pv.get() or 0.0

        piezo_correction_fs = piezo_voltage * piezo_fs_per_volt
        pll_correction_fs = pll_voltage * pll_fs_per_volt

        # **Compute PID Correction**
        correction = pid(phase_error)
        piezo_output_pv.put(correction)
        pll_output_pv.put(correction)

        # **Track PLL Output Voltage for Centering**
        pll_output_history.append(correction)
        if len(pll_output_history) > 20:  # Track last 20 values
            pll_output_history.pop(0)

        # **Compute Rolling Average of PLL Output**
        pll_output_avg = sum(pll_output_history) / len(pll_output_history)
        pll_output_avg_pv.put(pll_output_avg)

        # **Beam Dump Condition**
        if abs(phase_error) > pll_range and beam_dump_pv.get() == 0:
            print(f"🚨 Beam Dumped: Phase Error {phase_error} fs exceeded {pll_range} fs!")
            beam_dump_pv.put(1)

        time.sleep(1)

if __name__ == "__main__":
    print("✅ Laser PID Control Waiting for Start Signal...")

    while True:
        if sim_start_pv.get() == 1:
            print("🚀 Laser PID Control Started.")
            monitor_phase_lock()
        time.sleep(1)  # Prevent CPU overuse
