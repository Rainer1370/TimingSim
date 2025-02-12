from pcaspy import Driver, SimpleServer
import numpy as np
import time
import signal
import sys
import subprocess
import os
import json
import threading
import datetime

# Define EPICS PVs
prefix = "SIM:"

# Load PVs from external JSON file
pvdb_path = os.path.join(os.path.dirname(__file__), "pvdb.json")
with open(pvdb_path, "r") as f:
    pvdb = json.load(f)

# Define IOC-specific PVs outside of the "SIM:" namespace
ioc_pvdb = {
    "IOC:HEARTBEAT": {"type": "int", "value": 0},
    "IOC:START_TIME": {"type": "string", "value": ""}
}

# Constants for Environmental Simulations
BASE_TEMP = 22.0  # Average lab temperature in °C
TEMP_AMPLITUDE = 2.5  # Amplitude of temperature swings
CYCLE_PERIOD = 86400  # Diurnal cycle period in seconds (24 hours)

class PhaseDriftIOC(Driver):
    def __init__(self):
        super().__init__()
        self.simulation_running = False
        self.initialize_pvs()
        self.write_pv_list()

        # Start environmental factor updates
        self.env_thread = threading.Thread(target=self.update_environmental_factors, daemon=True)
        self.env_thread.start()

        # Start the heartbeat PV
        self.heartbeat_thread = threading.Thread(target=self.heartbeat_pv, daemon=True)
        self.heartbeat_thread.start()

        # Store IOC Start Time
        self.setParam("IOC:START_TIME", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.updatePVs()

    def initialize_pvs(self):
        """Ensures all PVs are initialized with their default values to prevent disconnections."""
        for pv_name, properties in pvdb.items():
            if "type" in properties and properties["type"] == "enum":
                properties["value"] = int(properties["value"])
            elif pv_name.startswith("PID:"):
                properties["value"] = 0.0  # Ensure PID gains start at 0

            self.setParam(pv_name, properties["value"])

        # Initialize IOC-specific PVs
        for pv_name, properties in ioc_pvdb.items():
            self.setParam(pv_name, properties["value"])
            self.setParamStatus(pv_name, 0, 0)  # Ensure no alarms on startup
        self.updatePVs()

    def write_pv_list(self):
        """Writes the current PV list to `dbl.txt` with a timestamp."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dbl_path = os.path.join(os.path.dirname(__file__), "dbl.txt")
        with open(dbl_path, "w") as f:
            f.write(f"# PV List Generated on {timestamp}\n\n")
            for pv_name in pvdb.keys():
                f.write(f"{prefix}{pv_name}\n")
            for pv_name in ioc_pvdb.keys():
                f.write(f"{pv_name}\n")
        print(f"✅ PV list saved to dbl.txt (Timestamp: {timestamp})")

    def update_environmental_factors(self):
        """Simulates diurnal temperature changes and external disturbances."""
        while True:
            now = datetime.datetime.now()
        #========================================================
        # Temperature follows a diurnal cycle, so we use a sin wave here and reference TOD
            seconds_since_midnight = now.hour * 3600 + now.minute * 60 + now.second
            diurnal_temp_offset = TEMP_AMPLITUDE * np.sin((2 * np.pi * seconds_since_midnight) / CYCLE_PERIOD)

        # 🌡️ **Simulate realistic temperature cycles**
            temp_lab = BASE_TEMP + diurnal_temp_offset
            # Fiber temp variation based off Lab Temp as a base
            temp_fiber = temp_lab + np.random.uniform(-0.5, 0.5)

        #========================================================
        # 🔨 **Realistic Construction & Vibration Effects**
            vibration_ext = self.getParam("VIBRATION:EXT") or 0.0
            # Small background noise,
            # We'll just throw in a 5% chance of momentary vibration
            vibration_noise = np.random.normal(0, 0.02)

            # 📌 **Random Construction Spikes (5% chance)**
            if np.random.random() < 0.05:
                vibration_noise += np.random.uniform(0.2, 0.5)
            #    print("🚨 Construction Vibration Spike Detected!") 
            # Depends on how verbose you want the code

        # 🔄 **Decay Effect: Gradually return vibration to baseline**
            # - Vibration decays by ** Maybe 3%? **, ensuring it doesn't accumulate indefinitely.
            # - Can be adjusted to model longer (or shorter) damping effects.
            vibration_ext = max(0, (vibration_ext + vibration_noise) * 0.97)  # Modify decay rate if needed

        #========================================================
        # ⚡ **Power Stability Fluctuations**
            power_stability = self.getParam("POWER:STABILITY") or 1.0
            # 📌 **Random fluctuations in power**
            power_stability += np.random.uniform(-0.01, 0.01)
            # I remember how unstable PG&E can be, but we can modify this if needed
            # 🔄 **Decay Effect: Gradually return to 1.0**
            power_stability += (1.0 - power_stability) * 0.1  # Smoothly correct deviations
            # ✅ Keep within safe range
            power_stability = max(0.95, min(1.05, power_stability))
            # ⚡ **Power Stability Fluctuations**
            # - Power fluctuates slightly within a safe range
            #   (0.95 - 1.05)
            # - If power deviates from **1.0**, it gradually returns
            #   by correcting **10% per update**.

        #========================================================
        # 📝 **Apply Updates to PVs**
            self.setParam("TEMP:LAB", temp_lab)
            self.setParam("TEMP:FIBER", temp_fiber)
            self.setParam("VIBRATION:EXT", vibration_ext)
            self.setParam("POWER:STABILITY", power_stability)

            self.updatePVs()
            time.sleep(5)  # Update every 5 seconds

        #========================================================
        # 🔹 **Why This (MIGHT) Work**
        # ----------------------------------------
        # ✅ **Realistic Temperature Behavior**:
        # - Lab temperature follows a natural diurnal cycle (24-hour sine wave).
        # - Fiber temperature varies slightly with random fluctuations (±0.5°C).
        #
        # ✅ **Improved Vibration Model**:
        # - Normally fluctuates with small background noise.
        # - **5% chance of construction spikes**, which momentarily increases vibration.
        # - **Decay Effect**: Vibrations gradually return to baseline (0.95x per update).
        #
        # ✅ **Improved Power Stability Model**:
        # - Power fluctuates slightly within a safe range (0.95 - 1.05).
        # - **Decay Effect**: If power deviates too far, it gradually returns to `1.0`
        #   by applying a 10% correction per update.
        #
        # ✅ **Why This is Important**:
        # - Prevents runaway effects where vibration and power instability accumulate.
        # - Simulates real-world lab conditions where external disturbances settle over time.
        # - Creates a **more accurate model** for evaluating system stability & control response.
        # (I also created some tools in the GUI to throw in random earthquakes, brown-outs, etc.)
        #========================================================

    def heartbeat_pv(self):
        """Updates the heartbeat PV every second, toggling between 0 and 1."""
        while True:
            current_heartbeat = self.getParam("IOC:HEARTBEAT")
            self.setParam("IOC:HEARTBEAT", 1 - current_heartbeat)  # Toggle between 0 and 1
            self.updatePVs()
            time.sleep(1)  # 1Hz update rate

    def start_simulation(self):
        """Starts the simulation by launching simulation_manager.py."""
        if self.simulation_running:
            print("🚀 Simulation already running.", flush=True)
            return

        print("🚀 Starting simulation...", flush=True)
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "simulation_manager.py")

        if not os.path.exists(script_path):
            print(f"❌ Error: simulation_manager.py not found at {script_path}", flush=True)
            return

        subprocess.Popen(["python", script_path])
        self.simulation_running = True
        self.setParam("START", 1)
#        self.setParam("STATUS:1", "Simulation Started at:")
#        self.setParam("STATUS:2", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.updatePVs()

    def stop_simulation(self):
        """Stops the simulation by killing related processes."""
        if not self.simulation_running:
            print("🛑 Simulation already stopped.", flush=True)
            return

        print("🛑 Stopping simulation...", flush=True)
        subprocess.call(["pkill", "-f", "simulation_manager.py"])
        subprocess.call(["pkill", "-f", "phase_sim.py"])
        subprocess.call(["pkill", "-f", "pid_control.py"])
        self.simulation_running = False
        self.setParam("START", 0)
        self.setParam("STATUS:1", "Simulation Stopped at:")
        self.setParam("STATUS:2", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.setParam("STATUS:3", "")
        self.setParam("STATUS:4", "")
        self.updatePVs()

    def write(self, reason, value):
        """Handles PV writes to control the simulation."""
        # print(f"📝 Attempting to write: {reason} = {value}", flush=True)

        if reason == "START":
            if value == 1:
                # print("🚀 Received Start Command", flush=True)
                self.setParam("START", 1)
                self.setParamStatus("START", 0, 0)  # No alarm
                self.start_simulation()
            else:
                # print("🛑 Received Stop Command", flush=True)
                self.setParam("START", 0)
                self.setParamStatus("START", 0, 0)  # No alarm
                self.stop_simulation()
            self.updatePVs()
            return True  # Ensure pcaspy processes the write

        elif reason == "BEAM:DUMP":
            print(f"🔹 Current value before change: {self.getParam('BEAM:DUMP')}", flush=True)

            if value in [0, 1]:  # Ensure valid index
                self.setParam("BEAM:DUMP", value)
                self.setParam("STATUS:3", "Beam Dumped at")
                self.setParam("STATUS:4", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                self.updatePVs()
                # print(f"✅ Updated BEAM:DUMP to {value} ({['On', 'Dumped'][value]})", flush=True)
            else:
                print(f"⚠️ Invalid value for BEAM:DUMP: {value}", flush=True)

            return True  # Ensure pcaspy processes the write

        elif reason == "BEAM:RESET":
            if value == 1:  # Reset only when BEAM:RESET is set to 1
                # print("🔄 Resetting BEAM:DUMP to On (0)", flush=True)
                self.setParam("BEAM:DUMP", 0)  # Force reset to "On"
                self.updatePVs()
                time.sleep(0.1)  # Small delay to ensure change propagates
                self.setParam("BEAM:RESET", 0)  # Automatically reset BEAM:RESET
                self.updatePVs()
                self.setParam("STATUS:3", "BEAM RESET")  # Update status
                self.setParam("STATUS:4", "")
                # print("✅ BEAM:DUMP reset successfully.", flush=True)

            return True  # Ensure pcaspy processes the write

        return super().write(reason, value)

def main():
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    server = SimpleServer()
    server.createPV(prefix, pvdb)
    server.createPV("", ioc_pvdb)
    driver = PhaseDriftIOC()
    print("✅ Soft IOC running. Press Ctrl+C to stop.")
    while True:
        server.process(1.0)

if __name__ == "__main__":
    main()
