"""LangGraph supervisor orchestration for telecom assistant."""

from __future__ import annotations

from typing import Literal, TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from llamaindex_rag.document_rag import query_policy_documents
from llamaindex_rag.sql_semantic_search import query_network_analytics
from utils.config import OPENAI_API_KEY

from orchestration.adk_remote_client import (
    call_billing_resolution,
    call_network_diagnostics,
)
from orchestration.crew_nodes import run_customer_communications_crew
from orchestration.state import AgentState

WorkerName = Literal[
    "PolicyRAG",
    "NetworkAnalytics",
    "NetworkDiagnosticsADK",
    "BillingResolutionADK",
    "CustomerCommsCrew",
    "FINISH",
]


class SupervisorDecision(TypedDict):
    """Structured supervisor output."""

    next: WorkerName


def _append_worker_output(state: AgentState, worker: str, output: str) -> dict:
    block = f"\n[{worker}]\n{output}\n"
    return {
        "agent_context": block,
        "execution_trace": [{"worker": worker, "output": output[:500]}],
    }


def supervisor_node(state: AgentState) -> dict:
    """Choose the next worker based on query and prior execution trace."""
    llm = ChatOpenAI(model="gpt-4.1-mini", api_key=OPENAI_API_KEY, temperature=0)
    structured = llm.with_structured_output(SupervisorDecision)
    already_called = [entry["worker"] for entry in state.get("execution_trace", [])]
    system_prompt = """
You are the supervisor for the Telecom AI Operations Center.
Available workers:
- PolicyRAG: policy, roaming, SLA rules, 5G FAQ, upgrade eligibility
- NetworkAnalytics: outage trends, packet loss stats, top-N analytics
- NetworkDiagnosticsADK: tower drops, tower diagnostics, signal quality by tower ID
- BillingResolutionADK: duplicate charge, credit/dispute, CUST- prefixed account issues
- CustomerCommsCrew: final customer-facing polished response

Routing rules:
1) Never route the same worker twice.
2) Always route CustomerCommsCrew before FINISH.
3) For combined questions requiring analytics/diagnostics + policy, do data/ADK worker first then PolicyRAG.
4) Return exactly one value for 'next' from the worker list or FINISH.
""".strip()
    user_prompt = (
        f"User query: {state.get('user_query', '')}\n"
        f"Already called workers: {already_called}\n"
        f"Current context: {state.get('agent_context', '')[:2000]}"
    )
    decision = structured.invoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )
    next_worker = decision["next"]
    called_set = set(already_called)
    user_query = state.get("user_query", "").lower()

    needs_policy = any(
        keyword in user_query
        for keyword in ["policy", "sla", "roaming", "faq", "upgrade"]
    )
    needs_data = any(
        keyword in user_query
        for keyword in [
            "outage",
            "packet loss",
            "latency",
            "diagnose",
            "tower",
            "charged",
            "credit",
            "cust-",
        ]
    )
    has_comms = "CustomerCommsCrew" in called_set

    final_next = next_worker

    # Enforce combined-query order: data/ADK first, then policy.
    if needs_policy and needs_data and "PolicyRAG" not in called_set:
        if called_set.intersection(
            {"NetworkAnalytics", "NetworkDiagnosticsADK", "BillingResolutionADK"}
        ):
            final_next = "PolicyRAG"
    # Never route the same worker twice.
    elif next_worker in called_set:
        if not has_comms:
            final_next = "CustomerCommsCrew"
        else:
            final_next = "FINISH"
    # Customer comms must run before finishing.
    elif next_worker == "FINISH" and not has_comms:
        final_next = "CustomerCommsCrew"
    # After customer comms, terminate.
    elif has_comms and next_worker != "FINISH":
        final_next = "FINISH"

    return {
        "next": final_next,
        "execution_trace": [{"worker": "Supervisor", "output": f"Analyzed query and routed to {final_next}."}]
    }


