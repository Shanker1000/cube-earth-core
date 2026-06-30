"""
drought.py — Drought risk detection using SMAP L4 (via AppEEARS)
Provides: root zone soil moisture percentile, surface moisture,
wilting fraction, precipitation — for drought stress monitoring
"""
import requests
import os
from datetime import datetime, timedelta

APPEEARS = "https://appeears.earthdatacloud.nasa.gov/api"

def get_token():
    username = os.environ['NASA_EARTHDATA_USER']
    password = os.environ['NASA_EARTHDATA_PASS']
    r = requests.post(f"{APPEEARS}/login", auth=(username, password), timeout=20)
    return r.json()['token']

def submit_drought_task(lat: float, lng: float, days: int = 60, task_name: str = "drought_check") -> str:
    """Submit AppEEARS point task for SMAP L4 drought layers. Returns task_id."""
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    task = {
        "task_type": "point",
        "task_name": task_name,
        "params": {
            "dates": [{
                "startDate": start_date.strftime("%m-%d-%Y"),
                "endDate": end_date.strftime("%m-%d-%Y")
            }],
            "layers": [
                {"product": "SPL4SMGP.008", "layer": "Geophysical_Data_sm_rootzone"},
                {"product": "SPL4SMGP.008", "layer": "Geophysical_Data_sm_rootzone_pctl"},
                {"product": "SPL4SMGP.008", "layer": "Geophysical_Data_sm_surface"},
                {"product": "SPL4SMGP.008", "layer": "Geophysical_Data_land_fraction_wilting"},
                {"product": "SPL4SMGP.008", "layer": "Geophysical_Data_precipitation_total_surface_flux"},
            ],
            "coordinates": [{"id": "parcel", "latitude": lat, "longitude": lng, "category": "field"}]
        }
    }
    r = requests.post(f"{APPEEARS}/task", json=task, headers=headers, timeout=30)
    return r.json().get('task_id')

def check_task_status(task_id: str) -> dict:
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{APPEEARS}/task/{task_id}", headers=headers, timeout=15)
    return r.json()

def get_drought_results(task_id: str) -> dict:
    """Download and parse results once task status == 'done'."""
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    bundle = requests.get(f"{APPEEARS}/bundle/{task_id}", headers=headers, timeout=15).json()
    files = bundle.get("files", [])
    csv_file = next((f for f in files if f["file_name"].endswith("-results.csv")), None)
    if not csv_file:
        return {"error": "No results CSV found"}

    csv_r = requests.get(f"{APPEEARS}/bundle/{task_id}/{csv_file['file_id']}",
                          headers=headers, timeout=60)
    lines = csv_r.text.strip().splitlines()
    if len(lines) < 2:
        return {"error": "No data rows"}

    header = lines[0].split(",")
    rows = []
    for line in lines[1:]:
        vals = line.split(",")
        if len(vals) != len(header):
            continue
        rows.append(dict(zip(header, vals)))

    return {"rows": rows, "count": len(rows)}

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        # Check status of existing task
        status = check_task_status(sys.argv[1])
        print(status)
    else:
        task_id = submit_drought_task(52.84, -6.93)
        print(f"Submitted: {task_id}")
