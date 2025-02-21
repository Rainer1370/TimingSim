import time
import datetime
import numpy as np
import epics  # pyepics library

# Constants for Environmental Simulations
BASE_TEMP = 22.0  # Average lab temperature in °C
TEMP_AMPLITUDE = 2.5  # Amplitude of temperature swings
CYCLE_PERIOD = 86400  # Diurnal cycle period in seconds (24 hours)

# PVs required for simulation
REQUIRED_PVS = ["SIM:TEMP:LAB", "SIM:TEMP:FIBER", "SIM:VIBRATION:EXT", "SIM:POWER:STABILITY"]

def check_ioc_status():
    """Check if IOC is running and PVs exist."""
    ioc_status = epics.caget("IOC:STATUS")
    all_pvs_exist = all(epics.caget(pv) is not None for pv in REQUIRED_PVS)
    return ioc_status and all_pvs_exist

def update_environmental_factors():
    """Simulates diurnal temperature changes, vibration spikes, and power fluctuations."""
    while True:
        if not check_ioc_status():
            print("⏳ IOC is down. Pausing environmental simulation...")
            while not check_ioc_status():
                time.sleep(2)  # Wait until IOC comes back
            print("✅ IOC restored. Resuming simulation...")

        try:
            now = datetime.datetime.now()

            # 🔹 **Temperature follows a diurnal cycle**
            seconds_since_midnight = now.hour * 3600 + now.minute * 60 + now.second
            diurnal_temp_offset = TEMP_AMPLITUDE * np.sin((2 * np.pi * seconds_since_midnight) / CYCLE_PERIOD)

            # 🌡️ **Simulate realistic temperature cycles**
            temp_lab = BASE_TEMP + diurnal_temp_offset
            temp_fiber = temp_lab + np.random.uniform(-0.5, 0.5)  # Fiber temp variation based on Lab Temp

            # 🔨 **Realistic Vibration Effects**
            vibration_ext = epics.caget("SIM:VIBRATION:EXT") or 0.0
            vibration_noise = np.random.normal(0, 0.02)  # Small random background noise

            # 📌 **5% chance of a construction-related vibration spike**
            if np.random.random() < 0.05:
                vibration_noise += np.random.uniform(0.2, 0.5)

            # 🔄 **Decay Effect: Gradually return vibration to baseline**
            vibration_ext = max(0, (vibration_ext + vibration_noise) * 0.97)

            # ⚡ **Power Stability Fluctuations**
            power_stability = epics.caget("SIM:POWER:STABILITY") or 1.0
            power_stability += np.random.uniform(-0.01, 0.01)  # Small random fluctuations
            power_stability = max(0.95, min(1.05, power_stability))  # Keep within [0.95, 1.05]

            # ✅ **Write updates to PVs**
            epics.caput("SIM:TEMP:LAB", temp_lab)
            epics.caput("SIM:TEMP:FIBER", temp_fiber)
            epics.caput("SIM:VIBRATION:EXT", vibration_ext)
            epics.caput("SIM:POWER:STABILITY", power_stability)

            time.sleep(1)  # Update every second

        except Exception as e:
            print(f"⚠️ Error in envSim.py: {e}")
            time.sleep(5)  # Wait before retrying

if __name__ == "__main__":
    print("Starting Environmental Simulation...")
    update_environmental_factors()
