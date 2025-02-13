from epics import PV
import time
import numpy as np

# Read/Write PVs
laser_phase_error_pv = PV("SIM:LASER:PH_ERROR")
laser_phase_setpoint_pv = PV("SIM:LASER:PH_SP")
laser_phase_readback_pv = PV("SIM:LASER:PH_RB")
laser_phase_corrected_pv = PV("SIM:LASER:PH_CORR")
laser_phase_drift_pv = PV("SIM:LASER:PH_DRIFT")
laser_phase_drift_rate_pv = PV("SIM:LASER:PH_DRIFT_RATE")
pll_output_pv = PV("SIM:PLL:OUTPUT")
pll_center_pv = PV("SIM:PLL:CENTER")
pll_range_pv = PV("SIM:PLL:RANGE")
pll_lock_status_pv = PV("SIM:PLL:LOCK_STATUS")
beam_dump_pv = PV("SIM:BEAM:DUMP")
beam_reset_pv = PV("SIM:BEAM:RESET")
beam_reset_state_pv = PV("SIM:BEAM:RESET_STATE")
sim_start_pv = PV("SIM:START")
sim_reset_pv = PV("SIM:RESET")

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

# MO Phase
mo_phase_pv = PV("SIM:MO:PHASE")
mo_freq_pv = PV("SIM:MO:FREQ")

# Fetch sensitivity values dynamically
power_sensitivity = power_sensitivity_pv.get() or 10.0
temp_sensitivity = temp_sensitivity_pv.get() or 5.0
fiber_sensitivity = fiber_sensitivity_pv.get() or 2.0
vibration_sensitivity = vibration_sensitivity_pv.get() or 20.0
piezo_correction_factor = piezo_correction_factor_pv.get() or 0.05

# Initial Values
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
    piezo_correction_factor = piezo_correction_factor_pv.get() or 0.05

#====================================================
def update_laser_phase_error():
    """
    Simulates laser phase drift and applies corrections using the Piezo system.
    - The laser phase error is influenced by fiber temp, lab temp, vibrations, and power fluctuations.
    - The Piezo correction helps compensate for phase deviations.
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
    laser_phase_error_pv.put(current_phase_error)
    laser_phase_readback_pv.put(current_phase_error)
    laser_phase_drift_pv.put(current_phase_error)
    laser_phase_drift_rate_pv.put(phase_change / dt if dt > 0 else 0.0)

#====================================================
def monitor_beam_status():
    """
    Monitors phase error and triggers a beam dump if the error exceeds a defined window.
    - Calls update_laser_phase_error() to track drift.
    - Dumps the beam if phase error exceeds the defined lock window.
    - Resets when SIM:RESET is triggered.
    """
    global current_phase_error

    # Define the phase error limit for a beam dump
    phase_error_limit = 50.0  # Example: Max allowed phase deviation in fs

    while True:
        if sim_start_pv.get() == 0:
            time.sleep(1)
            continue

        # Hold values if the beam is dumped
        if beam_dump_pv.get() == 1:
            print("🚨 Beam Dumped: Holding Values.")
            time.sleep(1)
            continue

        # Update Laser Phase Error
        update_laser_phase_error()

        # Apply correction response
        pll_output_pv.put(current_phase_error / 2)
        phase_corrected_pv.put(current_phase_error / 3)

        # Check if phase error exceeds allowable limit
        if abs(current_phase_error) > phase_error_limit:
            print(f"🚨 Beam Dumped: Phase Error ({current_phase_error} fs) Exceeded {phase_error_limit} fs!")
            beam_dump_pv.put(1)

        time.sleep(1)

#====================================================
def handle_reset():
    """
    Monitors SIM:RESET PV and realigns the laser phase to match a harmonic of the MO phase.
    - Ensures the laser phase is reset relative to the MO phase.
    - The phase error is recomputed to ensure it starts from zero after locking.
    """
    while True:
        if sim_reset_pv.get() == 1:
            print("🔄 Reset Triggered: Locking Laser Phase to MO Phase...")

            # Fetch current Master Oscillator phase
            mo_phase = mo_phase_pv.get() or 0.0  # Default to 0 if unavailable

            # Define harmonic factor (LCLS-II laser runs at 8x MO frequency)
            harmonic_factor = 8  

            # Compute new laser phase based on harmonic relationship
            laser_phase = harmonic_factor * mo_phase  # Laser phase locked to MO

            # Compute new phase error (Laser phase should match MO phase after reset)
            phase_error = laser_phase - mo_phase * harmonic_factor

            # Update PVs with new values
            laser_phase_readback_pv.put(laser_phase)
            laser_phase_drift_pv.put(laser_phase)
            laser_phase_error_pv.put(phase_error)  # Reset error to match MO phase
            laser_phase_drift_rate_pv.put(0.0)  # Reset drift rate

            # Hold reset state for 2 seconds
            time.sleep(2)

            # Reset SIM:RESET PV back to 0
            sim_reset_pv.put(0)
            print("✅ Reset Complete: Laser Phase Locked to MO.")

        time.sleep(0.1)  # Check every 100ms

#====================================================
if __name__ == "__main__":
    print("✅ Phase Simulation Waiting for Start Signal...")
    while True:
        if sim_start_pv.get() == 1:
            print("🚀 Phase Simulation Started.")
            monitor_beam_status()
        time.sleep(1)
