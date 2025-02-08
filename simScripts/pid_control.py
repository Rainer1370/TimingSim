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
beam_reset_pv = PV("SIM:BEAM:RESET")
sim_start_pv = PV("SIM:SIMULATION:START")

# PID Gains
kp_pv = PV("SIM:PID:Kp")
ki_pv = PV("SIM:PID:Ki")
kd_pv = PV("SIM:PID:Kd")

# PID Gain Modes (0 = Auto, 1 = Override)
kp_mode_pv = PV("SIM:PID:Kp_MODE")
ki_mode_pv = PV("SIM:PID:Ki_MODE")
kd_mode_pv = PV("SIM:PID:Kd_MODE")

# Initialize PID controller
pid = PID(0.1, 0.01, 0.01, setpoint=0.0)
pid.sample_time = 1.0  # Run every second

def update_pid_gains(phase_error, piezo_output):
    """Dynamically adjusts PID gains based on phase error and piezo response, unless overridden."""

    # Retrieve current mode settings
    kp_mode = kp_mode_pv.get() or 0  # 0 = Auto, 1 = Override
    ki_mode = ki_mode_pv.get() or 0
    kd_mode = kd_mode_pv.get() or 0

    # Retrieve current gains
    kp = kp_pv.get() or 0.1
    ki = ki_pv.get() or 0.01
    kd = kd_pv.get() or 0.01

    # Adaptive gain logic: Adjust values **only if mode is Auto (0)**
    if kp_mode == 0:
        if abs(phase_error) > 1.0:
            kp += 0.01  # Increase proportional gain slightly if error is large
        else:
            kp -= 0.005  # Reduce gain slightly when error is small
        kp = max(0.05, min(kp, 5.0))  # Keep within a safe range

    if ki_mode == 0:
        if abs(piezo_output) > 0.5:
            ki += 0.001
        else:
            ki -= 0.0005
        ki = max(0.001, min(ki, 1.0))

    if kd_mode == 0:
        if abs(phase_error) > 2.0:
            kd += 0.002
        else:
            kd -= 0.001
        kd = max(0.001, min(kd, 1.0))

    # Write values back to EPICS **only if mode is Auto (0)**
    if kp_mode == 0:
        kp_pv.put(kp, wait=True)
    if ki_mode == 0:
        ki_pv.put(ki, wait=True)
    if kd_mode == 0:
        kd_pv.put(kd, wait=True)

    # Apply gains to PID controller
    pid.tunings = (kp, ki, kd)

def monitor_beam_status():
    """Monitors phase error and applies corrections dynamically."""
    while True:
        if sim_start_pv.get() == 0:
            print("🛑 Simulation Stopped. Beam Dumped.")
            beam_dump_pv.put(1)
            phase_error_pv.put(0.0)
            pll_output_pv.put(0.0)
            phase_corrected_pv.put(0.0)
            piezo_output_pv.put(0.0)
            time.sleep(1)
            continue

        if beam_reset_pv.get() == 1:
            print("✅ Beam Reset Triggered. Restoring Phase Error to PLL Center.")
            phase_error_pv.put(pll_center_pv.get() or 0.0)
            beam_dump_pv.put(0)
            time.sleep(0.5)
            beam_reset_pv.put(0)
            print("🔄 Reset cleared.")

        # Ensure PLL range is valid
        pll_range = pll_range_pv.get() or 50.0  # Default if None

        # Get current phase error
        phase_error = phase_error_pv.get() or 0.0
        piezo_output = piezo_output_pv.get() or 0.0

        # Adjust PID gains based on phase error trends
        update_pid_gains(phase_error, piezo_output)

        # Compute PID correction
        correction = pid(phase_error)

        # Ensure correction is applied
        piezo_output_pv.put(correction, wait=True)
#        print(f"📢 Piezo Output Updated: {piezo_output_pv.get()} (Expected: {correction:.3f})")

        # Simulate phase error response
        new_phase_error = np.random.uniform(-0.05, 0.05) - correction * 0.1
        phase_error_pv.put(new_phase_error)

        # Adjust output PVs
        pll_output_pv.put(new_phase_error / 2)
        phase_corrected_pv.put(new_phase_error / 3)

        # Handle beam dump properly
        if abs(new_phase_error) > pll_range:
            print("🚨 Beam Dumped: Phase Out of Lock!")
            beam_dump_pv.put(1)

        time.sleep(1)

if __name__ == "__main__":
    print("✅ PID Control Waiting for Start Signal...")

    while True:
        if sim_start_pv.get() == 1:
            print("🚀 PID Control Started.")
            monitor_beam_status()
        time.sleep(1)  # Prevent CPU overuse
