import time
import epics
import numpy as np

# Constants
HARMONIC_FACTOR = 8  # Laser frequency is 8x MO frequency
C = 3e8  # Speed of light in m/s

# Environmental sensitivity constants
THERMAL_COEFF = 2e-7  # Reduced thermal coefficient (1/°C)
VIBRATION_SENSITIVITY = 5e-12  # Reduced vibration sensitivity (m/m)
POWER_SENSITIVITY = 0.0005  # Power fluctuation impact factor
FIBER_LENGTH = 1000.0  # Fiber length in meters

# Drift Dynamics
DRIFT_DECAY = 0.9995  # Very slow accumulation of drift
NOISE_SCALE = 0.0005  # Small random fluctuations
PHASE_CORRECTION_SCALE = 0.02  # Softens effect of corrections
MAX_PHASE_STEP = 2.0  # 🔹 **Limits phase jump per step to ±5 fs**
LASER_PHASE_RANGE = 360 / HARMONIC_FACTOR  # 🔹 **Laser phase range is 45 degrees**


def calculate_environmental_drift(previous_drift):
    """
    Calculate phase drift due to temperature, vibration, and power fluctuations.

    Returns:
        float: Total phase drift in femtoseconds (fs).
    """
    # Retrieve environmental values from EPICS PVs (provided by envSim.py)
    fiber_temp = epics.caget("SIM:TEMP:FIBER") or 22.0  # Fiber temperature in °C
    lab_temp = epics.caget("SIM:TEMP:LAB") or 22.0  # Lab ambient temperature in °C
    vibration = epics.caget("SIM:VIBRATION:EXT") or 0.002  # External vibration amplitude
    power_stability = epics.caget("SIM:POWER:STABILITY") or 0.001  # Power fluctuation level

    # Compute phase drifts caused by environmental factors:
    temp_drift = THERMAL_COEFF * FIBER_LENGTH / C * (fiber_temp - lab_temp) * 1e15  # Convert to fs
    vibration_drift = VIBRATION_SENSITIVITY * FIBER_LENGTH * vibration * 1e15  # Convert to fs
    power_drift = POWER_SENSITIVITY * power_stability * 1e15  # Convert to fs

    # Gradual phase drift with leaky integration
    drift_factor = previous_drift * DRIFT_DECAY  # Slow accumulation of drift
    total_drift = drift_factor + temp_drift + vibration_drift + power_drift

    return total_drift


def initialize_laser():
    """
    Initialize laser PVs with proper values.

    Notes:
        - Sets the laser frequency to 8x the MO frequency.
        - Initializes the laser phase to match the MO phase.
        - Assumes the laser is locked initially.
    """
    mo_freq = epics.caget("SIM:MO:FREQ") or 162500000.0  # Default MO frequency (Hz)
    laser_freq = mo_freq * HARMONIC_FACTOR  # Calculate laser frequency

    # Fetch initial MO phase
    mo_phase = epics.caget("SIM:MO:PHASE") or 0.0
    laser_phase = (HARMONIC_FACTOR * mo_phase) % LASER_PHASE_RANGE  # 🔹 Constrain laser phase

    # Set frequency and phase-related PVs
    epics.caput("SIM:LASER:FREQ", laser_freq)
    epics.caput("SIM:LASER:FREQ_SP", laser_freq)
    epics.caput("SIM:LASER:FREQ_RB", laser_freq)

    # Set laser phase to initially match MO phase within the valid range
    epics.caput("SIM:LASER:PH_SP", laser_phase)
    epics.caput("SIM:LASER:PH_RB", laser_phase)

    # Initialize lock status
    epics.caput("SIM:LASER:LOCK_STATUS", 1)  # Assume locked initially

    print(f"✅ Laser Initialized: Freq {laser_freq / 1e6:.2f} MHz | Phase Synced to MO ({laser_phase:.2f} fs)")


def update_laser_phase():
    """
    Simulate laser phase drift and apply corrections from the PLL and Piezo system.

    Notes:
        - Continuously updates the laser phase based on environmental drift and corrections.
        - Updates the laser lock status and triggers a beam dump if the phase error exceeds the window.
    """
    previous_drift = 0.0  # Initialize drift memory

    while True:
        if epics.caget("SIM:START") == 0:
            time.sleep(1)
            continue

        # Fetch MO phase & frequency
        mo_phase = epics.caget("SIM:MO:PHASE") or 0.0
        mo_freq = epics.caget("SIM:MO:FREQ") or 162500000.0

        # Calculate expected laser frequency & phase
        laser_freq = mo_freq * HARMONIC_FACTOR
        target_phase = (HARMONIC_FACTOR * mo_phase) % LASER_PHASE_RANGE  # 🔹 Constrain laser phase range

        # Fetch current laser phase
        laser_phase = epics.caget("SIM:LASER:PH_RB") or target_phase

        # Apply environmental & noise effects
        phase_drift = calculate_environmental_drift(previous_drift)
        noise = np.random.normal(0, NOISE_SCALE)  # Small Gaussian noise
        total_drift = phase_drift + noise
        previous_drift = phase_drift  # Update drift memory

        # Apply correction from PLL & Piezo
        pll_correction = epics.caget("SIM:PLL:OUTPUT") or 0.0
        piezo_correction = epics.caget("SIM:PIEZO:OUTPUT") or 0.0
        correction = pll_correction + piezo_correction

        # Compute new phase shift with limited step size
        phase_shift = (total_drift - correction) * PHASE_CORRECTION_SCALE

        # **🔹 Clamp phase change to prevent extreme jumps**
        phase_shift = max(-MAX_PHASE_STEP, min(phase_shift, MAX_PHASE_STEP))

        # Update laser phase with constrained range
        laser_phase = (laser_phase + phase_shift) % LASER_PHASE_RANGE

        # Calculate phase error
        phase_error = abs(laser_phase - target_phase)

        # Update PVs
        epics.caput("SIM:LASER:PH_RB", laser_phase)
        epics.caput("SIM:LASER:PH_ERROR", phase_error)
        epics.caput("SIM:LASER:FREQ_RB", laser_freq)

        # Update Lock Status
        phase_error_window = epics.caget("SIM:LASER:PH_ERR_WIN") or 10.0  # Tightened error threshold
        if phase_error <= phase_error_window:
            epics.caput("SIM:LASER:LOCK_STATUS", 1)  # Laser Locked
        else:
            epics.caput("SIM:LASER:LOCK_STATUS", 0)  # Laser Unlocked
            epics.caput("SIM:BEAM:DUMP", 1)  # Trigger beam dump if unlocked

        time.sleep(1)  # Update at 1 Hz


if __name__ == "__main__":
    print("✅ Laser Phase Simulation Waiting for Start Signal...")
    initialize_laser()

    while True:
        if epics.caget("SIM:START") == 1:
            print("🚀 Laser Phase Simulation Started.")
            update_laser_phase()
        time.sleep(1)
