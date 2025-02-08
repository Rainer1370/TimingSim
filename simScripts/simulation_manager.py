import subprocess
import signal
import os
import sys
import time
from epics import PV

# EPICS PVs for control
sim_start_pv = PV("SIM:SIMULATION:START")
beam_dump_pv = PV("SIM:BEAM:DUMP")
beam_reset_pv = PV("SIM:BEAM:RESET")

# Get the absolute path to `simScripts/` directory
script_dir = os.path.abspath(os.path.dirname(__file__))

# Track subprocesses
processes = []

def start_simulation():
    """Start phase simulation and PID control as subprocesses."""
    global processes
    if processes:
        print("🚀 Simulation is already running.")
        return

    print("🚀 Starting Simulation Manager...")

    # Start the subprocesses with absolute paths
    phase_proc = subprocess.Popen(["python", os.path.join(script_dir, "phase_sim.py")])
    pid_proc = subprocess.Popen(["python", os.path.join(script_dir, "pid_control.py")])

    processes = [phase_proc, pid_proc]

    print("✅ Phase Simulation and PID Control started.")

def stop_simulation():
    """Stops all simulation processes."""
    global processes
    if not processes:
        print("🛑 Simulation already stopped. No action taken.")
        return

    print("🛑 Stopping Simulation...")
    
    # Kill all subprocesses
    for proc in processes:
        proc.terminate()
    for proc in processes:
        proc.wait()  # Ensures they fully stop before resetting

    processes = []
    print("✅ All simulation processes stopped.")

def monitor_simulation():
    """Monitors PVs and manages simulation state."""
    while True:
        sim_status = sim_start_pv.get()
        beam_status = beam_dump_pv.get()

        if sim_status == 1 and not processes:
            start_simulation()

        if sim_status == 0 and processes:
            stop_simulation()

        if beam_status == 1:  # Beam dumped, stop everything
            print("🚨 Beam Dump detected. Stopping simulation.")
            stop_simulation()

        if beam_reset_pv.get() == 1 and not processes:
            print("🔄 Beam Reset detected. Restarting simulation.")
            start_simulation()

        time.sleep(1)  # Prevent CPU overuse

def handle_exit(signum, frame):
    """Ensure clean shutdown on exit signals."""
    print("🔄 Exiting Simulation Manager...")
    stop_simulation()
    sys.exit(0)

# Handle termination signals
signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

if __name__ == "__main__":
    print("✅ Simulation Manager Running. Waiting for Start Signal...")
    monitor_simulation()
