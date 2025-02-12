from epics import PV
import time
import numpy as np

# Read/Write PVs
phase_error_pv = PV("SIM:PHASE:ERROR")
pll_output_pv = PV("SIM:PLL:OUTPUT")
phase_corrected_pv = PV("SIM:PHASE:CORRECTED")
pll_center_pv = PV("SIM:PLL:CENTER")
pll_range_pv = PV("SIM:PLL:RANGE")
beam_dump_pv = PV("SIM:BEAM:DUMP")
sim_start_pv = PV("SIM:START")

# Environmental Factor PVs
temp_fiber_pv = PV("SIM:TEMP:FIBER")
vibration_ext_pv = PV("SIM:VIBRATION:EXT")
power_stability_pv = PV("SIM:POWER:STABILITY")

# Sensitivity Constants (fs drift per unit)
TEMP_SENSITIVITY = 5.0  # fs per °C
VIBRATION_SENSITIVITY = 20.0  # fs per vibration unit
POWER_SENSITIVITY = 10.0  # fs per % fluctuation

# Initial Values
current_phase_error = 0.0
last_update_time = time.time()

def update_phase_error():
    """Update the phase error based on environmental factors."""
    global current_phase_error, last_update_time

    if beam_dump_pv.get() == 1:
        return 0.0  # Stop drifting and hold phase at 0

    # Get environmental values (default if None)
    temp_fiber = temp_fiber_pv.get() or 22.0
    vibration_ext = vibration_ext_pv.get() or 0.0
    power_stability = power_stability_pv.get() or 1.0

    # Phase Drift Components
    temp_drift = (temp_fiber - 22.0) * TEMP_SENSITIVITY
    vibration_noise = np.random.uniform(-VIBRATION_SENSITIVITY, VIBRATION_SENSITIVITY) * vibration_ext
    power_drift = (1.0 - power_stability) * POWER_SENSITIVITY

    # Apply drift over time (no instant jumps)
    dt = time.time() - last_update_time
    last_update_time = time.time()
    phase_change = (temp_drift + vibration_noise + power_drift) * dt * 0.1
    current_phase_error += phase_change

    return current_phase_error

def monitor_beam_status():
    """Monitor phase drift and beam dump conditions."""
    global current_phase_error

    while True:
        # Stop if simulation is not running
        if sim_start_pv.get() == 0:
            print("🛑 Simulation Stopped.")
            time.sleep(1)
            continue

        # If beam is dumped, reset phase to 0 and hold it
        if beam_dump_pv.get() == 1:
            print("🚨 Beam Dumped: Resetting Phase.")
            current_phase_error = 0.0
            phase_error_pv.put(0.0)
            pll_output_pv.put(0.0)
            phase_corrected_pv.put(0.0)
            time.sleep(1)
            continue

        # Get current PLL range
        pll_range = pll_range_pv.get() or 50.0

        # Update Phase Error
        current_phase_error = update_phase_error()
        phase_error_pv.put(current_phase_error)

        # Simulate correction response
        pll_output_pv.put(current_phase_error / 2)
        phase_corrected_pv.put(current_phase_error / 3)

        # Handle Beam Dump
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
        time.sleep(1)
