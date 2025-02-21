import time
import numpy as np
import epics  # pyepics library

# Required PVs
REQUIRED_PVS = ["SIM:MO:FREQ", "SIM:MO:PHASE"]

def check_ioc_status():
    """Check if IOC is running and PVs exist."""
    ioc_status = epics.caget("IOC:STATUS")
    all_pvs_exist = all(epics.caget(pv) is not None for pv in REQUIRED_PVS)
    return ioc_status and all_pvs_exist

class MasterOscillator:
    """Simulates Master Oscillator (MO) frequency and phase drift."""
    def __init__(self):
        self.mo_freq = 162500000.0  # Initial MO frequency in Hz (162.5 MHz nominal)
        self.mo_phase = 0.0  # Initial phase in degrees
        self.phase_window = 90.0  # Phase is constrained within a 90-degree window
        self.last_update_time = time.time()

    def update_mo_with_feedback(self):
        """Simulates MO phase drift and applies correction feedback."""
        while True:
            if not check_ioc_status():
                print("⏳ IOC is down. Pausing Master Oscillator simulation...")
                while not check_ioc_status():
                    time.sleep(2)  # Wait until IOC comes back
                print("✅ IOC restored. Resuming simulation...")

            try:
                current_time = time.time()
                dt = current_time - self.last_update_time  # Time step
                self.last_update_time = current_time

                # Fetch environmental factors
                temp_lab = epics.caget("SIM:TEMP:LAB") or 22.0
                vibration_ext = epics.caget("SIM:VIBRATION:EXT") or 0.0
                power_stability = epics.caget("SIM:POWER:STABILITY") or 1.0

                # Compute frequency drift
                k_T = 0.02  # Hz/°C (temperature sensitivity)
                k_V = 0.01  # Hz/(m/s²) (vibration sensitivity)
                k_P = 0.015  # Hz/% (power stability sensitivity)

                temp_drift = k_T * (temp_lab - 22.0)  # Reference temp = 22°C
                vibration_drift = k_V * vibration_ext
                power_drift = k_P * (1.0 - power_stability)

                external_drift = temp_drift + vibration_drift + power_drift
                external_drift = max(-0.02, min(0.02, external_drift))  # Prevent runaway drift

                # Small natural frequency fluctuation
                natural_drift = np.random.uniform(-0.05, 0.05)

                # Feedback Correction (PLL) - Correct toward nominal frequency
                correction_strength = 0.02
                pll_feedback = (162500000.0 - self.mo_freq) * correction_strength  

                # Update MO frequency
                self.mo_freq += natural_drift + external_drift + pll_feedback
                self.mo_freq = max(162499950.0, min(162500050.0, self.mo_freq))  # Keep within range

                # Apply some noise to phase
                self.mo_phase += np.random.uniform(-1.0, 1.0)
                self.mo_phase = max(0, min(self.phase_window, self.mo_phase))  # Constrain phase

                # ✅ **Print debug messages before writing to PVs**
                #print(f"🔹 Updating PVs - SIM:MO:FREQ={self.mo_freq}, SIM:MO:PHASE={self.mo_phase:.2f}")

                # ✅ **Update PVs**
                epics.caput("SIM:MO:FREQ", self.mo_freq)
                epics.caput("SIM:MO:PHASE", self.mo_phase)

                time.sleep(1)  # 1 Hz update rate

            except Exception as e:
                print(f"⚠️ Error in moSim.py: {e}")
                time.sleep(5)  # Wait before retrying

if __name__ == "__main__":
    print("Starting Master Oscillator Simulation...")
    mo = MasterOscillator()
    mo.update_mo_with_feedback()
