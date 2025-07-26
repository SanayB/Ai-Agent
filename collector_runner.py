# collector_runner.py

from scraper1 import fetch, extract_records, load_existing, save
import datetime

FILENAME = "cves.json"

def collect_new_cves():
    print(f"\n Running Collector (runner) at {datetime.datetime.utcnow().isoformat()}Z")
    try:
        raw = fetch()
        new_records = extract_records(raw)
        existing = load_existing(FILENAME)
        old_ids = {r["id"] for r in existing["records"]}
        unique = [r for r in new_records if r["id"] not in old_ids]

        if unique:
            save(FILENAME, existing, new_records, raw)
            print(f" Added {len(unique)} new CVEs.")
        else:
            print(" No new CVEs found.")
        return bool(unique)
    except Exception as e:
        print(f" Error during collection: {e}")
        return False
