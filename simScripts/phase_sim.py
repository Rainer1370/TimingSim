from epics import PV
import time
import numpy as np

# Read/Write PVs
phase_error_pv = PV("SIM:PHASE:ERROR")
phase_setpoint_pv = PV("SIM:PHASE:SETPOINT")
phase_readback_pv = PV("SIM:PHASE:READBACK")
phase_corrected_pv = PV("SIM:PHASE:CORRECTED")
phase_drift_pv = PV("SIM:PHASE:DRIFT")
phase_drift_rate_pv = PV("SIM:PHASE:DRIFT_RATE")
pll_output_pv = PV("SIM:PLL:OUTPUT")
pll_center_pv = PV("SIM:PLL:CENTER")
pll_range_pv = PV("SIM:PLL:RANGE")
pll_lock_status_pv = PV("SIM:PLL:LOCK_STATUS")
beam_dump_pv = PV("SIM:BEAM:DUMP")
beam_reset_pv = PV("SIM:BEAM:RESET")
beam_reset_state_pv = PV("SIM:BEAM:RESET_STATE")
sim_start_pv = PV("SIM:START")
sim_reset_pv = PV("SIM:RESET")

# Master Oscillator PVs
mo_phase_pv = PV("SIM:MO:PHASE")
mo_phase_correction_pv = PV("SIM:MO:PHASE_CORRECTION")
mo_freq_pv = PV("SIM:MO:FREQ")
mo_freq_drift_pv = PV("SIM:MO:FREQ_DRIFT")
mo_lock_status_pv = PV("SIM:MO:LOCK_STATUS")

# Piezo Control PV
piezo_output_pv = PV("SIM:PIEZO:OUTPUT")

# Environmental Factor PVs
temp_lab_pv = PV("SIM:TEMP:LAB")
temp_fiber_pv = PV("SIM:TEMP:FIBER")
vibration_ext_pv = PV("SIM:VIBRATION:EXT")
power_stability_pv = PV("SIM:POWER:STABILITY")

# Sensitivity PVs (Configurable)
power_sensitivity_pv = PV("SENS:POWER")
temp_sensitivity_pv = PV("SENS:TEMP")
fiber_sensitivity_pv = PV("SENS:FIBER")
vibration_sensitivity_pv = PV("SENS:VIBRATION")
mo_temp_sensitivity_pv = PV("SENS:MO_TEMP")
piezo_correction_factor_pv = PV("SENS:PIEZO")

# Constants
MO_NOMINAL_FREQ = 162500000.00  # 162.5 MHz, nominal MO frequency
MO_FREQ_CORRECTION_RATE = 0.1  # Rate at which the MO frequency corrects itself (Hz per cycle)
MO_FREQ_UNLOCK_THRESHOLD = 1e5  # Deviation threshold before unlocking (0.1 MHz)

# Fetch sensitivity values dynamically
power_sensitivity = power_sensitivity_pv.get() or 10.0
temp_sensitivity = temp_sensitivity_pv.get() or 5.0
fiber_sensitivity = fiber_sensitivity_pv.get() or 2.0
vibration_sensitivity = vibration_sensitivity_pv.get() or 20.0
mo_temp_sensitivity = mo_temp_sensitivity_pv.get() or 2.0
piezo_correction_factor = piezo_correction_factor_pv.get() or 0.05

# Initial Values
current_mo_freq = MO_NOMINAL_FREQ
current_mo_phase = 0.0
current_phase_error = 0.0
current_phase_drift = 0.0
last_update_time = time.time()

#====================================================
def fetch_sensitivity_values():
    """Fetch sensitivity values dynamically to allow real-time updates."""
    global power_sensitivity, temp_sensitivity, fiber_sensitivity, vibration_sensitivity, mo_temp_sensitivity, piezo_correction_factor
    power_sensitivity = power_sensitivity_pv.get() or 10.0
    temp_sensitivity = temp_sensitivity_pv.get() or 5.0
    fiber_sensitivity = fiber_sensitivity_pv.get() or 2.0
    vibration_sensitivity = vibration_sensitivity_pv.get() or 20.0
    mo_temp_sensitivity = mo_temp_sensitivity_pv.get() or 2.0
    piezo_correction_factor = piezo_correction_factor_pv.get() or 0.05

