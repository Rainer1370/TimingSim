import subprocess
import os
import time
from datetime import datetime
from epics import PV

# EPICS PVs for status updates
beam_dump_pv = PV("SIM:BEAM:DUMP")
message1 = PV("SIM:STATUS:1")
message2 = PV("SIM:STATUS:2")
#mo_phase_lock = PV("SIM:MO:LOCK_STATUS",1)
#pll_phase_lock = PV("SIM:PLL:LOCK_STATUS",1)

# Get the absolute path to the script directory
script_dir = os.path.abspath(os.path.dirname(__file__))

# Track subprocesses
processes = []

def start_simulation():
    """Start phase simulation and PID control as subprocesses."""
    global processes
    if processes:
        message1.put("Simulation already started")
        return  # Already running

    print("🚀 Starting Simulation...")
    phase_proc = subprocess.Popen(["python3", os.path.join(script_dir, "phase_sim.py")])
    pid_proc = subprocess.Popen(["python3", os.path.join(script_dir, "pid_control.py")])
    processes = [phase_proc, pid_proc]

    message1.put("Simulation Started at:")
    message2.put(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("✅ Simulation started.")

def pause_simulation():
    """Pauses the simulation when the beam dumps."""
    global processes
    if not processes:
        return  # Nothing to stop

    print("🚨 Beam Dump detected. Pausing simulation.")

    for proc in processes:
        proc.terminate()
    for proc in processes:
        proc.wait()

    processes = []

    message1.put("Simulation Paused at:")
    message2.put(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("✅ Simulation paused due to beam dump.")

def monitor_beam_dump():
    """Monitors beam dump PV and manages simulation state."""
    beam_dumped = False  # Track beam dump state

    while True:
        beam_status = beam_dump_pv.get()

        if beam_status == 1 and not beam_dumped:
            pause_simulation()
            beam_dumped = True  # Prevent repeat calls

        if beam_status == 0 and beam_dumped:
            print("🔄 Beam Dump cleared. Restarting simulation.")

            message1.put("Simulation Restarted at:")
            message2.put(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

            start_simulation()
            beam_dumped = False  # Reset flag

        time.sleep(1)  # Prevent CPU overuse

if __name__ == "__main__":
    print("✅ Simulation Manager Running. Monitoring Beam Dump...")
    start_simulation()  # Initial startup message
    monitor_beam_dump()
