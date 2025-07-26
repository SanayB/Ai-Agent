# collector.py

from crewai import Agent
from scraper1 import fetch, extract_records, load_existing, save
import pandas as pd
import schedule
import datetime

FILENAME = "cves.json"

# Collector logic
def collect_new_cves():
    print(f"\n Running Collector at {datetime.datetime.utcnow().isoformat()}Z")
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
        return bool(unique)  # ✅ ← ADDED LINE: return True/False
    except Exception as e:
        print(f" Error during collection: {e}")
        return False  # ✅ ← In case of error, return False too

# Set up the agent (optional metadata for future CrewAI tasks)
collector_agent = Agent(
    role="Threat Intelligence Collector",
    goal="Keep the vulnerability database up to date",
    backstory="You fetch new CVEs regularly from the NVD API.",
    verbose=False
)

# Schedule the collector to run every 10 minutes
schedule.every(10).minutes.do(collect_new_cves)

print(" Collector scheduled to run every 10 minutes.")
collect_new_cves()  # Run once at startup

# Loop forever and run pending tasks
while True:
    schedule.run_pending()
