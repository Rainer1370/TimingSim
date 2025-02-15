from epics import PV
import time
import numpy as np
from datetime import datetime  # Import datetime for timestamp

# Read/Write PVs
laser_phase_error_pv = PV("SIM:LASER:PH_ERROR")
laser_phase_setpoint_pv = PV("SIM:LASER:PH_SP")
laser_phase_readback_pv = PV("SIM:LASER:PH_RB")
laser_phase_corrected_pv = PV("SIM:LASER:PH_CORR")
laser_phase_drift_pv = PV("SIM:LASER:PH_DRIFT")
laser_phase_drift_rate_pv = PV("SIM:LASER:PH_DRIFT_RATE")
phase_error_window_pv = PV("SIM:LASER:PH_ERR_WIN")
k_align_pv = PV("SIM:LASER:K_ALIGN")
pll_output_pv = PV("SIM:PLL:OUTPUT")
pll_fs_per_volt_pv = PV("SIM:PLL:FS_PER_VOLT")
pll_center_pv = PV("SIM:PLL:CENTER")
pll_range_pv = PV("SIM:PLL:RANGE")
pll_lock_status_pv = PV("SIM:PLL:LOCK_STATUS")
beam_dump_pv = PV("SIM:BEAM:DUMP")
beam_reset_pv = PV("SIM:BEAM:RESET")
beam_reset_state_pv = PV("SIM:BEAM:RESET_STATE")
sim_start_pv = PV("SIM:START")
sim_reset_pv = PV("SIM:RESET")

# Status Message PVs
message1_pv = PV("SIM:STATUS:1")
message2_pv = PV("SIM:STATUS:2")
message3_pv = PV("SIM:STATUS:3")
message4_pv = PV("SIM:STATUS:4")

# Define HARMONIC_FACTOR globally
HARMONIC_FACTOR = 8  # Laser phase is 8x MO phase

# Piezo PVs
piezo_output_pv = PV("SIM:PIEZO:OUTPUT")
piezo_fs_per_volt_pv = PV("SIM:PLL:FS_PER_VOLT")

# Environmental Factor PVs (Updated by envSim.py)
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
mo_lock_status_pv = PV("SIM:MO:LOCK_STATUS")

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
laser_phase_readback = mo_phase_pv.get()

