"""Streamlit UI for Prodapt AI Operations Center."""

from __future__ import annotations

from pathlib import Path
import os

os.environ["HF_HOME"] = ".hf_cache"
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"

import httpx
import streamlit as st
from orchestration.graph import run_telecom_assistant
from utils.config import DB_PATH, INDEX_PATH
from utils.db import get_pending_credits, approve_credit


def _service_status(name: str, base_url: str) -> tuple[bool, str]:
    endpoint = f"{base_url.rstrip('/')}/.well-known/agent-card.json"
    try:
        response = httpx.get(endpoint, timeout=1.0)
        response.raise_for_status()
        return True, f"✅ {name} — Running"
    except Exception:  # noqa: BLE001
        return False, f"❌ {name} — Not running"


def _render_sidebar() -> None:
    st.sidebar.header("System Status")

    if Path(DB_PATH).exists():
        st.sidebar.success("✅ Database Ready")
    else:
        st.sidebar.error("❌ Run python init_db.py")

    if Path(INDEX_PATH).exists():
        st.sidebar.success("✅ Vector Index Built")
    else:
        st.sidebar.warning("⚠️ Builds on first RAG query")

    net_up, net_msg = _service_status(
        "Network Diagnostics (8001)", "http://127.0.0.1:8001"
    )
    bill_up, bill_msg = _service_status(
        "Billing Resolution (8002)", "http://127.0.0.1:8002"
    )
    st.sidebar.write(net_msg)
    st.sidebar.write(bill_msg)

    if not net_up or not bill_up:
        st.sidebar.warning(
            "One or more ADK services are down.\n"
            "- `python adk_services/network_diagnostics/agent.py`\n"
            "- `python adk_services/billing_resolution/agent.py`"
        )

    framework_rows = [
        {"Capability": "Policy / FAQ", "Framework": "LlamaIndex RAG"},
        {"Capability": "Network Analytics", "Framework": "LlamaIndex Semantic SQL"},
        {"Capability": "Network Diagnostics", "Framework": "Google ADK A2A :8001"},
        {"Capability": "Billing Resolution", "Framework": "Google ADK A2A :8002"},
        {"Capability": "Orchestration", "Framework": "LangGraph Supervisor"},
        {"Capability": "Customer Comms", "Framework": "CrewAI Sequential Crew"},
    ]
    st.sidebar.dataframe(framework_rows, width="stretch", hide_index=True)

    st.sidebar.divider()
    st.sidebar.header("💡 Try these Scenarios")
    scenarios = [
        "What is Prodapt's roaming policy for Western Europe?",
        "Which region had the most CRITICAL network outages recently?",
        "My 5G keeps dropping in Austin near tower TX-512. Please diagnose.",
        "Customer CUST-10002 was charged twice for Unlimited Plus. Investigate and apply credit.",
        "We had a 6-hour outage in the Midwest. Am I eligible for an SLA credit and what does policy say?",
        "Write a poem about butterflies"
    ]
    
    query_to_run = None
    for i, s in enumerate(scenarios):
        if st.sidebar.button(s, key=f"scenario_{i}", use_container_width=True):
            query_to_run = s
            
    return query_to_run


def main() -> None:
    """Render Streamlit page and execute telecom assistant graph."""
    st.set_page_config(
        page_title="Prodapt AI Operations Center", page_icon="🛰️", layout="wide"
    )

    query_to_run = _render_sidebar()
    
    st.title("🛰️ Prodapt AI Operations Center")
    st.caption("LlamaIndex + Google ADK + LangGraph + CrewAI")

    query = st.text_area(
        "Customer inquiry",
        value=query_to_run if query_to_run else "",
        placeholder=(
            "Examples:\n"
            "- What is Prodapt's roaming policy for Western Europe?\n"
            "- Customer CUST-10002 was charged twice. Investigate and apply credit."
        ),
        height=160,
    )

    if st.button("🚀 Process Inquiry", type="primary", use_container_width=True) or query_to_run:
        actual_query = query_to_run if query_to_run else query
        if not actual_query.strip():
            st.warning("Please enter an inquiry before submitting.")
            return
        try:
            with st.spinner("Running multi-agent workflow..."):
                result = run_telecom_assistant(actual_query.strip())

            st.success(result.get("final_response", "No response generated."))

            trace = result.get("execution_trace", [])
            with st.expander("🔍 Agent Execution Trace", expanded=True):
                if not trace:
                    st.info("No trace available.")
                for idx, step in enumerate(trace, start=1):
                    st.markdown(f"**Step {idx} - {step.get('worker', 'Unknown')}**")
                    st.write(str(step.get("output", ""))[:500])
                    st.divider()

            with st.expander("🔧 Raw Context (debug)"):
                st.code(result.get("agent_context", ""))
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))

    st.divider()
    st.subheader("💳 Pending Credit Approvals")
    pending_credits = get_pending_credits()
    if not pending_credits:
        st.info("No credits are currently pending approval.")
    else:
        for credit in pending_credits:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**Customer:** `{credit['customer_id']}` | **Amount:** `${credit['amount']:.2f}`")
                st.caption(f"Reason: {credit['reason']}")
            with col2:
                if st.button("Approve Credit", key=f"approve_{credit['credit_id']}", use_container_width=True):
                    approve_credit(credit['credit_id'])
                    st.rerun()


if __name__ == "__main__":
    main()
