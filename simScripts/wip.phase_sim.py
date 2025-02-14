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

    # Trigger beam dump if phase error exceeds dynamic phase window
    if phase_error > phase_error_window_deg:
        print(f"\U0001F6A8 Beam Dumped: Phase Error {phase_error}° exceeded limit {phase_error_window_deg}°")
        beam_dump_pv.put(1)

if __name__ == "__main__":
    print("✅ Phase Simulation Waiting for Start Signal...")
    while True:
        if sim_start_pv.get() == 1:
            print("🚀 Phase Simulation Started.")
            while sim_start_pv.get() == 1:
                update_laser_phase()
                time.sleep(1)  # Run at 1 Hz update rate
        time.sleep(1)






'''

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

# Define HARMONIC_FACTOR globally
HARMONIC_FACTOR = 8  # Laser phase is 8x MO phase

# Piezo PVs
piezo_output_pv = PV("SIM:PIEZO:OUTPUT")
piezo_fs_per_volt_pv = PV("SIM:PLL:FS_PER_VOLT")

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
laser_phase_readback = mo_phase_pv.get()

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
"""
📌 Phase Response Function (Updated with Unit Explanations)

The laser phase response governs how the laser phase evolves over time based on:

    - Environmental effects (temperature, vibrations, power fluctuations).
    - Correction mechanisms:
        - Piezo feedback (fine adjustments).
        - PLL output (broadband stabilization).
    - Phase alignment with MO harmonic (8× MO phase).
    - Beam dump occurs when laser phase deviates **beyond the dynamically calculated phase error window**.

🚀 **Updated Mathematical Model**

The laser phase, θ_L, evolves over time as:

    θ_L(t+Δt) = θ_L(t) + Δθ_env - Δθ_corr

### **Units Breakdown**
_________________________________________________________________________________________________________________________
| Symbol           	| Description                                      	| Default Units 			|
|-----------------------|-------------------------------------------------------|---------------------------------------|
| θ_L (Laser Phase) 	| Absolute phase of the laser 				| **degrees (°)** 			|
| θ_MO (MO Phase) 	| Absolute phase of the Master Oscillator (MO) 		| **degrees (°)** 			|
| k_T 			| Sensitivity of laser phase to temperature changes 	| **fs/°C** 				|
| k_V 			| Sensitivity of laser phase to vibrations 		| **fs/(m/s²)** 			|
| k_P 			| Sensitivity of laser phase to power stability changes | **fs/%** 				|
| Δθ_env 		| Phase drift due to environmental factors 		| **fs** 				|
| Δθ_corr 		| Correction applied to compensate drift (Piezo & PLL) 	| **fs** 				|
| k_PLL 		| Correction factor for PLL adjustments 		| **unitless scaling factor** 		|
| θ_PLL 		| PLL output correction 				| **fs** 				|
| k_Piezo 		| Correction factor for Piezo adjustments 		| **unitless scaling factor** 		|
| θ_Piezo 		| Piezo correction output 				| **fs** 				|
| k_align 		| Gradual alignment factor for phase lock 		| **unitless scaling factor** 		|
| Phase_Error_Window 	| Allowable phase deviation before beam dump 		| **fs → converted to degrees (°)** 	|
| T_cycle 		| Period of the MO cycle 				| **fs (1 MO period in femtoseconds)** 	|
-------------------------------------------------------------------------------------------------------------------------

### **Phase Components and their Influence**

1️⃣ **Environmental Drift Contribution**
   - The environmental phase drift **Δθ_env** is calculated as:

     Δθ_env = k_T (temp_fiber - 22.0) + k_V (vibration) + k_P (1 - power_stability)

   - This represents how external conditions cause the laser phase to shift **(units: fs).**

2️⃣ **Corrections from Control Systems**
   - The applied corrections **Δθ_corr** compensate for drift and are calculated as:

     Δθ_corr = k_PLL ⋅ θ_PLL + k_Piezo ⋅ θ_Piezo

   - **PLL correction:** Provides broadband phase stabilization.
   - **Piezo correction:** Provides fine-tuned phase adjustment.
   - These corrections are in **fs** to counteract environmental drift.

3️⃣ **Phase Locking to the MO Harmonic**
   - The laser must remain **phase-locked** to the **8th harmonic** of the Master Oscillator:

     θ_L = (θ_L + k_align (θ_MO × 8 - θ_L)) mod 360

   - Here, **θ_L** is kept within **0-360°** to ensure proper locking.
   - **k_align** determines how quickly the phase lock correction is applied.

4️⃣ **Dynamic Beam Dump Trigger**
   - If the laser phase deviates too far from the MO phase reference, a beam dump is triggered:

     |θ_L - θ_MO × 8| > Phase_Error_Window -> (all in ° here)

   - The phase error window is dynamically calculated as:

     θ_err_win(°) = [θ_err_win(fs) x 360] / T_cycle (fs)

   - **This ensures that the beam dump threshold adapts to changes in MO frequency.**

---

🚀 **Summary of Unit Conversions**
- **Environmental drift, corrections, and PLL/Piezo adjustments** are in **fs**.
- **Laser phase & MO phase** are kept in **degrees** (°).
- **Phase Error Window is dynamically converted** from **fs → degrees** based on the **MO cycle period**.

✅ This ensures **consistent unit handling** across all calculations.
"""
#====================================================
def update_laser_phase():
    """Simulates laser phase drift and applies corrections from the PLL and Piezo system."""
    global current_phase_error, last_update_time, HARMONIC_FACTOR

    fetch_sensitivity_values()

    # Read environmental factors
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

    # Trigger beam dump if phase error exceeds dynamic phase window
    if phase_error > phase_error_window_deg:
        print(f"\U0001F6A8 Beam Dumped: Phase Error {phase_error}° exceeded limit {phase_error_window_deg}°")
        beam_dump_pv.put(1)

'''
def update_laser_phase():
    """Simulates laser phase drift and applies corrections from the PLL and Piezo system."""
    global current_phase_error, last_update_time, HARMONIC_FACTOR

    fetch_sensitivity_values()

    # Read environmental factors
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

    laser_phase += phase_change - total_correction  # Apply corrections

    # Ensure phase aligns with MO harmonic
    mo_freq = mo_freq_pv.get() or 162500000.0  # Default MO frequency (Hz)

    # Compute dynamic phase error window
    mo_cycle_time_fs = (1e15 / mo_freq)  # Convert period to fs
    phase_error_window_fs = phase_error_window_pv.get() or 45.0  # Default phase window
    phase_error_window_deg = (phase_error_window_fs * 360) / mo_cycle_time_fs  # Convert to degrees

    # Compute target phase (harmonic alignment)
    target_phase = (HARMONIC_FACTOR * mo_phase) % 360
    correction_step = (target_phase - laser_phase) * 0.05  # Gradual alignment
    laser_phase += correction_step

    # Constrain values
    laser_phase = (laser_phase + 360) % 360
    phase_error = abs(laser_phase - target_phase) % 360

    # Update PVs
    laser_phase_readback_pv.put(laser_phase)
    laser_phase_drift_pv.put(laser_phase)
    laser_phase_error_pv.put(phase_error)
    laser_phase_drift_rate_pv.put(phase_change / dt if dt > 0 else 0.0)

    # Trigger beam dump if phase error exceeds dynamic phase window
    if phase_error > phase_error_window_deg:
        print(f"\U0001F6A8 Beam Dumped: Phase Error {phase_error}° exceeded limit {phase_error_window_deg}°")
        beam_dump_pv.put(1)
