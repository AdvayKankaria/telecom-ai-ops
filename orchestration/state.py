"""Shared state definitions for LangGraph orchestration."""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langgraph.graph import MessagesState


class TraceEntry(TypedDict):
    """Execution trace item shape."""

    worker: str
    output: str


class AgentState(MessagesState):
    """State propagated between supervisor and worker nodes."""

    next: str
    user_query: str
    agent_context: Annotated[str, operator.add]
    execution_trace: Annotated[list[TraceEntry], operator.add]
    final_response: str
