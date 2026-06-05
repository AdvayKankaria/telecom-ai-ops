"""Google ADK service for network diagnostics."""

from __future__ import annotations

import json
from typing import Any

import uvicorn
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.agents import Agent
from utils.db import get_db_connection


def _json(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, default=str)


async def check_tower_status(tower_id: str) -> str:
    """Return status and latest telemetry for a specific tower."""
    query = """
        SELECT
            nt.tower_id,
            nt.region,
            nt.city,
            nt.technology,
            nt.status AS tower_status,
            tp.signal_strength_dbm,
            tp.avg_latency_ms,
            tp.packet_loss_pct,
            tp.throughput_mbps,
            oi.incident_id,
            oi.severity AS incident_severity,
            oi.status AS incident_status,
            oi.description AS incident_description
        FROM network_towers nt
        LEFT JOIN tower_performance tp
            ON tp.tower_id = nt.tower_id
            AND tp.recorded_at = (
                SELECT MAX(recorded_at)
                FROM tower_performance
                WHERE tower_id = nt.tower_id
            )
        LEFT JOIN open_incidents oi
            ON oi.tower_id = nt.tower_id
            AND oi.status IN ('OPEN', 'IN_PROGRESS')
        WHERE nt.tower_id = ?
    """
    try:
        with get_db_connection() as connection:
            row = connection.execute(query, (tower_id,)).fetchone()
        if row is None:
            return _json({"error": f"Tower '{tower_id}' not found."})
        return _json(dict(row))
    except Exception as exc:  # noqa: BLE001
        return _json({"error": f"Failed tower status lookup for {tower_id}: {exc}"})


async def run_connectivity_diagnostics(tower_id: str, symptom: str) -> str:
    """Analyze signal and packet loss to suggest likely fixes."""
    query = """
        SELECT avg_latency_ms, packet_loss_pct, throughput_mbps, signal_strength_dbm
        FROM tower_performance
        WHERE tower_id = ?
        ORDER BY recorded_at DESC
        LIMIT 1
    """
    try:
        with get_db_connection() as connection:
            metrics = connection.execute(query, (tower_id,)).fetchone()
        if metrics is None:
            return _json(
                {"error": f"No performance telemetry found for tower '{tower_id}'."}
            )

        packet_loss = (
            metrics["packet_loss_pct"]
            if metrics["packet_loss_pct"] is not None
            else 0.0
        )
        signal = (
            metrics["signal_strength_dbm"]
            if metrics["signal_strength_dbm"] is not None
            else -120.0
        )
        latency = (
            metrics["avg_latency_ms"] if metrics["avg_latency_ms"] is not None else None
        )

        diagnosis = []
        recommendations = []
        if packet_loss >= 5:
            diagnosis.append(
                "Severe packet loss indicates backhaul or radio instability."
            )
            recommendations.append(
                "Escalate to field operations and perform immediate radio path audit."
            )
        elif packet_loss >= 1:
            diagnosis.append("Moderate packet loss indicates degraded quality.")
            recommendations.append(
                "Inspect interference and validate scheduler/load balancing settings."
            )
        else:
            diagnosis.append("Packet loss is within normal limits.")

        if signal <= -95:
            diagnosis.append("Signal strength is poor.")
            recommendations.append(
                "Check antenna alignment, feeder integrity, and local obstructions."
            )
        elif signal <= -85:
            diagnosis.append("Signal strength is borderline.")
            recommendations.append(
                "Monitor RSRP/RSRQ trends and evaluate optimization."
            )
        else:
            diagnosis.append("Signal strength is healthy.")

        if latency is not None and latency > 80:
            recommendations.append(
                "Investigate transport congestion and QoS prioritization."
            )

        return _json(
            {
                "tower_id": tower_id,
                "symptom": symptom,
                "metrics": dict(metrics),
                "diagnosis": diagnosis,
                "recommended_actions": recommendations,
            }
        )
    except Exception as exc:  # noqa: BLE001
        return _json(
            {"error": f"Failed connectivity diagnostics for {tower_id}: {exc}"}
        )


async def get_regional_network_summary(region: str) -> str:
    """Summarize tower status, open incidents, and worst tower in a region."""
    status_query = """
        SELECT status, COUNT(*) AS count
        FROM network_towers
        WHERE region = ?
        GROUP BY status
    """
    incident_query = """
        SELECT COUNT(*) AS open_incidents
        FROM open_incidents oi
        JOIN network_towers nt ON nt.tower_id = oi.tower_id
        WHERE nt.region = ? AND oi.status IN ('OPEN', 'IN_PROGRESS')
    """
    worst_query = """
        SELECT nt.tower_id, nt.city, tp.packet_loss_pct
        FROM network_towers nt
        JOIN tower_performance tp ON tp.tower_id = nt.tower_id
        WHERE nt.region = ?
        ORDER BY tp.packet_loss_pct DESC
        LIMIT 1
    """
    try:
        with get_db_connection() as connection:
            status_rows = connection.execute(status_query, (region,)).fetchall()
            incident_row = connection.execute(incident_query, (region,)).fetchone()
            worst_row = connection.execute(worst_query, (region,)).fetchone()

        return _json(
            {
                "region": region,
                "tower_status_counts": [dict(row) for row in status_rows],
                "open_incident_count": incident_row["open_incidents"]
                if incident_row
                else 0,
                "worst_packet_loss_tower": dict(worst_row) if worst_row else None,
            }
        )
    except Exception as exc:  # noqa: BLE001
        return _json({"error": f"Failed regional summary for {region}: {exc}"})


root_agent = Agent(
    name="network_diagnostics_adk",
    model="gemini-2.5-flash",
    instruction=(
        "You are the Telecom NOC AI. Diagnose tower connectivity issues and summarise "
        "regional network health. All data comes from SQL - never invent values. "
        "Return concise technical reports."
    ),
    tools=[
        check_tower_status,
        run_connectivity_diagnostics,
        get_regional_network_summary,
    ],
)


if __name__ == "__main__":
    app = to_a2a(root_agent, host="127.0.0.1", port=8001)
    uvicorn.run(app, host="127.0.0.1", port=8001)
