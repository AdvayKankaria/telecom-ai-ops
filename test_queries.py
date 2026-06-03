from orchestration.graph import run_telecom_assistant

queries = [
    "Which region had the most CRITICAL network outages recently?",
    "My 5G keeps dropping in Austin near tower TX-512. Please diagnose.",
    "Customer CUST-10002 was charged twice for Unlimited Plus. Investigate and apply credit.",
    "Write a poem about butterflies" # test guardrail
]

for q in queries:
    print(f"\n--- Testing: {q} ---")
    try:
        res = run_telecom_assistant(q)
        print(f"Final Response: {res['final_response']}")
    except Exception as e:
        print(f"Error: {e}")