'''
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

            # Align laser phase directly to MO phase
            laser_phase = mo_phase

            # Compute new phase error (Laser phase should match MO phase after reset)
            phase_error = 0.0  # No initial error after reset

            # Update PVs with new values
            laser_phase_readback_pv.put(laser_phase)
            laser_phase_drift_pv.put(laser_phase)
            laser_phase_error_pv.put(phase_error)  # Reset error to zero
            laser_phase_drift_rate_pv.put(0.0)  # Reset drift rate

            # Hold reset state for 2 seconds
            time.sleep(2)

            # Reset SIM:RESET PV back to 0
            sim_reset_pv.put(0)
            print("✅ Reset Complete: Laser Phase Locked to MO.")

        time.sleep(0.1)  # Check every 100ms

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
        laser_phase_corrected_pv.put(current_phase_error / 3)

        # Check if phase error exceeds allowable limit
        if abs(current_phase_error) > phase_error_limit:
            print(f"🚨 Beam Dumped: Phase Error ({current_phase_error} fs) Exceeded {phase_error_limit} fs!")
            beam_dump_pv.put(1)

        time.sleep(1)

#====================================================
if __name__ == "__main__":
    print("✅ Phase Simulation Waiting for Start Signal...")
    while True:
        if sim_start_pv.get() == 1:
            print("🚀 Phase Simulation Started.")
            while sim_start_pv.get() == 1:
                update_laser_phase()
                time.sleep(1)  # Run at 1 Hz update rate
        time.sleep(1)
'''
# 
