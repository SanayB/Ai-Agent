import sys
import requests
import pandas as pd
import json
import os

if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

FILENAME = "cves_.json"


#give file name or url to read
def fetch():
    url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    resp = requests.get(url, headers={"Accept": "application/json"}) #http request using .get method
    resp.raise_for_status()#check the response code
    return resp.json()



#extract records based on parameters .get is used because we only want to fetch the data
#get the id, published date, last modified date, description in english and references
def extract_records(data):
    records = []
    for entry in data.get("vulnerabilities", []):
        cve = entry.get("cve", {})
        rec = {
            "id": cve.get("id"),
            "published": cve.get("published"),
            "lastModified": cve.get("lastModified"),
        }
        for desc in cve.get("descriptions", []):
            if desc.get("lang") == "en":
                rec["description"] = desc.get("value")
                break
        rec["references"] = [r.get("url") for r in cve.get("references", [])]
        records.append(rec)
    return records

#load existing file instead of creating a new one
def load_existing(filename):
    if not os.path.exists(filename):
        return {"fetched_at": None, "raw": None, "records": []}
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

def save(filename, existing, new_records, raw):
    combined = existing
    # Merge unique new records based on CVE ID
    old_ids = {r["id"] for r in combined["records"]}
    unique = [r for r in new_records if r["id"] not in old_ids]
    combined["records"].extend(unique)
    combined["fetched_at"] = pd.Timestamp.utcnow().isoformat() + "Z"
    combined["raw"] = raw
    # Write back updated data
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)
    print(f"Appended {len(unique)} new records, saved to {filename}")

def main():
    raw = fetch()
    new = extract_records(raw)
    existing = load_existing(FILENAME)
    df = pd.DataFrame(new)
    print(df[["id", "published", "lastModified"]].head())
    save(FILENAME, existing, new, raw)

if __name__ == "__main__":
    main()
