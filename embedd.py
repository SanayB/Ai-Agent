import json
from sentence_transformers import SentenceTransformer

#Pass input file 
INPUT_FILE = "E:/my code/project/cves.json"
OUTPUT_FILE = "embedded_cves.json"
MODEL_NAME = "all-MiniLM-L6-v2"

#Sentence transformer 
print(f"[INFO] Loading model: {MODEL_NAME}")
model = SentenceTransformer(MODEL_NAME)

# load file
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    raw = json.load(f)

vulns = raw.get("raw", {}).get("vulnerabilities", [])
print(f"[INFO] Found {len(vulns)} vulnerabilities")

#EXTRACT AND EMBED
embedded = []
for item in vulns:
    cve = item.get("cve", {})
    cve_id = cve.get("id", "")
    
    # Find English description
    desc_list = cve.get("descriptions", [])
    en_desc = next((d["value"] for d in desc_list if d.get("lang") == "en"), None)
    
    if en_desc:
        embedding = model.encode(en_desc).tolist()
        embedded.append({
            "id": cve_id,
            "description": en_desc,
            "embedding": embedding
        })

# Save to new file
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(embedded, f, indent=2, ensure_ascii=False)

print(f"[OK] Embedded {len(embedded)} CVEs to {OUTPUT_FILE}")

