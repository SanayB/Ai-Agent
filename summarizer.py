from langchain_ollama import OllamaLLM
import json

def generate_summary_with_llm():
    print("   Running LLM summarizer (Ollama)...")

    try:
        with open("embedded_cves.json", "r", encoding="utf-8") as f:
            records = json.load(f)
    except FileNotFoundError:
        print("   File 'embedded_cves.json' not found.")
        return

    recent_docs = [r["description"] for r in records[-5:] if "description" in r]

    if not recent_docs:
        print("   No descriptions found to summarize.")
        return

    llm = OllamaLLM(model="gemma3", temperature=0.3)

    prompt = f"""
You are a cybersecurity analyst.

Summarize the following CVE vulnerability descriptions into Markdown bullet points.

Descriptions:
{recent_docs}

For each CVE, include:
- CVE ID (if available)
- What it affects
- Severity (if known)
- Risk summary (plain English)
- 1 short recommendation

Format: Markdown bullet points.
"""

    response = llm.invoke(prompt)

    print("\n Summary Output:\n")
    print(response)

    # Optional: return summary if needed elsewhere (e.g., for dashboard)
    return response
