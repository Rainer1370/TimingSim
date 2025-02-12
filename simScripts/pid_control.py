from epics import PV
import time
from simple_pid import PID
import numpy as np

# Read/Write PVs
phase_error_pv = PV("SIM:PHASE:ERROR")
pll_output_pv = PV("SIM:PLL:OUTPUT")
phase_corrected_pv = PV("SIM:PHASE:CORRECTED")
piezo_output_pv = PV("SIM:PIEZO:OUTPUT")
pll_center_pv = PV("SIM:PLL:CENTER")
pll_range_pv = PV("SIM:PLL:RANGE")
beam_dump_pv = PV("SIM:BEAM:DUMP")
sim_start_pv = PV("SIM:START")

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

def update_pid_gains(phase_error, piezo_output):
    """Dynamically adjusts PID gains based on phase error and piezo response, unless overridden."""
    
    # Retrieve current mode settings (0 = Auto, 1 = Manual Override)
    kp_mode = kp_mode_pv.get() or 0
    ki_mode = ki_mode_pv.get() or 0
    kd_mode = kd_mode_pv.get() or 0

    # Retrieve current gain values
    kp = kp_pv.get() or 0.1
    ki = ki_pv.get() or 0.01
    kd = kd_pv.get() or 0.01

    # **Update PID Mode Message PV**
    if kp_mode == 1 or ki_mode == 1 or kd_mode == 1:
        message4_pv.put("PID Control Inactive", wait=True)
    else:
        message4_pv.put("PID Control Active", wait=True)

    # Adaptive gain logic (only for Auto mode)
    if kp_mode == 0:  # Adjust Kp dynamically
        if abs(phase_error) > 1.0:
            kp += 0.01  # Increase proportional gain slightly if error is large
        else:
            kp -= 0.005  # Reduce gain slightly when error is small
        kp = max(0.05, min(kp, 5.0))  # Keep within a safe range
        kp_pv.put(kp, wait=True)  # Update Kp PV only in Auto mode

    if ki_mode == 0:  # Adjust Ki dynamically
        if abs(piezo_output) > 0.5:
            ki += 0.001  # Increase integral action when piezo is active
        else:
            ki -= 0.0005  # Reduce integration when piezo is stable
        ki = max(0.001, min(ki, 1.0))
        ki_pv.put(ki, wait=True)  # Update Ki PV only in Auto mode

    if kd_mode == 0:  # Adjust Kd dynamically
        if abs(phase_error) > 2.0:
            kd += 0.002  # Increase derivative action if phase error is large
        else:
            kd -= 0.001  # Reduce derivative action if error is stable
        kd = max(0.001, min(kd, 1.0))
        kd_pv.put(kd, wait=True)  # Update Kd PV only in Auto mode

    # Apply gains to PID controller
    pid.tunings = (kp, ki, kd)

def monitor_phase_lock():
    """Monitors phase error and applies corrections dynamically."""
    while True:
        if sim_start_pv.get() == 0:
            print("🛑 Simulation Stopped.")
            time.sleep(1)
            continue

        if beam_dump_pv.get() == 1:
            print("🚨 Beam Dumped: Holding Values.")
            time.sleep(1)
            continue

        # Get current phase error
        phase_error = phase_error_pv.get() or 0.0
        pll_range = pll_range_pv.get() or 50.0

        # Compute PID correction
        correction = pid(phase_error)

        # Simulate piezo response (lag effect)
        piezo_response = piezo_output_pv.get() or 0.0
        piezo_response += (correction - piezo_response) * 0.2  # Smooth response
        piezo_output_pv.put(piezo_response, wait=True)

        # Simulate phase stabilization due to piezo correction
        new_phase_error = phase_error - (piezo_response * 0.1)
        phase_error_pv.put(new_phase_error)

        # Adjust output PVs
        pll_output_pv.put(new_phase_error / 2)
        phase_corrected_pv.put(new_phase_error / 3)

        # Adaptive tuning (Only modifies values if Auto mode is selected)
        update_pid_gains(phase_error, piezo_response)

        # Handle beam dump if phase goes out of range
        if abs(new_phase_error) > pll_range:
            print("🚨 Beam Dumped: Phase Out of Lock!")
            beam_dump_pv.put(1)

        time.sleep(1)

if __name__ == "__main__":
    print("✅ PID Control Waiting for Start Signal...")

    while True:
        if sim_start_pv.get() == 1:
            print("🚀 PID Control Started.")
            monitor_phase_lock()
        time.sleep(1)  # Prevent CPU overuse
