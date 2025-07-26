from collector import collect_new_cves
from analyser import analyze_and_embed_new_cves
from summarizer import generate_summary_with_llm

def run_workflow():
    print("[1] Checking and collecting new CVEs...")
    try:
        has_new = collect_new_cves()
    except Exception as e:
        print(f"   Collector failed: {e}")
        has_new = False

    print("[2] Embedding CVEs...")
    try:
        analyze_and_embed_new_cves()
    except Exception as e:
        print(f"   Analyzer failed: {e}")

    print("[3] Summarizing with LLM...")
    try:
        generate_summary_with_llm()
    except Exception as e:
        print(f"   Summarizer failed: {e}")

    print("\n[✓] Workflow completed.\n")

if __name__ == "__main__":
    run_workflow()
