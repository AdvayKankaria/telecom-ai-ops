"""LlamaIndex semantic SQL analytics query engine."""

from __future__ import annotations

from llama_index.core import SQLDatabase, VectorStoreIndex
from llama_index.core.indices.struct_store import SQLTableRetrieverQueryEngine
from llama_index.core.objects import ObjectIndex, SQLTableNodeMapping, SQLTableSchema
from llama_index.llms.openai import OpenAI
from utils.config import DB_PATH, OPENAI_API_KEY


def _build_query_engine() -> SQLTableRetrieverQueryEngine:
    """Build semantic table retriever query engine."""
    try:
        sql_database = SQLDatabase.from_uri(f"sqlite:///{DB_PATH}")
        table_node_mapping = SQLTableNodeMapping(sql_database)
        table_schemas = [
            SQLTableSchema(
                table_name="network_towers",
                context_str=(
                    "Master inventory of telecom towers with tower IDs, region, city, "
                    "technology type, operational status, and subscriber capacity. "
                    "Use for regional health snapshots and tower state lookups."
                ),
            ),
            SQLTableSchema(
                table_name="network_outages",
                context_str=(
                    "Records of historical network outages including severity "
                    "(CRITICAL/HIGH/MEDIUM/LOW), affected customer counts, region, "
                    "start/end times, and root cause. Use for outage trend analytics."
                ),
            ),
            SQLTableSchema(
                table_name="tower_performance",
                context_str=(
                    "Time-series tower performance metrics including average latency, "
                    "packet loss percentage, throughput, and signal strength. "
                    "Use for identifying degraded towers and ranking performance."
                ),
            ),
            SQLTableSchema(
                table_name="open_incidents",
                context_str=(
                    "Current active and in-progress incidents linked to towers with "
                    "severity, status, ETA, and descriptions. Use for live incident "
                    "counts and operational response visibility."
                ),
            ),
            SQLTableSchema(
                table_name="customer_subscriptions",
                context_str=(
                    "Customer subscription profiles including account type, plan, data "
                    "limits, monthly fee, contract end date, and region. Use for "
                    "subscription mix and regional customer segmentation analytics."
                ),
            ),
            SQLTableSchema(
                table_name="billing_accounts",
                context_str=(
                    "Current billing balances and billing cycle day per customer. "
                    "Use for account-level balance checks and billing exposure analytics."
                ),
            ),
            SQLTableSchema(
                table_name="billing_charges",
                context_str=(
                    "Individual customer charge line items with description, amount, "
                    "charge date, billing period, and duplicate flag markers. "
                    "Use for charge trend analysis and duplicate charge investigation."
                ),
            ),
            SQLTableSchema(
                table_name="billing_credits",
                context_str=(
                    "Applied or pending billing credits with amount, reason, status, "
                    "reference number, and timestamps. Use for credit policy tracking "
                    "and reimbursement analytics."
                ),
            ),
            SQLTableSchema(
                table_name="billing_disputes",
                context_str=(
                    "Customer billing dispute cases tied to charges, with reason and "
                    "case lifecycle states (OPEN/RESOLVED/REJECTED). Use for dispute "
                    "volume and resolution pipeline analysis."
                ),
            ),
        ]

        obj_index = ObjectIndex.from_objects(
            table_schemas,
            table_node_mapping,
            VectorStoreIndex,
        )
        retriever = obj_index.as_retriever(similarity_top_k=2)
        return SQLTableRetrieverQueryEngine(
            sql_database=sql_database,
            table_retriever=retriever,
            llm=OpenAI(model="gpt-4.1-mini", api_key=OPENAI_API_KEY),
        )
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"Failed to build network analytics query engine: {exc}"
        ) from exc


def query_network_analytics(question: str) -> str:
    """Run natural-language analytics query against telecom SQL database."""
    try:
        query_engine = _build_query_engine()
        response = query_engine.query(question)
        return str(response)
    except RuntimeError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Network analytics query failed: {exc}") from exc