def initialize_simulation():
    """Initialize the simulation by setting laser phase setpoint and readback to MO phase."""
    mo_phase = mo_phase_pv.get() or 0.0  # Get MO phase
    laser_phase_setpoint_pv.put(mo_phase)  # Set laser phase setpoint to MO phase
    laser_phase_readback_pv.put(mo_phase)  # Set laser phase readback to MO phase

    # Set lock statuses to "Locked"
    pll_lock_status_pv.put(1)  # Set PLL lock status to "Locked"
    mo_lock_status_pv.put(1)  # Set MO lock status to "Locked"

    # Update status messages
    message1_pv.put("Simulation Started at")
    message2_pv.put(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    print("✅ Simulation Initialized: Laser phase setpoint and readback aligned to MO phase.")
    print("✅ PLL and MO lock statuses set to 'Locked'.")
    print("✅ Status messages updated.")

def fetch_sensitivity_values():
    """Fetch sensitivity values dynamically to allow real-time updates."""
    global power_sensitivity, temp_sensitivity, fiber_sensitivity, vibration_sensitivity, mo_temp_sensitivity, piezo_correction_factor
    power_sensitivity = power_sensitivity_pv.get() or 10.0
    temp_sensitivity = temp_sensitivity_pv.get() or 5.0
    fiber_sensitivity = fiber_sensitivity_pv.get() or 2.0
    vibration_sensitivity = vibration_sensitivity_pv.get() or 20.0
    piezo_correction_factor = piezo_correction_factor_pv.get() or 0.05

def update_laser_phase():
    """Simulates laser phase drift and applies corrections from the PLL and Piezo system."""
    global current_phase_error, last_update_time, HARMONIC_FACTOR

    fetch_sensitivity_values()

    # Read environmental factors (updated by envSim.py)
    temp_fiber = temp_fiber_pv.get() or 22.0
    vibration_ext = vibration_ext_pv.get() or 0.0
    power_stability = power_stability_pv.get() or 1.0

    # Compute phase drift due to environment
    temp_drift = (temp_fiber - 22.0) * temp_sensitivity
    vibration_noise = np.random.uniform(-vibration_sensitivity, vibration_sensitivity) * vibration_ext
    power_drift = (1.0 - power_stability) * power_sensitivity

    # Apply drift over time
    dt = time.time() - last_update_time
    last_update_time = time.time()
    phase_change = (temp_drift + vibration_noise + power_drift) * dt * 0.1

    # Apply Piezo and PLL corrections
    piezo_correction = piezo_output_pv.get() or 0.0
    pll_correction = pll_output_pv.get() or 0.0
    total_correction = piezo_correction + pll_correction

    # Ensure laser phase starts at MO phase if uninitialized
    mo_phase = mo_phase_pv.get() or 0.0
    laser_phase = laser_phase_readback_pv.get()

    if laser_phase is None or laser_phase == 0.0:
        laser_phase = mo_phase  # Align laser phase with MO phase on startup
        laser_phase_readback_pv.put(laser_phase)  # Ensure it's written to the PV

    # Apply calculated drift and correction
    laser_phase += phase_change - total_correction  # Apply drift & correction

    # Ensure phase aligns with MO harmonic
    mo_freq = mo_freq_pv.get() or 162500000.0  # Default MO frequency (Hz)
    mo_cycle_time_fs = (1e15 / mo_freq)  # Convert period to fs

    phase_error_window_fs = phase_error_window_pv.get() or 45.0  # Default phase window
    phase_error_window_deg = (phase_error_window_fs * 360) / mo_cycle_time_fs  # Convert to degrees

    # Compute target phase (harmonic alignment)
    target_phase = (HARMONIC_FACTOR * mo_phase) % 360

    # **Apply a more stable correction step**
    k_align = k_align_pv.get() or 0.05  # Ensure reasonable alignment speed
    correction_step = k_align * (target_phase - laser_phase)  # Gradual locking to MO harmonic phase
    laser_phase += correction_step

    # Constrain values (avoid jumps)
    laser_phase = (laser_phase + 360) % 360
    phase_error = abs(laser_phase - target_phase) % 360

    # Ensure **continuous updates** of the laser phase PV
    laser_phase_readback_pv.put(laser_phase)
    laser_phase_drift_pv.put(phase_change)
    laser_phase_error_pv.put(phase_error)
    laser_phase_drift_rate_pv.put(phase_change / dt if dt > 0 else 0.0)

    # **Update Lock Statuses**
    if phase_error <= phase_error_window_deg:
        pll_lock_status_pv.put(1)  # PLL Locked
        mo_lock_status_pv.put(1)  # MO Locked
    else:
        pll_lock_status_pv.put(0)  # PLL Unlocked
        mo_lock_status_pv.put(0)  # MO Unlocked

    # Trigger beam dump if phase error exceeds dynamic phase window
    if phase_error > phase_error_window_deg:
        print(f"\U0001F6A8 Beam Dumped: Phase Error {phase_error}° exceeded limit {phase_error_window_deg}°")
        beam_dump_pv.put(1)

if __name__ == "__main__":
    print("✅ Phase Simulation Waiting for Start Signal...")
    initialize_simulation()  # Initialize simulation on startup
    while True:
        if sim_start_pv.get() == 1:
            print("🚀 Phase Simulation Started.")
            while sim_start_pv.get() == 1:
                update_laser_phase()
                time.sleep(1)  # Run at 1 Hz update rate
        time.sleep(1)