#====================================================
def update_mo_phase_and_freq():
    """
    Simulates the behavior of the Master Oscillator (MO) in response to environmental factors.
    - The **MO frequency** drifts due to lab and fiber temperature fluctuations.
    - A **feedback correction** attempts to restore the MO frequency to its nominal value.
    - The **MO phase** accumulates based on frequency deviations over time.
    """
    global current_mo_freq, current_mo_phase, last_update_time

    fetch_sensitivity_values()

    # Get environmental values
    temp_lab = temp_lab_pv.get() or 22.0
    temp_fiber = temp_fiber_pv.get() or 22.0
    power_stability = power_stability_pv.get() or 1.0

    # Compute frequency drift based on environmental factors
    freq_drift = ((temp_lab - 22.0) * mo_temp_sensitivity +
                  (temp_fiber - 22.0) * fiber_sensitivity +
                  ((1.0 - power_stability) * power_sensitivity))
    current_mo_freq += freq_drift

    # Apply feedback correction to restore MO frequency to nominal value
    if abs(current_mo_freq - MO_NOMINAL_FREQ) > MO_FREQ_UNLOCK_THRESHOLD:
        mo_lock_status_pv.put(0)  # Unlock if deviation is too large
    else:
        correction = (MO_NOMINAL_FREQ - current_mo_freq) * MO_FREQ_CORRECTION_RATE
        current_mo_freq += correction
        mo_lock_status_pv.put(1)  # Lock once within range

    # Update MO phase drift based on frequency deviations
    dt = time.time() - last_update_time
    last_update_time = time.time()
    mo_phase_drift = (current_mo_freq - MO_NOMINAL_FREQ) * dt
    current_mo_phase += mo_phase_drift

    # Write updated values to PVs
    mo_freq_pv.put(current_mo_freq)
    mo_freq_drift_pv.put(freq_drift)
    mo_phase_pv.put(current_mo_phase)

    return current_mo_phase

#====================================================
def update_laser_phase_error():
    """
    Simulates laser phase drift and applies corrections using the Piezo system.
    - Laser phase error is influenced by fiber temp, lab temp, vibrations, and power fluctuations.
    - Piezo correction mitigates phase error but has a limited effect.
    """
    global current_phase_error, last_update_time

    fetch_sensitivity_values()

    # Get environmental values
    temp_fiber = temp_fiber_pv.get() or 22.0
    vibration_ext = vibration_ext_pv.get() or 0.0
    power_stability = power_stability_pv.get() or 1.0
    piezo_correction = piezo_output_pv.get() or 0.0

    # Compute phase error drift
    temp_drift = (temp_fiber - 22.0) * temp_sensitivity
    vibration_noise = np.random.uniform(-vibration_sensitivity, vibration_sensitivity) * vibration_ext
    power_drift = (1.0 - power_stability) * power_sensitivity
    piezo_adjustment = piezo_correction * piezo_correction_factor

    # Apply drift over time
    dt = time.time() - last_update_time
    last_update_time = time.time()
    phase_change = (temp_drift + vibration_noise + power_drift - piezo_adjustment) * dt * 0.1
    current_phase_error += phase_change

    # Write updated values to PVs
    phase_error_pv.put(current_phase_error)
    phase_readback_pv.put(current_phase_error)
    phase_drift_pv.put(current_phase_error)
    phase_drift_rate_pv.put(phase_change / dt if dt > 0 else 0.0)

#====================================================
def monitor_beam_status():
    """
    Monitors phase errors, MO behavior, and beam dump status.
    - Handles normal operation and beam dump detection.
    - Calls update functions for MO and Laser phase behavior.
    """
    global current_mo_freq, current_mo_phase, current_phase_error, current_phase_drift

    while True:
        if sim_start_pv.get() == 0:
            time.sleep(1)
            continue

        # Hold values if the beam is dumped
        if beam_dump_pv.get() == 1:
            print("🚨 Beam Dumped: Holding Values.")
            time.sleep(1)
            continue

        # Update MO and Laser Phase Separately
        update_mo_phase_and_freq()
        update_laser_phase_error()

        # Get current PLL range
        pll_range = pll_range_pv.get() or 50.0

        # Apply correction response
        pll_output_pv.put(current_phase_error / 2)
        phase_corrected_pv.put(current_phase_error / 3)

        # Handle Beam Dump if out of lock
        if abs(current_phase_error) > pll_range:
            print("🚨 Beam Dumped: Phase Out of Lock!")
            beam_dump_pv.put(1)

        time.sleep(1)

#====================================================
def handle_reset():
    """
    Monitors SIM:RESET PV and resets critical values when triggered.
    - If SIM:RESET is set to 1, all relevant PVs are zeroed.
    - After 2 seconds, SIM:RESET is set back to 0 automatically.
    """
    while True:
        if sim_reset_pv.get() == 1:
            print("🔄 Reset Triggered: Zeroing out phase values...")

            # Zero out relevant PVs
            phase_readback_pv.put(0.0)
            phase_drift_pv.put(0.0)
            phase_drift_rate_pv.put(0.0)
            pll_output_pv.put(0.0)
            piezo_output_pv.put(0.0)
            phase_corrected_pv.put(0.0)

            # Hold reset state for 2 seconds
            time.sleep(2)

            # Reset SIM:RESET PV back to 0
            sim_reset_pv.put(0)
            print("✅ Reset Complete: SIM:RESET cleared.")

        time.sleep(0.1)  # Check every 100ms

#====================================================
if __name__ == "__main__":
    print("✅ Phase Simulation Waiting for Start Signal...")
    while True:
        if sim_start_pv.get() == 1:
            print("🚀 Phase Simulation Started.")
            monitor_beam_status()
        time.sleep(1)
