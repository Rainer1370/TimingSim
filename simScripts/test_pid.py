from epics import PV
import time

# PID Gains
kp_pv = PV("SIM:PID:Kp")
ki_pv = PV("SIM:PID:Ki")
kd_pv = PV("SIM:PID:Kd")

# Define min/max range for cycling
min_value = 0.0
max_value = 5.0
step = 0.5  # Increment step

def cycle_pv_values():
    """Cycles PV values from min to max and back."""
    while True:
        # Ramp up
        for value in range(int(min_value * 10), int(max_value * 10) + 1, int(step * 10)):
            actual_value = value / 10.0
            write_and_verify(actual_value)
            time.sleep(0.5)

        # Ramp down
        for value in range(int(max_value * 10), int(min_value * 10) - 1, -int(step * 10)):
            actual_value = value / 10.0
            write_and_verify(actual_value)
            time.sleep(0.5)

def write_and_verify(value):
    """Writes and verifies PV updates."""
    kp_pv.put(value, wait=True)
    ki_pv.put(value / 2, wait=True)  # Slightly different values
    kd_pv.put(value / 3, wait=True)

    time.sleep(0.2)  # Allow updates to propagate

    kp = kp_pv.get()
    ki = ki_pv.get()
    kd = kd_pv.get()

    print(f"🔧 Written Values: Kp={value}, Ki={value/2}, Kd={value/3}")
    print(f"📡 Read Values: Kp={kp}, Ki={ki}, Kd={kd}")

    if kp == value and ki == value / 2 and kd == value / 3:
        print("✅ PVs updated successfully!")
    else:
        print("⚠️ PVs did not update correctly!")

if __name__ == "__main__":
    print("🚀 Starting PID Gain Cycling Test...")
    cycle_pv_values()
