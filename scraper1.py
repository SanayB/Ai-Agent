import sys
import requests
import pandas as pd
import json
import os

# Configure UTF-8 encoding for Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

FILENAME = "cves.json"

# Fetch CVE data from NVD API
def fetch():
    url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    try:
        resp = requests.get(url, headers={"Accept": "application/json"})
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        raise Exception(f"Failed to fetch data: {e}")

# Extract CVE records with ID, dates, description, CVSS score, and references
def extract_records(data):
    records = []
    for entry in data.get("vulnerabilities", []):
        cve = entry.get("cve", {})
        rec = {
            "id": cve.get("id", "Unknown"),
            "published": cve.get("published", "Unknown"),
            "lastModified": cve.get("lastModified", "Unknown"),
            "description": "No English description",
            "cvss_score": cve.get("metrics", {}).get("cvssMetricV31", [{}])[0].get("cvssData", {}).get("baseScore", "Unknown")
        }
        for desc in cve.get("descriptions", []):
            if desc.get("lang") == "en":
                rec["description"] = desc.get("value", "No description available")
                break
        rec["references"] = [r.get("url") for r in cve.get("references", [])]
        records.append(rec)
    return records

# Load existing JSON file if it exists
def load_existing(filename):
    if not os.path.exists(filename):
        return {"fetched_at": None, "raw": None, "records": []}
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

# Save new records, merging with existing ones
def save(filename, existing, new_records, raw):
    combined = existing
    old_ids = {r["id"] for r in combined["records"]}
    unique = [r for r in new_records if r["id"] not in old_ids]
    combined["records"].extend(unique)
    combined["fetched_at"] = pd.Timestamp.utcnow().isoformat() + "Z"
    combined["raw"] = raw
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)
    print(f"Appended {len(unique)} new records, saved to {filename}")

def main():
    try:
        raw = fetch()   #get the details from nvd
        new = extract_records(raw)
        existing = load_existing(FILENAME)    #add new nvds into existing file
        df = pd.DataFrame(new)    #convert new records to DataFrame
        print(df[["id", "published", "lastModified", "cvss_score"]].head())
        save(FILENAME, existing, new, raw)   #save everything in the file
    except Exception as e:
        print(f"Error: {e}")   #print failed to fetch data

if __name__ == "__main__":
    main()