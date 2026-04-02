"""
EquipmentAgent — looks up equipment specs, maintenance history, running hours,
and associated spare parts from the JSON database.
"""

from typing import Any
from tools import db_reader


class EquipmentAgent:
    """Agent responsible for equipment data lookups and status reporting."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.agent_name = "equipment"

    def run(self, params: dict) -> dict:
        """
        Main entry point. Expects params to contain at least 'tag'.
        Returns equipment specs, maintenance history, running hours status, and spare parts.
        """
        tag = params.get("tag", "").upper()
        if not tag:
            return {
                "status": "error",
                "agent": self.agent_name,
                "data": {"message": "Mangler utstyrstagg i forespørselen."},
            }

        equipment = db_reader.get_equipment(self.db_path, tag)
        if not equipment:
            return {
                "status": "not_found",
                "agent": self.agent_name,
                "data": {"message": f"Utstyr ikke funnet: {tag}"},
            }

        history = db_reader.get_work_orders_for_equipment(self.db_path, tag, limit=5)
        parts = db_reader.get_spare_parts_for_equipment(self.db_path, tag)
        platform = db_reader.get_platform(self.db_path, equipment.get("platform_id", ""))

        # Calculate overhaul status
        running_hours = equipment.get("running_hours", 0) or 0
        oh_interval = equipment.get("oh_interval_hours", 0) or 0
        hours_remaining = max(0, oh_interval - running_hours)
        overhaul_overdue = running_hours > oh_interval

        return {
            "status": "ok",
            "agent": self.agent_name,
            "data": {
                "equipment": equipment,
                "platform": platform,
                "maintenance_history": history,
                "spare_parts": parts,
                "overhaul_status": {
                    "running_hours": running_hours,
                    "oh_interval_hours": oh_interval,
                    "hours_remaining": hours_remaining,
                    "overhaul_overdue": overhaul_overdue,
                    "next_planned_overhaul": equipment.get("next_planned_overhaul"),
                },
            },
        }

    def get_equipment_for_planning(self, tag: str) -> dict:
        """Convenience method for the orchestrator to fetch equipment data for planning."""
        return self.run({"tag": tag})
