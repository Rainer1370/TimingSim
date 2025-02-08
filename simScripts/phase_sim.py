from epics import PV
import time
import math
import numpy as np

# Read/Write PVs
phase_error_pv = PV("SIM:PHASE:ERROR")
pll_output_pv = PV("SIM:PLL:OUTPUT")
phase_corrected_pv = PV("SIM:PHASE:CORRECTED")
pll_center_pv = PV("SIM:PLL:CENTER")
pll_range_pv = PV("SIM:PLL:RANGE")
beam_dump_pv = PV("SIM:BEAM:DUMP")
beam_reset_pv = PV("SIM:BEAM:RESET")
sim_start_pv = PV("SIM:SIMULATION:START")

# Environmental Factor PVs
temp_lab_pv = PV("SIM:TEMP:LAB")
temp_fiber_pv = PV("SIM:TEMP:FIBER")
vibration_ext_pv = PV("SIM:VIBRATION:EXT")
power_stability_pv = PV("SIM:POWER:STABILITY")

# Phase Drift Variables
current_phase_error = 0.0  # Initialize phase error
last_update_time = time.time()

def update_phase_error():
    """Update the phase error based on external factors."""
    global current_phase_error, last_update_time

    # Get environmental values (default if None)
    temp_fiber = temp_fiber_pv.get() or 22.0
    vibration_ext = vibration_ext_pv.get() or 0.0
    power_stability = power_stability_pv.get() or 1.0

    # **Sensitivity Factors**
    TEMP_SENSITIVITY = 5.0  # fs drift per degree change
    VIBRATION_SENSITIVITY = 20.0  # fs fluctuation
    POWER_SENSITIVITY = 10.0  # fs drift per % fluctuation

    # **Phase Drift Components**
    temp_drift = (temp_fiber - 22.0) * TEMP_SENSITIVITY
    vibration_noise = np.random.uniform(-VIBRATION_SENSITIVITY, VIBRATION_SENSITIVITY) * vibration_ext
    power_drift = (1.0 - power_stability) * POWER_SENSITIVITY

    # Apply changes over time to prevent instant jumps
    dt = time.time() - last_update_time
    last_update_time = time.time()

    # **Simulated Phase Error Update**
    phase_change = (temp_drift + vibration_noise + power_drift) * dt * 0.1  # Smooth effect
    current_phase_error += phase_change

    return current_phase_error

def monitor_beam_status():
    """Monitor beam dump status and reset phase error when cleared."""
    global current_phase_error

    while True:
        if sim_start_pv.get() == 0:
            print("🛑 Simulation Stopped. Beam Dumped.")
            beam_dump_pv.put(1)
            current_phase_error = 0.0
            phase_error_pv.put(0.0)
            pll_output_pv.put(0.0)
            phase_corrected_pv.put(0.0)
            time.sleep(1)
            continue

        if beam_reset_pv.get() == 1:
            print("✅ Beam Reset Triggered. Restoring Phase Error to PLL Center.")
            current_phase_error = pll_center_pv.get() or 0.0
            phase_error_pv.put(current_phase_error)
            beam_dump_pv.put(0)
            time.sleep(0.5)
            beam_reset_pv.put(0)
            print("🔄 Reset cleared.")

        # Ensure PLL range is valid
        pll_range = pll_range_pv.get() or 50.0  # Default if None

        # **Update Phase Error**
        current_phase_error = update_phase_error()
        phase_error_pv.put(current_phase_error)

        # Simulate correction response
        pll_output_pv.put(current_phase_error / 2)
        phase_corrected_pv.put(current_phase_error / 3)

        # **Handle Beam Dump**
        if abs(current_phase_error) > pll_range:
            print("🚨 Beam Dumped: Phase Out of Lock!")
            beam_dump_pv.put(1)

        time.sleep(1)

if __name__ == "__main__":
    print("✅ Phase Simulation Waiting for Start Signal...")
    while True:
        if sim_start_pv.get() == 1:
            print("🚀 Phase Simulation Started.")
            monitor_beam_status()
        time.sleep(1)  # Prevent CPU overuse
