import time
import epics  # Use EPICS caget/caput for PV access
import numpy as np

HARMONIC_FACTOR = 8  # Laser frequency is 8x MO frequency

def initialize_laser():
    """Initialize laser PVs with proper values."""
    mo_freq = epics.caget("SIM:MO:FREQ") or 162500000.0  # Default MO frequency (Hz)
    laser_freq = mo_freq * HARMONIC_FACTOR  # Calculate laser frequency

    # Set frequency-related PVs
    epics.caput("SIM:LASER:FREQ", laser_freq)
    epics.caput("SIM:LASER:FREQ_SP", laser_freq)
    epics.caput("SIM:LASER:FREQ_RB", laser_freq)

    # Set initial phase to match MO phase
    mo_phase = epics.caget("SIM:MO:PHASE") or 0.0
    epics.caput("SIM:LASER:PH_SP", mo_phase)
    epics.caput("SIM:LASER:PH_RB", mo_phase)

    # Initialize lock status
    epics.caput("SIM:LASER:LOCK_STATUS", 1)  # Assume locked initially

    print("✅ Laser Initialized: Frequency & Phase Synced with Master Oscillator.")

def update_laser_phase():
    """Simulates laser phase drift and applies corrections from the PLL and Piezo system."""
    while True:
        if epics.caget("SIM:START") == 0:
            time.sleep(1)
            continue

        # Fetch MO phase & frequency
        mo_phase = epics.caget("SIM:MO:PHASE") or 0.0
        mo_freq = epics.caget("SIM:MO:FREQ") or 162500000.0

        # Calculate expected laser frequency & phase
        laser_freq = mo_freq * HARMONIC_FACTOR
        target_phase = (HARMONIC_FACTOR * mo_phase) % 360

        # Fetch current laser phase
        laser_phase = epics.caget("SIM:LASER:PH_RB") or target_phase

        # Apply environmental & noise effects
        phase_drift = np.random.uniform(-0.1, 0.1)  # Small random drift (in fs)
        total_drift = phase_drift  # Could add thermal, vibration, power effects here

        # Apply correction from PLL & Piezo
        pll_correction = epics.caget("SIM:PLL:OUTPUT") or 0.0
        piezo_correction = epics.caget("SIM:PIEZO:OUTPUT") or 0.0
        correction = pll_correction + piezo_correction

        # Update laser phase
        laser_phase += total_drift - correction

        # Keep phase within 360-degree cycle
        laser_phase = (laser_phase + 360) % 360
        phase_error = abs(laser_phase - target_phase) % 360

        # Update PVs
        epics.caput("SIM:LASER:PH_RB", laser_phase)
        epics.caput("SIM:LASER:PH_ERROR", phase_error)
        epics.caput("SIM:LASER:FREQ_RB", laser_freq)

        # Update Lock Status
        phase_error_window = epics.caget("SIM:LASER:PH_ERR_WIN") or 45.0
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
