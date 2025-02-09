import sqlite3
import csv
import sys

# Database location
db_filename = "/home/rain/Scripts/TimingSim/data/epics_archive.db"

def fetch_pv_history(pv_name, start_time=None, end_time=None, output_csv="pv_history.csv"):
    """Fetch historical PV data and export it as a CSV file."""
    conn = sqlite3.connect(db_filename)
    cursor = conn.cursor()

    query = "SELECT timestamp, value FROM epics_archive WHERE pv_name=?"
    params = [pv_name]

    if start_time and end_time:
        query += " AND timestamp BETWEEN ? AND ?"
        params.extend([start_time, end_time])

    query += " ORDER BY timestamp ASC"

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    
    if not rows:
        print(f"⚠️ No historical data found for {pv_name}.")
        return

    # Write to CSV
    with open(output_csv, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["timestamp", "value"])  # Header
        writer.writerows(rows)
    
    print(f"✅ Exported {len(rows)} records for {pv_name} to {output_csv}")

    conn.close()

# If run from the command line
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fetch_pv_history.py <PV_NAME> [start_time] [end_time]")
        sys.exit(1)
    
    pv_name = sys.argv[1]
    start_time = sys.argv[2] if len(sys.argv) > 2 else None
    end_time = sys.argv[3] if len(sys.argv) > 3 else None
    
    fetch_pv_history(pv_name, start_time, end_time)