def policy_rag_node(state: AgentState) -> dict:
    output = query_policy_documents(state["user_query"])
    return _append_worker_output(state, "PolicyRAG", output)


def network_analytics_node(state: AgentState) -> dict:
    output = query_network_analytics(state["user_query"])
    return _append_worker_output(state, "NetworkAnalytics", output)


def network_diagnostics_adk_node(state: AgentState) -> dict:
    output = call_network_diagnostics(state["user_query"])
    return _append_worker_output(state, "NetworkDiagnosticsADK", output)


def billing_resolution_adk_node(state: AgentState) -> dict:
    output = call_billing_resolution(state["user_query"])
    return _append_worker_output(state, "BillingResolutionADK", output)


def customer_comms_crew_node(state: AgentState) -> dict:
    output = run_customer_communications_crew(
        state["user_query"], state.get("agent_context", "")
    )
    payload = _append_worker_output(state, "CustomerCommsCrew", output)
    payload["final_response"] = output
    return payload


def _route(state: AgentState) -> str:
    next_worker = state.get("next", "FINISH")
    if next_worker == "FINISH":
        return END
    return next_worker


graph_builder = StateGraph(AgentState)
graph_builder.add_node("supervisor", supervisor_node)
graph_builder.add_node("PolicyRAG", policy_rag_node)
graph_builder.add_node("NetworkAnalytics", network_analytics_node)
graph_builder.add_node("NetworkDiagnosticsADK", network_diagnostics_adk_node)
graph_builder.add_node("BillingResolutionADK", billing_resolution_adk_node)
graph_builder.add_node("CustomerCommsCrew", customer_comms_crew_node)

graph_builder.add_edge(START, "supervisor")
graph_builder.add_conditional_edges(
    "supervisor",
    _route,
    {
        "PolicyRAG": "PolicyRAG",
        "NetworkAnalytics": "NetworkAnalytics",
        "NetworkDiagnosticsADK": "NetworkDiagnosticsADK",
        "BillingResolutionADK": "BillingResolutionADK",
        "CustomerCommsCrew": "CustomerCommsCrew",
        END: END,
    },
)
for node in [
    "PolicyRAG",
    "NetworkAnalytics",
    "NetworkDiagnosticsADK",
    "BillingResolutionADK",
    "CustomerCommsCrew",
]:
    graph_builder.add_edge(node, "supervisor")

TELECOM_GRAPH = graph_builder.compile()


def run_telecom_assistant(user_query: str) -> dict:
    """Run full graph and return key output artifacts."""
    from langchain_openai import ChatOpenAI
    from utils.config import OPENAI_API_KEY
    
    llm = ChatOpenAI(model="gpt-4.1-mini", api_key=OPENAI_API_KEY, temperature=0)
    system_prompt = (
        "You are an input filter for a telecom assistant. "
        "Your job is to determine if the user query is strictly related to "
        "telecommunications, networking, mobile plans, outages, or Telecom support. "
        "If it is related, output 'ALLOW'. If it is an off-topic general question "
        "(like 'what is the capital of France' or 'write a poem'), output 'REJECT'."
    )
    res = llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_query}
    ])
    
    if "REJECT" in res.content:
        return {
            "final_response": "I can only answer questions related to Telecom telecom operations, networking, and billing.",
            "execution_trace": [{"worker": "Guardrail", "output": "Query rejected as off-topic."}],
            "agent_context": "Query rejected as off-topic."
        }
        
    initial_state: AgentState = {
        "messages": [],
        "next": "",
        "user_query": user_query,
        "agent_context": "",
        "execution_trace": [],
        "final_response": "",
    }
    result = TELECOM_GRAPH.invoke(initial_state)
    return {
        "final_response": result.get("final_response", ""),
        "execution_trace": result.get("execution_trace", []),
        "agent_context": result.get("agent_context", ""),
    }
