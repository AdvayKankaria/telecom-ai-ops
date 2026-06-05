import sys
import os
from pathlib import Path

os.environ["HF_HOME"] = ".hf_cache"
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent))

from orchestration.graph import run_telecom_assistant

scenarios = [
    {
        "name": "Scenario 1 — Policy / FAQ",
        "query": "What is Telecom's roaming policy for Western Europe?"
    },
    {
        "name": "Scenario 2 — Network Analytics",
        "query": "Which region had the most CRITICAL network outages recently?"
    },
    {
        "name": "Scenario 3 — Network Diagnostics",
        "query": "My 5G keeps dropping in Austin near tower TX-512. Please diagnose."
    },
    {
        "name": "Scenario 4 — Billing Dispute",
        "query": "Customer CUST-10002 was charged twice for Unlimited Plus. Investigate and apply credit."
    },
    {
        "name": "Scenario 5 — Combined Multi-Worker Flow",
        "query": "We had a 6-hour outage in the Midwest. Am I eligible for an SLA credit and what does policy say?"
    }
]

print("=== STARTING CAPSTONE SCENARIO VERIFICATION ===\n")

for i, s in enumerate(scenarios, 1):
    print(f"--- Running {s['name']} ---")
    print(f"Query: {s['query']}")
    try:
        result = run_telecom_assistant(s["query"])
        trace = result.get("execution_trace", [])
        print("Routing Path: ", " -> ".join([t["worker"] for t in trace]))
        print("Final Response Snippet: ", result.get("final_response", "")[:200].replace('\n', ' ') + "...\n")
    except Exception as e:
        print(f"ERROR: {e}\n")

print("=== DONE ===")
