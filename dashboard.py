import streamlit as st
import chromadb
from langchain_ollama import OllamaLLM
from sentence_transformers import SentenceTransformer

from streamlit_autorefresh import st_autorefresh



# CONFIG
CHROMA_DB_DIR = "E:/my code/chromadb_store"
COLLECTION_NAME = "cves"
MODEL_NAME = "all-MiniLM-L6-v2"
TOP_K = 5

# Initialize
st.set_page_config(page_title="CVE Threat Dashboard", layout="wide")
st.title("🔐 CVE Threat Intelligence Dashboard")

# Load embedding model
embed_model = SentenceTransformer(MODEL_NAME)

# Connect to ChromaDB
client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
collection = client.get_or_create_collection(name=COLLECTION_NAME)

# Load and display recent CVEs
def load_recent_cves(n=5):
    results = collection.get(include=["documents", "metadatas"])
    combined = []
    for doc, meta in zip(results["documents"], results["metadatas"]):
        meta = meta or {}
        combined.append((doc, meta))
    combined.sort(key=lambda x: x[1].get("id", ""), reverse=True)
    return combined[-n:] if len(combined) >= n else combined

# Summarize CVEs using Ollama
def summarize_recent(docs):
    llm = OllamaLLM(model="gemma3", temperature=0.3)
    descriptions = [doc for doc, meta in docs if doc]
    print(descriptions)
    if not descriptions:
        return "No CVE descriptions available to summarize."

    prompt = (

        "You are a cybersecurity analyst.\n\n"
        "Summarize the following CVE vulnerability descriptions into bullet points.\n\n"
        "Descriptions:\n"
        f"{descriptions}\n\n"
        "For each CVE, include:\n"
        "- CVE ID (if available)\n"
        "- What it affects\n"
        "- Severity (if known)\n"
        "- Risk summary\n"
        "- 1 recommendation\n"
        "Format: Markdown bullet points."
    )
    return llm.invoke(prompt)

# if we want dont want to run ollama on pc we can run on kaggle(gpu for bigger models)


# def summarize_recent(docs):
#     descriptions = [doc for doc, meta in docs if doc]
#     if not descriptions:
#         return "No CVE descriptions available to summarize."

#     prompt = (
#         "You are a cybersecurity analyst.\n\n"
#         "Summarize the following CVE vulnerability descriptions into bullet points.\n\n"
#         "Descriptions:\n"
#         f"{descriptions}\n\n"
#         "For each CVE, include:\n"
#         "- CVE ID (if available)\n"
#         "- What it affects\n"
#         "- Severity (if known)\n"
#         "- Risk summary\n"
#         "- 1 recommendation\n"
#         "Format: Markdown bullet points."
#     )

#     try:
#         response = requests.post(
#             "https://main-oriole-grossly.ngrok-free.app/api/generate",
#             json={"model": "gemma3", "prompt": prompt},
#             timeout=30  # optional: prevent hanging
#         )
#         response.raise_for_status()

#         # Handle responses that may contain multiple JSON lines or extra output
#         raw = response.text.strip()

#         # Try to extract the first valid JSON object
#         first_brace = raw.find("{")
#         last_brace = raw.rfind("}")
#         if first_brace == -1 or last_brace == -1:
#             return "⚠️ Unexpected response format from remote Ollama."

#         json_str = raw[first_brace:last_brace+1]
#         data = json.loads(json_str)

#         return data.get("response", "✅ Remote call succeeded, but no 'response' field found.")

#     except requests.RequestException as e:
#         return f"⚠️ Error contacting remote Ollama: {e}"
#     except json.JSONDecodeError as e:
#         return f"⚠️ Failed to decode JSON from remote Ollama: {e}"


# Section: Recent CVEs
recent = load_recent_cves()

if not recent:
    st.warning(" No CVEs found in the database.")
else:
    st.subheader(" Recent CVEs")
    for i, (doc, meta) in enumerate(recent):
        cve_id = meta.get("id", "N/A")
        score = meta.get("cvss_score", "N/A")
        st.markdown(f"**{i+1}) CVE ID:** {cve_id} | **CVSS Score:** {score}")
        st.caption(doc)

    # Summary Section
    st.subheader(" LLM Summary (Last 5 CVEs)")
    summary = summarize_recent(recent)
    st.markdown(summary)

# Section: Semantic Search
st.subheader("🔍 Semantic Search CVEs")
query = st.text_input("Enter a search query (e.g., Remote Code Execution in Apache):")

if query:
    st.info(f"Searching for: '{query}'")

    # Encode the query
    query_embedding = embed_model.encode(query).tolist()

    # Search in ChromaDB
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=TOP_K,
        include=["documents", "metadatas", "distances"]
    )

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    dists = results.get("distances", [[]])[0]

    if docs:
        st.subheader("🎯 Top Semantic Matches")
        for i in range(len(docs)):
            meta = metas[i] or {}
            cve_id = meta.get("id", "N/A")
            score = meta.get("cvss_score", "N/A")
            distance = dists[i]
            st.markdown(f"**{i+1}) CVE ID:** {cve_id} | **CVSS Score:** {score} | **Similarity Score:** {distance:.4f}")
            st.caption(docs[i])
    else:
        st.warning("No matching CVEs found.")


#Auto refresh after 10 minutues
st_autorefresh(interval=600000, key="auto_refresh")
