import time
import numpy as np
import epics  # pyepics library

class MasterOscillator:
    """
    Simulates Master Oscillator (MO) frequency and phase drift.
    - Updates `SIM:MO:FREQ` (MO Frequency).
    - Updates `SIM:MO:PHASE` (MO Phase).
    - Applies environmental factors (temperature, vibration, power).
    - Uses feedback correction (PLL) to stabilize drift.
    - Models phase as random fluctuations within a 90-degree window.
    """
    def __init__(self):
        self.mo_freq = 162500000.0  # Initial MO frequency in Hz (162.5 MHz nominal)
        self.mo_phase = 0.0  # Initial phase in degrees
        self.last_update_time = time.time()
        self.freq_drift_buffer = []
        self.buffer_size = 10  # Rolling average filter for frequency drift
        self.phase_window = 90.0  # Phase is constrained within a 90-degree window

    def update_mo_with_feedback(self):
        """Simulates MO phase drift and applies correction feedback."""
        while True:
            current_time = time.time()
            dt = current_time - self.last_update_time  # Time step
            self.last_update_time = current_time

            # 🔹 **Fetch Environmental Factors from EPICS PVs**
            temp_lab = epics.caget("SIM:TEMP:LAB") or 22.0  # Default to 22°C
            vibration_ext = epics.caget("SIM:VIBRATION:EXT") or 0.0
            power_stability = epics.caget("SIM:POWER:STABILITY") or 1.0

            # 🔹 **Compute Frequency Drift from Environmental Factors**
            k_T = 0.02  # Hz/°C (temperature sensitivity)
            k_V = 0.01  # Hz/(m/s²) (vibration sensitivity)
            k_P = 0.015  # Hz/% (power stability sensitivity)

            temp_drift = k_T * (temp_lab - 22.0)  # Reference temperature = 22°C
            vibration_drift = k_V * vibration_ext
            power_drift = k_P * (1.0 - power_stability)

            external_drift = temp_drift + vibration_drift + power_drift
            external_drift = max(-0.02, min(0.02, external_drift))  # Prevent runaway drift

            # 🔹 **Natural Frequency Drift (Small Random Walk)**
            natural_drift = np.random.uniform(-0.05, 0.05)  # Small fluctuation in Hz

            # 🔹 **Feedback Correction (PLL)**
            correction_strength = 0.02
            pll_feedback = (162500000.0 - self.mo_freq) * correction_strength  # Correct toward nominal freq

            # 🔹 **Update MO Frequency**
            self.mo_freq += natural_drift + external_drift + pll_feedback

            # Apply rolling average for stability
            self.freq_drift_buffer.append(self.mo_freq)
            if len(self.freq_drift_buffer) > self.buffer_size:
                self.freq_drift_buffer.pop(0)

            self.mo_freq = sum(self.freq_drift_buffer) / len(self.freq_drift_buffer)  # Smoothed freq update

            # ✅ **Constrain frequency within ±50 Hz from nominal**
            self.mo_freq = max(162499950.0, min(162500050.0, self.mo_freq))

            # 🔹 **Update Phase with Random Fluctuations**
            phase_fluctuation = np.random.uniform(-1.0, 1.0)  # Random fluctuation in degrees
            self.mo_phase += phase_fluctuation

            # ✅ **Constrain Phase within a 90-degree window**
            if self.mo_phase < 0:
                self.mo_phase = 0
            elif self.mo_phase > self.phase_window:
                self.mo_phase = self.phase_window

            # ✅ **Update PVs**
            epics.caput("SIM:MO:FREQ", self.mo_freq)
            epics.caput("SIM:MO:PHASE", self.mo_phase)

            print(f"Updated PVs: SIM:MO:FREQ={self.mo_freq}, SIM:MO:PHASE={self.mo_phase:.2f}")

            time.sleep(1)  # 1 Hz update rate


# Main execution block
if __name__ == "__main__":
    try:
        print("Starting Master Oscillator simulation...")
        mo = MasterOscillator()
        mo.update_mo_with_feedback()
    except Exception as e:
        print(f"Error in main execution: {e}")
