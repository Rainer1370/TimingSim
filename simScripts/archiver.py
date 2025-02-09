import sqlite3
import time
import os
from epics import PV

# Database path
db_dir = "/home/rain/Scripts/TimingSim/data"
db_filename = os.path.join(db_dir, "epics_archive.db")

# Ensure database directory exists
if not os.path.exists(db_dir):
    os.makedirs(db_dir)  # Create directory if missing

# Ensure database table exists
def initialize_database():
    """Creates the SQLite database and table if they don't exist."""
    conn = sqlite3.connect(db_filename)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS epics_archive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            pv_name TEXT,
            value REAL
        )
    """)
    conn.commit()
    conn.close()

# Call once at startup
initialize_database()

def log_pv_update(pvname, value, **kwargs):
    """Logs the PV update into the SQLite database using a separate connection per thread."""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        conn = sqlite3.connect(db_filename, check_same_thread=False)  # Allow cross-thread access
        cursor = conn.cursor()
        cursor.execute("INSERT INTO epics_archive (timestamp, pv_name, value) VALUES (?, ?, ?)", (timestamp, pvname, value))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"⚠️ SQLite Error: {e}")

# Load monitored PVs dynamically from `dbl.txt`
dbl_file = "/home/rain/Scripts/TimingSim/simScripts/iocs/dbl.txt"

pvs_to_monitor = []
try:
    with open(dbl_file, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):  # Exclude comments and empty lines
                pvs_to_monitor.append(line)

    print(f"✅ Monitoring {len(pvs_to_monitor)} PVs from dbl.txt")
except FileNotFoundError:
    print("⚠️ Warning: dbl.txt not found. Archiver will not monitor any PVs.")

# Attach callbacks to all PVs in `dbl.txt`
pv_objects = [PV(pv, callback=log_pv_update) for pv in pvs_to_monitor]

print("✅ Archiver Running. Logging PV updates...")

# Keep script running
while True:
    time.sleep(1)
