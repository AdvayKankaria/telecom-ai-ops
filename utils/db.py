"""SQLite database helper utilities."""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager

from utils.config import DB_PATH


@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """Yield a SQLite connection configured for this application."""
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(DB_PATH)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        yield connection
    finally:
        if connection is not None:
            connection.close()


def get_pending_credits() -> list[dict]:
    """Fetch all credits waiting for manual manager approval."""
    query = "SELECT credit_id, customer_id, amount, reason FROM billing_credits WHERE status = 'PENDING_APPROVAL'"
    with get_db_connection() as conn:
        rows = conn.execute(query).fetchall()
        return [dict(row) for row in rows]


def approve_credit(credit_id: int) -> None:
    """Safely approve a pending credit and deduct from the user's balance.
    The WHERE clause ensures we never double-approve if clicked twice."""
    get_credit_query = "SELECT customer_id, amount FROM billing_credits WHERE credit_id = ? AND status = 'PENDING_APPROVAL'"
    update_credit_query = "UPDATE billing_credits SET status = 'APPLIED' WHERE credit_id = ?"
    update_account_query = "UPDATE billing_accounts SET current_balance = current_balance - ? WHERE customer_id = ?"
    update_charges_query = "UPDATE billing_charges SET is_duplicate_flag = 0 WHERE customer_id = ? AND is_duplicate_flag = 1"
    
    with get_db_connection() as conn:
        credit = conn.execute(get_credit_query, (credit_id,)).fetchone()
        if credit:
            conn.execute(update_credit_query, (credit_id,))
            conn.execute(update_account_query, (credit['amount'], credit['customer_id']))
            conn.execute(update_charges_query, (credit['customer_id'],))
            conn.commit()
