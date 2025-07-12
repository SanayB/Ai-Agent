import chromadb
from chromadb.config import Settings

# Connect to your local ChromaDB
client = chromadb.PersistentClient(path="E:/my code")
collection = client.get_or_create_collection("cves")

# Example search query
query = "remote code execution via buffer overflow"

# Perform semantic search
results = collection.query(
    query_texts=[query],
    n_results=5  # Number of closest results to fetch
)

# Display the results
for i, doc in enumerate(results['documents'][0]):
    print(f"\n Result #{i+1}")
    print(f"ID: {results['ids'][0][i]}")
    print(f"Description: {doc}")
