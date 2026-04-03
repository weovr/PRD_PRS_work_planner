"""
ExecutionAgent — tracks ongoing and recently completed work orders.
Flags overdue jobs, calculates actual vs. planned hours, and generates
status summaries (with optional AI-assisted finding summaries via Anthropic API).
"""

import os
from datetime import datetime
from typing import Any, Optional
from tools import db_reader


class ExecutionAgent:
    """Agent responsible for execution tracking and status reporting of active work orders."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.agent_name = "execution"

    def run(self, params: dict) -> dict:
        """
        Main entry point.
        Supports actions:
          - 'status': list all open work orders (default)
          - 'find_by_equipment': find work orders for a specific equipment tag
          - 'find_by_job_id': find a work order matching a job ID or safran activity
          - 'daily_report': generate a daily status summary
        """
        action = params.get("action", "status")

        if action == "status":
            return self._get_open_work_orders(params)
        elif action == "find_by_equipment":
            return self._find_by_equipment(params)
        elif action == "find_by_job_id":
            return self._find_by_job_id(params)
        elif action == "daily_report":
            return self._daily_report(params)
        else:
            return {
                "status": "error",
                "agent": self.agent_name,
                "data": {"message": f"Ukjent handling: {action}"},
            }

    def _get_open_work_orders(self, params: dict) -> dict:
        """Fetch all open work orders and flag any that are overdue."""
        platform_id = params.get("platform_id")
        open_wos = db_reader.get_open_work_orders(self.db_path)

        if platform_id:
            open_wos = [wo for wo in open_wos if wo.get("platform_id") == platform_id]

        today = datetime.today()
        overdue_flags = {}
        for wo in open_wos:
            finish_str = wo.get("finish_date")
            if finish_str:
                try:
                    finish_date = datetime.strptime(finish_str, "%Y-%m-%d")
                    overdue_flags[wo["wo_number"]] = finish_date < today
                except ValueError:
                    overdue_flags[wo["wo_number"]] = False
            else:
                # No finish date set yet — check if start date is in the past
                start_str = wo.get("start_date")
                if start_str:
                    try:
                        start_date = datetime.strptime(start_str, "%Y-%m-%d")
                        # Flag as overdue if start was > 60 days ago with no finish
                        overdue_flags[wo["wo_number"]] = (today - start_date).days > 60
                    except ValueError:
                        overdue_flags[wo["wo_number"]] = False
                else:
                    overdue_flags[wo["wo_number"]] = False

        return {
            "status": "ok",
            "agent": self.agent_name,
            "data": {
                "open_work_orders": open_wos,
                "overdue_flags": overdue_flags,
                "total_open": len(open_wos),
                "total_overdue": sum(1 for v in overdue_flags.values() if v),
            },
        }

    def _find_by_equipment(self, params: dict) -> dict:
        """Find open work orders for a specific equipment tag."""
        tag = params.get("tag", "").upper()
        if not tag:
            return {
                "status": "error",
                "agent": self.agent_name,
                "data": {"message": "Mangler utstyrstagg."},
            }

        all_wos = db_reader.get_all_work_orders(self.db_path)
        matching = [wo for wo in all_wos if wo.get("equipment_tag", "").upper() == tag]
        open_wos = [wo for wo in matching if wo.get("status") not in ("TECO", "CLSD")]

        return {
            "status": "ok",
            "agent": self.agent_name,
            "data": {
                "equipment_tag": tag,
                "matching_work_orders": matching,
                "open_work_orders": open_wos,
            },
        }

    def _find_by_job_id(self, params: dict) -> dict:
        """Find a work order by job_id (matches against safran_activity_id or wo_number)."""
        job_id = params.get("job_id", "")
        safran_id = params.get("safran_activity_id", "")
        search_term = job_id or safran_id

        if not search_term:
            return {
                "status": "error",
                "agent": self.agent_name,
                "data": {"message": "Mangler job_id eller safran_activity_id."},
            }

        all_wos = db_reader.get_all_work_orders(self.db_path)
        search_upper = search_term.upper()
        matching = [
            wo for wo in all_wos
            if (wo.get("wo_number", "") == search_term
                or wo.get("safran_activity_id", "").upper() == search_upper)
        ]

        return {
            "status": "ok" if matching else "not_found",
            "agent": self.agent_name,
            "data": {
                "search_term": search_term,
                "matching_work_orders": matching,
            },
        }

    def _daily_report(self, params: dict) -> dict:
        """Generate a daily status summary for all open work orders."""
        open_result = self._get_open_work_orders(params)
        open_wos = open_result["data"]["open_work_orders"]
        overdue_flags = open_result["data"]["overdue_flags"]

        today = datetime.today()
        report_lines = []
        report_lines.append(f"DAGLIG STATUSRAPPORT — {today.strftime('%Y-%m-%d')}")
        report_lines.append(f"Åpne arbeidsordre: {len(open_wos)}")
        report_lines.append(f"Forsinkede: {sum(1 for v in overdue_flags.values() if v)}")
        report_lines.append("")

        for wo in open_wos:
            overdue = overdue_flags.get(wo.get("wo_number"), False)
            status_label = "FORSINKET" if overdue else wo.get("status", "N/A")
            report_lines.append(
                f"  AO {wo.get('wo_number')} [{status_label}] | "
                f"{wo.get('equipment_tag')} | "
                f"{wo.get('platform_id')} | "
                f"Start: {wo.get('start_date', 'N/A')}"
            )

        summary_text = "\n".join(report_lines)

        return {
            "status": "ok",
            "agent": self.agent_name,
            "data": {
                "report_date": today.strftime("%Y-%m-%d"),
                "open_work_orders": open_wos,
                "overdue_flags": overdue_flags,
                "report_text": summary_text,
            },
        }

    def summarize_findings(self, wo: dict) -> str:
        """
        Generate a 2-3 sentence AI summary of work order findings (in Norwegian).
        Falls back to a template if the API call fails.
        """
        findings = wo.get("findings", "")
        completion_notes = wo.get("completion_notes", "")
        if not findings and not completion_notes:
            return "Ingen funn registrert på denne arbeidsordren."

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key:
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=api_key)
                content = (
                    f"Arbeidsordre: {wo.get('wo_number')}\n"
                    f"Beskrivelse: {wo.get('description', '')}\n"
                    f"Funn: {findings}\n"
                    f"Fullføringsnotater: {completion_notes}"
                )
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=200,
                    system=(
                        "You are an offshore maintenance engineer at Equinor. "
                        "Summarize the work order findings and completion notes in 2-3 sentences. "
                        "Write in Norwegian (bokmål). Be factual and technical."
                    ),
                    messages=[{"role": "user", "content": content}],
                )
                return response.content[0].text
            except Exception:
                pass  # Fall through to template

        # Template fallback
        summary_parts = []
        if findings:
            summary_parts.append(f"Funn: {findings}")
        if completion_notes:
            summary_parts.append(f"Fullføring: {completion_notes}")
        return " ".join(summary_parts)
