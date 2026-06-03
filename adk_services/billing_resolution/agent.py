"""Google ADK service for billing resolution."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import uvicorn
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.agents import Agent
from utils.config import BILLING_AUTO_APPROVE_LIMIT
from utils.db import get_db_connection


def _json(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, default=str)


async def lookup_billing_account(customer_id: str) -> str:
    """Fetch billing account details and recent charges for a customer."""
    account_query = """
        SELECT customer_id, current_balance, billing_cycle_day
        FROM billing_accounts
        WHERE customer_id = ?
    """
    charges_query = """
        SELECT charge_id, description, amount, charge_date, billing_period, is_duplicate_flag
        FROM billing_charges
        WHERE customer_id = ?
        ORDER BY charge_date DESC, charge_id DESC
        LIMIT 10
    """
    try:
        with get_db_connection() as connection:
            account_row = connection.execute(account_query, (customer_id,)).fetchone()
            charge_rows = connection.execute(charges_query, (customer_id,)).fetchall()

        if account_row is None:
            return _json(
                {"error": f"Customer '{customer_id}' not found in billing_accounts."}
            )
        return _json(
            {
                "account": dict(account_row),
                "recent_charges": [dict(row) for row in charge_rows],
            }
        )
    except Exception as exc:  # noqa: BLE001
        return _json(
            {"error": f"Failed to lookup billing account for {customer_id}: {exc}"}
        )


async def check_duplicate_charges(customer_id: str) -> str:
    """Return duplicate charge rows flagged for a customer."""
    query = """
        SELECT charge_id, description, amount, billing_period
        FROM billing_charges
        WHERE customer_id = ? AND is_duplicate_flag = 1
        ORDER BY charge_id DESC
    """
    try:
        with get_db_connection() as connection:
            rows = connection.execute(query, (customer_id,)).fetchall()
        return _json(
            {
                "customer_id": customer_id,
                "duplicate_charges": [dict(row) for row in rows],
            }
        )
    except Exception as exc:  # noqa: BLE001
        return _json(
            {"error": f"Failed duplicate charge check for {customer_id}: {exc}"}
        )


async def apply_billing_credit(customer_id: str, amount: float, reason: str) -> str:
    """Apply or pend a billing credit according to policy threshold."""
    if amount <= 0:
        return _json({"error": "Credit amount must be greater than zero."})

    account_query = "SELECT current_balance FROM billing_accounts WHERE customer_id = ?"
    insert_query = """
        INSERT INTO billing_credits (customer_id, amount, reason, status, reference_number, applied_at)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
    """
    update_query = """
        UPDATE billing_accounts
        SET current_balance = current_balance - ?
        WHERE customer_id = ?
    """
    try:
        with get_db_connection() as connection:
            customer_row = connection.execute(account_query, (customer_id,)).fetchone()
            if customer_row is None:
                return _json({"error": f"Customer '{customer_id}' does not exist."})

            status = (
                "APPLIED"
                if amount <= BILLING_AUTO_APPROVE_LIMIT
                else "PENDING_APPROVAL"
            )
            reference = f"{customer_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

            connection.execute(
                insert_query, (customer_id, amount, reason, status, reference)
            )
            if status == "APPLIED":
                connection.execute(update_query, (amount, customer_id))
                connection.execute(
                    "UPDATE billing_charges SET is_duplicate_flag = 0 WHERE customer_id = ? AND is_duplicate_flag = 1",
                    (customer_id,)
                )
            connection.commit()

            return _json(
                {
                    "customer_id": customer_id,
                    "amount": amount,
                    "reason": reason,
                    "status": status,
                    "reference_number": reference,
                }
            )
    except Exception as exc:  # noqa: BLE001
        return _json(
            {"error": f"Failed to apply billing credit for {customer_id}: {exc}"}
        )


root_agent = Agent(
    name="billing_resolution_adk",
    model="gemini-2.5-flash",
    instruction=(
        "You are the Prodapt Billing Resolution AI. Investigate disputes, detect duplicate "
        "charges, and apply credits per billing_disputes_policy. Credits <= $50 are "
        "auto-approved; above $50 go to PENDING_APPROVAL. All reads/writes use SQL."
    ),
    tools=[lookup_billing_account, check_duplicate_charges, apply_billing_credit],
)


if __name__ == "__main__":
    app = to_a2a(root_agent, host="127.0.0.1", port=8002)
    uvicorn.run(app, host="127.0.0.1", port=8002)
