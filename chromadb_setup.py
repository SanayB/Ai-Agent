import chromadb
from chromadb.config import Settings

client = chromadb.PersistentClient(path='E:/my code')


   

collection = client.get_or_create_collection("cves")
print("Local ChromaDB ready.")
