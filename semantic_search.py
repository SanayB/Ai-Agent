import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# CONFIG
CHROMA_DB_DIR = "E:/my code"
COLLECTION_NAME = "cves"
MODEL_NAME = "all-MiniLM-L6-v2"
TOP_K = 5

# Connect to ChromaDB
client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
collection = client.get_or_create_collection(name=COLLECTION_NAME)
print("Connected to local ChromaDB collection.")

# Load SentenceTransformer Model
model = SentenceTransformer(MODEL_NAME)
print(f"Loaded model: {MODEL_NAME}")

# Take user input
query_text = input("Enter your search query: ")

# Encode input query
query_embedding = model.encode(query_text).tolist()

# Run search
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=TOP_K,
    include=["documents", "metadatas", "distances"]
)

# Handle empty collection
if not results["documents"] or not results["documents"][0]:
    print("No data found. Your collection may be empty. Please ingest CVE data first.")
    exit()

# Display results
print("\nTop Similar CVEs:\n")
for i in range(len(results["ids"][0])):
    print(f"Rank {i+1}:")
    print(f"  ID     : {results['ids'][0][i]}")
    print(f"  Desc   : {results['documents'][0][i]}")
    print(f"  Score  : {results['distances'][0][i]:.4f}")
    print("-" * 60)
