"""
PlanningAgent — creates complete job session plans based on equipment data,
job templates, vendor mobilization time, spare parts availability, and crew.
All logic is deterministic: same inputs always produce same outputs.
"""

from datetime import datetime, timedelta
from typing import Any, Optional
from tools import db_reader


class PlanningAgent:
    """Agent responsible for creating structured job plans from templates and database data."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.agent_name = "planning"

    def run(self, params: dict) -> dict:
        """
        Main entry point. Expects:
          - tag: equipment tag
          - job_type: template ID (e.g. 'bundle_change_centrifugal_compressor')
          - proposed_start: ISO date string (e.g. '2026-09-01')
          - equipment_data: pre-fetched equipment dict (optional, will fetch if missing)
        """
        tag = params.get("tag", "").upper()
        job_type = params.get("job_type", "")
        proposed_start_str = params.get("proposed_start", "")
        equipment_data = params.get("equipment_data")

        if not tag or not job_type:
            return {
                "status": "error",
                "agent": self.agent_name,
                "data": {"message": "Mangler 'tag' eller 'job_type' i forespørselen."},
            }

        # Fetch equipment if not passed in
        if not equipment_data:
            equipment = db_reader.get_equipment(self.db_path, tag)
            if not equipment:
                return {
                    "status": "not_found",
                    "agent": self.agent_name,
                    "data": {"message": f"Utstyr ikke funnet: {tag}"},
                }
        else:
            equipment = equipment_data

        # Fetch template
        template = db_reader.get_job_template(self.db_path, job_type)
        if not template:
            return {
                "status": "not_found",
                "agent": self.agent_name,
                "data": {"message": f"Jobbmal ikke funnet: {job_type}"},
            }

        # Fetch platform
        platform = db_reader.get_platform(self.db_path, equipment.get("platform_id", ""))
        platform_name = platform.get("name", equipment.get("platform_id", "N/A")) if platform else "N/A"

        # Parse proposed start date
        try:
            if proposed_start_str:
                proposed_start = datetime.strptime(proposed_start_str, "%Y-%m-%d")
            else:
                # Default: use next_planned_overhaul or today + 90 days
                npo = equipment.get("next_planned_overhaul")
                if npo:
                    proposed_start = datetime.strptime(npo, "%Y-%m-%d")
                else:
                    proposed_start = datetime.today() + timedelta(days=90)
        except ValueError:
            proposed_start = datetime.today() + timedelta(days=90)

        pob_days = template.get("estimated_pob_days", 14)
        proposed_finish = proposed_start + timedelta(days=pob_days)

        # Vendor mobilization deadline
        vendor_id = self._find_vendor_id(equipment)
        vendor = db_reader.get_vendor(self.db_path, vendor_id) if vendor_id else None
        mob_time = vendor.get("mob_time_days", 14) if vendor else 14
        mob_deadline = proposed_start - timedelta(days=mob_time)

        vendor_name = vendor.get("name", "N/A") if vendor else "N/A"

        # Spare parts status
        required_parts = template.get("required_spare_parts", [])
        parts_status_detail = self._check_parts_status(required_parts)
        parts_status_text = self._summarize_parts_status(parts_status_detail)

        # Generate job ID
        year = proposed_start.year
        seq = self._get_next_sequence(tag, year)
        job_id = f"JOB-{year}-{tag}-{seq:03d}"

        # Safran activity reference
        safran_activity = f"ACT-{year}-{tag.replace('-', '')}-OH"

        # PTW type summary
        ptw_requirements = template.get("ptw_requirements", [])
        ptw_type = " + ".join(ptw_requirements) if ptw_requirements else "Standard PTW"

        plan = {
            "job_id": job_id,
            "title": f"{template.get('name', job_type)}, {platform_name}",
            "equipment_tag": tag,
            "platform": platform_name,
            "platform_id": equipment.get("platform_id", "N/A"),
            "job_type": job_type,
            "proposed_start": proposed_start.strftime("%Y-%m-%d"),
            "proposed_finish": proposed_finish.strftime("%Y-%m-%d"),
            "pob_days": pob_days,
            "crew_required": template.get("crew_required", {}),
            "vendor": vendor_name,
            "vendor_id": vendor_id,
            "vendor_mob_deadline": mob_deadline.strftime("%Y-%m-%d"),
            "critical_parts": required_parts,
            "parts_status": parts_status_text,
            "parts_status_detail": parts_status_detail,
            "ptw_type": ptw_type,
            "safran_activity": safran_activity,
            "sap_wo_type": template.get("sap_wo_type", "PM02"),
            "estimated_cost_nok": template.get("estimated_cost_nok", 0),
            "risk_level": template.get("risk_level", "Middels"),
            "activities": template.get("activities", []),
        }

        return {
            "status": "ok",
            "agent": self.agent_name,
            "data": {"plan": plan},
        }

    def recalculate_timeline(self, params: dict) -> dict:
        """
        Recalculate job timeline after a delay.
        Expects: original_plan, delay_days
        """
        original_plan = params.get("original_plan", {})
        delay_days = params.get("delay_days", 0)

        if not original_plan:
            return {
                "status": "error",
                "agent": self.agent_name,
                "data": {"message": "Mangler original jobbplan for omberegning."},
            }

        try:
            original_start = datetime.strptime(original_plan.get("proposed_start", ""), "%Y-%m-%d")
            original_finish = datetime.strptime(original_plan.get("proposed_finish", ""), "%Y-%m-%d")
            original_mob = datetime.strptime(original_plan.get("vendor_mob_deadline", ""), "%Y-%m-%d")
        except (ValueError, TypeError):
            return {
                "status": "error",
                "agent": self.agent_name,
                "data": {"message": "Ugyldig datoformat i original jobbplan."},
            }

        delta = timedelta(days=delay_days)
        new_start = original_start + delta
        new_finish = original_finish + delta
        new_mob = original_mob + delta

        revised_plan = dict(original_plan)
        revised_plan["proposed_start"] = new_start.strftime("%Y-%m-%d")
        revised_plan["proposed_finish"] = new_finish.strftime("%Y-%m-%d")
        revised_plan["vendor_mob_deadline"] = new_mob.strftime("%Y-%m-%d")
        revised_plan["delay_applied_days"] = delay_days
        revised_plan["revision_note"] = (
            f"Revisjon: {delay_days} dagers forsinkelse lagt inn. "
            f"Opprinnelig oppstart {original_plan.get('proposed_start')} → ny oppstart {new_start.strftime('%Y-%m-%d')}."
        )

        return {
            "status": "ok",
            "agent": self.agent_name,
            "data": {"plan": revised_plan, "delay_days": delay_days},
        }

    def _find_vendor_id(self, equipment: dict) -> Optional[str]:
        """Determine vendor_id from equipment frame agreement or manufacturer."""
        fa = equipment.get("vendor_frame_agreement", "")
        if "Baker Hughes" in fa or "NP" in fa:
            return "BH-NP"
        if "Siemens" in fa:
            return "SE"
        if "MAN" in fa:
            return "MAN-ES"
        if "Flowserve" in fa:
            return "FS"
        if "John Crane" in fa:
            return "JC"
        if "SKF" in fa:
            return "SKF"
        # Fallback to manufacturer
        mfr = equipment.get("manufacturer", "")
        if "Baker Hughes" in mfr or "Nuovo Pignone" in mfr:
            return "BH-NP"
        if "Siemens" in mfr:
            return "SE"
        if "MAN" in mfr:
            return "MAN-ES"
        if "Flowserve" in mfr:
            return "FS"
        return None

    def _check_parts_status(self, part_ids: list) -> list:
        """Check stock status for a list of part IDs."""
        result = []
        for part_id in part_ids:
            part = db_reader.get_spare_part(self.db_path, part_id)
            if part:
                qty = part.get("stock_quantity", 0) or 0
                result.append({
                    "part_id": part_id,
                    "description": part.get("description", "N/A"),
                    "stock_quantity": qty,
                    "stock_location": part.get("stock_location", "N/A"),
                    "available": qty > 0,
                    "criticality": part.get("criticality", "N/A"),
                })
            else:
                result.append({
                    "part_id": part_id,
                    "description": "Ukjent del",
                    "stock_quantity": 0,
                    "stock_location": "N/A",
                    "available": False,
                    "criticality": "Ukjent",
                })
        return result

    def _summarize_parts_status(self, parts_detail: list) -> str:
        """Return a human-readable summary of parts availability."""
        if not parts_detail:
            return "Ingen kritiske reservedeler kreves"
        all_available = all(p.get("available") for p in parts_detail)
        if all_available:
            locations = list({p.get("stock_location", "N/A") for p in parts_detail})
            return "På lager — " + ", ".join(locations)
        missing = [p["part_id"] for p in parts_detail if not p.get("available")]
        return f"MANGLER PÅ LAGER: {', '.join(missing)} — bestilling nødvendig"

    def _get_next_sequence(self, tag: str, year: int) -> int:
        """Calculate the next job sequence number for a tag/year combination."""
        # Read existing work orders to determine next seq number
        all_wos = db_reader.get_all_work_orders(self.db_path)
        prefix = f"JOB-{year}-{tag}-"
        existing = [
            wo.get("safran_activity_id", "") for wo in all_wos
            if wo.get("equipment_tag", "").upper() == tag.upper()
        ]
        # Count how many jobs this year already exist
        count = sum(1 for _ in existing if str(year) in _)
        return count + 1
