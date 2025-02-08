from epics import PV
import time
import simple_pid
import math
import numpy as np

# Read/Write PVs
phase_error_pv = PV("SIM:PHASE:ERROR")
pll_output_pv = PV("SIM:PLL:OUTPUT")
phase_corrected_pv = PV("SIM:PHASE:CORRECTED")
piezo_output_pv = PV("SIM:PIEZO:OUTPUT")
pll_center_pv = PV("SIM:PLL:CENTER")
pll_range_pv = PV("SIM:PLL:RANGE")
beam_dump_pv = PV("SIM:BEAM:DUMP")
beam_reset_pv = PV("SIM:BEAM:RESET")
sim_start_pv = PV("SIM:SIMULATION:START")

def monitor_beam_status():
    """Monitor beam dump status and reset phase error when cleared."""
    while True:
        if sim_start_pv.get() == 0:
            print("🛑 Simulation Stopped. Beam Dumped.")
            beam_dump_pv.put(1)
            phase_error_pv.put(0.0)
            pll_output_pv.put(0.0)
            phase_corrected_pv.put(0.0)
            time.sleep(1)
            continue

        if beam_reset_pv.get() == 1:
            print("✅ Beam Reset Triggered. Restoring Phase Error to PLL Center.")
            phase_error_pv.put(pll_center_pv.get() or 0.0)
            beam_dump_pv.put(0)
            time.sleep(0.5)
            beam_reset_pv.put(0)
            print("🔄 Reset cleared.")

        # Ensure PLL range is valid
        pll_range = pll_range_pv.get() or 50.0  # Default if None

        # Read piezo output
        piezo_correction = piezo_output_pv.get() or 0.0

        # Simulate phase error responding to Piezo movement
        phase_error = np.random.uniform(-0.05, 0.05) - piezo_correction * 0.1
        phase_error_pv.put(phase_error)
        pll_output_pv.put(phase_error / 2)
        phase_corrected_pv.put(phase_error / 3)

        # Handle beam dump properly
        if abs(phase_error) > pll_range:
            print("🚨 Beam Dumped: Phase Out of Lock!")
            beam_dump_pv.put(1)

        time.sleep(1)

if __name__ == "__main__":
    print("✅ Phase Simulation Waiting for Start Signal...")
    while True:
        if sim_start_pv.get() == 1:
            print("🚀 Phase Simulation Started.")
            monitor_beam_status()
        time.sleep(1)  # Prevent CPU overuse

