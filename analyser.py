
#create embeddings for the newly updated cves


import json
import chromadb
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

DATA_FILE = "cves.json"
MODEL_NAME = "all-MiniLM-L6-v2"
PERSIST_DIR = "E:/my code/chromadb_store"
COLLECTION_NAME = "cves"

def analyze_and_embed_new_cves():
    model = SentenceTransformer(MODEL_NAME)
    client = chromadb.PersistentClient(path=PERSIST_DIR)
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    existing_ids = set(collection.get()["ids"])

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    records = data.get("records", [])

    new_ids, new_docs, new_embeddings, new_metas = [], [], [], []

    for rec in tqdm(records, desc="Embedding CVEs"):
        cve_id = rec["id"]
    desc = rec["description"]
    score = rec.get("cvss_score")
    if score is None:
        score = -1.0  # Ensure valid float for ChromaDB metadata

    if cve_id not in existing_ids and isinstance(desc, str):
        embedding = model.encode(desc).tolist()
        new_ids.append(cve_id)
        new_docs.append(desc)
        new_embeddings.append(embedding)
        new_metas.append({"id": cve_id, "cvss_score": score})


    for i in range(0, len(new_ids), 100):
        collection.add(
            ids=new_ids[i:i+100],
            documents=new_docs[i:i+100],
            embeddings=new_embeddings[i:i+100],
            metadatas=new_metas[i:i+100],
        )

    print(f"Inserted {len(new_ids)} new CVEs into ChromaDB")
