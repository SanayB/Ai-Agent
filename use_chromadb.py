import json
import chromadb
from chromadb.config import Settings

# Step 1: Connect to local ChromaDB
client = chromadb.PersistentClient(path="E:/my code")
collection = client.get_or_create_collection("cves")
print("[OK] Connected to local ChromaDB")

# Step 2: Load the embedded JSON data
with open("embedded_cves.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Step 3: Extract IDs, Descriptions, and Embeddings
ids = [entry["id"] for entry in data]
docs = [entry["description"] for entry in data]
embeds = [entry["embedding"] for entry in data]

# Optional: Split into chunks if large
BATCH_SIZE = 500
for i in range(0, len(ids), BATCH_SIZE):
    collection.add(
        ids=ids[i:i+BATCH_SIZE],
        documents=docs[i:i+BATCH_SIZE],
        embeddings=embeds[i:i+BATCH_SIZE]
    )
    print(f"[+] Uploaded {i+BATCH_SIZE} CVEs...")

print(f"Uploaded {len(ids)} total CVEs to ChromaDB!")
