"""CrewAI nodes for customer communications polishing."""

from __future__ import annotations

from crewai import Agent, Crew, Process, Task
from langchain_openai import ChatOpenAI
from utils.config import OPENAI_API_KEY


def run_customer_communications_crew(user_query: str, agent_context: str) -> str:
    """Run a sequential CrewAI workflow to craft customer-ready output."""
    llm = ChatOpenAI(model="gpt-4.1-mini", api_key=OPENAI_API_KEY, temperature=0.2)

    comms_agent = Agent(
        role="Communications Specialist",
        goal="Write clear, empathetic, solution-oriented customer updates.",
        backstory="Expert in telecom support communication and expectation management.",
        llm=llm,
        verbose=False,
    )
    reviewer_agent = Agent(
        role="Quality Reviewer",
        goal="Ensure response is accurate, policy-compliant, and customer-safe.",
        backstory="Quality lead who enforces policy and factual precision.",
        llm=llm,
        verbose=False,
    )

    draft_task = Task(
        description=(
            "Using the original inquiry and specialist context, draft a professional "
            "customer response. Avoid internal jargon, SQL terms, or system labels.\n\n"
            f"User query:\n{user_query}\n\n"
            f"Specialist context:\n{agent_context}"
        ),
        expected_output="A polished customer-facing response draft in 2-4 paragraphs.",
        agent=comms_agent,
    )
    review_task = Task(
        description=(
            "Review and refine the draft for factual correctness, tone, and policy "
            "compliance (including the $50 auto-credit rule). Return only the final "
            "customer-facing response text."
        ),
        expected_output="Final customer response only.",
        agent=reviewer_agent,
        context=[draft_task],
    )

    crew = Crew(
        agents=[comms_agent, reviewer_agent],
        tasks=[draft_task, review_task],
        process=Process.sequential,
        verbose=False,
    )
    result = crew.kickoff()
    return str(result)
