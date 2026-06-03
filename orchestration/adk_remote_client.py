"""Helpers for calling remote ADK A2A services safely."""

from __future__ import annotations

import logging

from google.adk.agents import Agent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from utils.config import BILLING_RESOLUTION_URL, NETWORK_DIAGNOSTICS_URL

LOGGER = logging.getLogger(__name__)


async def _call_remote_a2a(message: str, base_url: str, service_name: str) -> str:
    """Call one ADK A2A service and return final text response."""
    runner = None
    try:
        remote_agent = RemoteA2aAgent(
            name=f"{service_name.lower()}_remote",
            agent_card=f"{base_url.rstrip('/')}/.well-known/agent-card.json",
        )
        proxy_agent = Agent(
            name=f"{service_name.lower()}_proxy",
            model="gemini-2.5-flash",
            instruction="Forward the user request and return the remote response exactly.",
            sub_agents=[remote_agent],
        )
        runner = Runner(
            app_name="prodapt_orchestrator",
            agent=proxy_agent,
            session_service=InMemorySessionService(),
        )
        session = await runner.session_service.create_session(
            app_name="prodapt_orchestrator",
            user_id="langgraph",
            state={},
        )
        content = types.Content(role="user", parts=[types.Part.from_text(text=message)])
        final_text = ""
        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=content,
        ):
            if event.content and event.content.parts:
                texts = [
                    part.text
                    for part in event.content.parts
                    if getattr(part, "text", None)
                ]
                if texts:
                    final_text = "\n".join(texts)
        return final_text or f"{service_name} returned no text output."
    except ConnectionRefusedError:
        if service_name == "NetworkDiagnosticsADK":
            return (
                "NetworkDiagnosticsADK service is not running at "
                "http://127.0.0.1:8001. Start the ADK service and retry."
            )
        return (
            f"{service_name} service is not running at {base_url}. "
            "Start the ADK service and retry."
        )
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Remote ADK call failed for %s", service_name)
        return f"{service_name} service is not available at {base_url}. Details: {exc}"
    finally:
        if runner is not None:
            await runner.close()


def call_network_diagnostics(message: str) -> str:
    """Call Network Diagnostics ADK service."""
    import asyncio

    return asyncio.run(
        _call_remote_a2a(message, NETWORK_DIAGNOSTICS_URL, "NetworkDiagnosticsADK")
    )


def call_billing_resolution(message: str) -> str:
    """Call Billing Resolution ADK service."""
    import asyncio

    return asyncio.run(
        _call_remote_a2a(message, BILLING_RESOLUTION_URL, "BillingResolutionADK")
    )
