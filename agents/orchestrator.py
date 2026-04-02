"""
OrchestratorAgent — master agent that receives user requests in natural language,
parses intent, routes to specialist agents in sequence, and assembles final output.
"""

from typing import Any
from agents.equipment_agent import EquipmentAgent
from agents.planning_agent import PlanningAgent
from agents.vendor_agent import VendorAgent
from agents.execution_agent import ExecutionAgent
from agents.safety_agent import SafetyAgent


# Intent keywords for routing — deterministic keyword matching
INTENT_KEYWORDS = {
    "plan_job": [
        "planlegg", "planlegge", "opprett jobbplan", "bundleskifte", "overhaul",
        "boreskop", "tettingsbytte", "lagerbytte", "pumperevisjon", "hot section",
    ],
    "check_equipment": [
        "utstyrsstatus", "utstyrsinfo", "sjekk utstyr", "spesifikasjon", "historikk",
        "driftstimer", "vedlikeholdshistorikk",
    ],
    "check_vendor": [
        "leverandørinfo", "leverandørstatus", "sjekk leverandør", "rammekontrakt",
        "ledetid", "mob-tid",
    ],
    "check_parts": [
        "reservedeler", "lagersjekk", "reservedelssjekk", "sjekk deler",
    ],
    "draft_vendor_email": [
        "e-post", "epost", "skriv til leverandør", "leverandøre-post",
    ],
    "execution_status": [
        "status", "åpne arbeidsordre", "pågående jobb", "forsinkelse", "forsinket",
        "daglig rapport",
    ],
    "check_crew": [
        "bemanning", "sertifikat", "sertifikater", "crew", "certifikater", "krets",
    ],
    "vendor_delay": [
        "forsinkelse", "forsinket", "melder forsinkelse", "delay", "utsatt levering",
    ],
}


class OrchestratorAgent:
    """
    Master routing agent. Parses user intent from Norwegian/English text,
    activates specialist agents in the correct order, and returns assembled results.
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.agents = {
            "planning": PlanningAgent(db_path),
            "equipment": EquipmentAgent(db_path),
            "vendor": VendorAgent(db_path),
            "execution": ExecutionAgent(db_path),
            "safety": SafetyAgent(db_path),
        }

    def run(self, user_request: str) -> dict:
        """
        Main entry point. Accepts a free-text user request, parses intent,
        routes to agents, and returns a structured result dict.
        """
        request_lower = user_request.lower()
        intent = self._parse_intent(request_lower)
        equipment_tag = self._extract_equipment_tag(user_request)
        date_str = self._extract_date(user_request)

        results = {
            "user_request": user_request,
            "intent": intent,
            "equipment_tag": equipment_tag,
            "agent_results": {},
        }

        if intent == "plan_job":
            results = self._handle_plan_job(results, equipment_tag, date_str, user_request)
        elif intent == "vendor_delay":
            results = self._handle_vendor_delay(results, user_request)
        elif intent == "check_equipment":
            results = self._handle_check_equipment(results, equipment_tag)
        elif intent == "check_vendor":
            vendor_name = self._extract_vendor_name(user_request)
            results = self._handle_check_vendor(results, vendor_name)
        elif intent == "execution_status":
            results = self._handle_execution_status(results)
        elif intent == "check_crew":
            results = self._handle_check_crew(results, equipment_tag)
        else:
            results["agent_results"]["error"] = {
                "status": "error",
                "message": f"Klarte ikke å tolke forespørselen: '{user_request}'. "
                           f"Prøv å inkludere utstyrstagg (f.eks. K-3101) og jobbtype.",
            }

        return results

    def _handle_plan_job(self, results: dict, tag: str, date_str: str, request: str) -> dict:
        """Full job planning workflow: Equipment → Planning → Safety → Vendor."""
        # Step 1: Equipment lookup
        eq_result = self.agents["equipment"].run({"tag": tag})
        results["agent_results"]["equipment"] = eq_result

        if eq_result.get("status") not in ("ok",):
            return results

        equipment = eq_result["data"]["equipment"]

        # Step 2: Determine job type from request
        job_type = self._determine_job_type(request, equipment)

        # Step 3: Planning
        plan_result = self.agents["planning"].run({
            "tag": tag,
            "job_type": job_type,
            "proposed_start": date_str,
            "equipment_data": equipment,
        })
        results["agent_results"]["planning"] = plan_result

        if plan_result.get("status") != "ok":
            return results

        plan = plan_result["data"]["plan"]

        # Step 4: Safety check
        safety_result = self.agents["safety"].run({
            "plan": plan,
            "platform_id": equipment.get("platform_id", ""),
        })
        results["agent_results"]["safety"] = safety_result

        # Step 5: Vendor — lookup and draft mobilization email
        vendor_lookup = self.agents["vendor"].run({
            "action": "lookup",
            "vendor_id": plan.get("vendor_id"),
            "job_start_date": plan.get("proposed_start"),
        })
        results["agent_results"]["vendor_lookup"] = vendor_lookup

        email_result = self.agents["vendor"].run({
            "action": "draft_mobilization_email",
            "plan": plan,
        })
        results["agent_results"]["vendor_email"] = email_result

        return results

    def _handle_vendor_delay(self, results: dict, request: str) -> dict:
        """Vendor delay workflow: find affected WO → recalculate timeline → draft emails."""
        delay_days = self._extract_delay_days(request)
        part_id = self._extract_part_id(request)
        tag = results.get("equipment_tag", "K-3101")

        # Step 1: Find affected work order
        exec_result = self.agents["execution"].run({
            "action": "find_by_equipment",
            "tag": tag,
        })
        results["agent_results"]["execution"] = exec_result

        # Find most recent open WO for this equipment
        open_wos = exec_result.get("data", {}).get("open_work_orders", [])
        original_plan = None
        if open_wos:
            wo = open_wos[0]
            # Build a pseudo-plan from the work order
            original_plan = {
                "job_id": wo.get("safran_activity_id", f"JOB-{wo.get('wo_number')}"),
                "title": wo.get("description", ""),
                "equipment_tag": wo.get("equipment_tag", tag),
                "platform": wo.get("platform_id", ""),
                "platform_id": wo.get("platform_id", ""),
                "proposed_start": wo.get("start_date", ""),
                "proposed_finish": wo.get("finish_date") or "2026-09-15",
                "vendor_mob_deadline": "2026-08-15",
                "vendor": "Baker Hughes / Nuovo Pignone",
                "vendor_id": "BH-NP",
                "pob_days": wo.get("pob_days", 15),
                "crew_required": {},
                "critical_parts": [part_id] if part_id else [],
                "parts_status": "Forsinket levering",
                "ptw_type": "Hot Work + Confined Space",
                "safran_activity": wo.get("safran_activity_id", ""),
                "sap_wo_type": wo.get("wo_type", "PM02"),
                "estimated_cost_nok": wo.get("cost_nok", 4200000),
                "risk_level": "Høy",
                "activities": [],
            }
        else:
            # Fallback: search for the specific WO by part or tag in all WOs
            all_wos_result = self.agents["execution"].run({"action": "status"})
            all_open = all_wos_result.get("data", {}).get("open_work_orders", [])
            if all_open:
                wo = all_open[0]
                original_plan = {
                    "job_id": wo.get("safran_activity_id", ""),
                    "title": wo.get("description", ""),
                    "equipment_tag": wo.get("equipment_tag", ""),
                    "platform": wo.get("platform_id", ""),
                    "platform_id": wo.get("platform_id", ""),
                    "proposed_start": wo.get("start_date", ""),
                    "proposed_finish": wo.get("finish_date") or "2026-09-15",
                    "vendor_mob_deadline": "2026-08-15",
                    "vendor": "Baker Hughes / Nuovo Pignone",
                    "vendor_id": "BH-NP",
                    "pob_days": wo.get("pob_days", 15),
                    "crew_required": {},
                    "critical_parts": [part_id] if part_id else [],
                    "parts_status": "Forsinket levering",
                    "ptw_type": "Hot Work + Confined Space",
                    "safran_activity": wo.get("safran_activity_id", ""),
                    "sap_wo_type": wo.get("wo_type", "PM02"),
                    "estimated_cost_nok": wo.get("cost_nok", 0),
                    "risk_level": "Høy",
                    "activities": [],
                }

        if not original_plan:
            results["agent_results"]["error"] = {
                "status": "error",
                "message": "Ingen åpen arbeidsordre funnet for omplanlegging.",
            }
            return results

        # Step 2: Recalculate timeline
        revised_result = self.agents["planning"].recalculate_timeline({
            "original_plan": original_plan,
            "delay_days": delay_days,
        })
        results["agent_results"]["planning_revised"] = revised_result
        revised_plan = revised_result.get("data", {}).get("plan", original_plan)

        # Step 3: Draft delay acknowledgment email
        from datetime import datetime, timedelta
        try:
            orig_start = datetime.strptime(original_plan.get("proposed_start", ""), "%Y-%m-%d")
            new_start = orig_start + timedelta(days=delay_days)
        except (ValueError, TypeError):
            orig_start_str = original_plan.get("proposed_start", "N/A")
            new_start_str = "N/A"
        else:
            orig_start_str = orig_start.strftime("%Y-%m-%d")
            new_start_str = new_start.strftime("%Y-%m-%d")

        part_description = part_id or "Kritisk reservedel"
        delay_email_result = self.agents["vendor"].run({
            "action": "draft_delay_email",
            "plan": revised_plan,
            "delay_days": delay_days,
            "part_id": part_id,
            "part_description": part_description,
            "original_delivery_date": orig_start_str,
            "new_delivery_date": new_start_str,
        })
        results["agent_results"]["vendor_delay_email"] = delay_email_result

        # Step 4: Draft escalation email (second email)
        escalation_email_result = self.agents["vendor"].run({
            "action": "draft_delay_email",
            "plan": revised_plan,
            "delay_days": delay_days,
            "part_id": part_id,
            "part_description": part_description,
            "original_delivery_date": orig_start_str,
            "new_delivery_date": new_start_str,
        })
        results["agent_results"]["vendor_escalation_email"] = escalation_email_result

        return results

    def _handle_check_equipment(self, results: dict, tag: str) -> dict:
        """Equipment lookup workflow."""
        eq_result = self.agents["equipment"].run({"tag": tag})
        results["agent_results"]["equipment"] = eq_result
        return results

    def _handle_check_vendor(self, results: dict, vendor_name: str) -> dict:
        """Vendor lookup workflow."""
        vendor_result = self.agents["vendor"].run({
            "action": "lookup",
            "vendor_name": vendor_name,
        })
        results["agent_results"]["vendor"] = vendor_result
        return results

    def _handle_execution_status(self, results: dict) -> dict:
        """Execution status workflow."""
        exec_result = self.agents["execution"].run({"action": "status"})
        results["agent_results"]["execution"] = exec_result
        return results

    def _handle_check_crew(self, results: dict, tag: str) -> dict:
        """Crew certification check workflow."""
        equipment = db_reader_helper_get_equipment(self.db_path, tag) if tag else None
        platform_id = equipment.get("platform_id", "") if equipment else ""
        safety_result = self.agents["safety"].run({
            "plan": {},
            "platform_id": platform_id,
        })
        results["agent_results"]["safety"] = safety_result
        return results

    # --- Intent parsing helpers ---

    def _parse_intent(self, request_lower: str) -> str:
        """Determine the primary intent from a lowercased request string."""
        # Vendor delay is a special compound intent — check first
        if any(kw in request_lower for kw in INTENT_KEYWORDS["vendor_delay"]):
            if "melder" in request_lower or "forsinkelse" in request_lower:
                return "vendor_delay"

        # Score each intent by keyword hits
        scores = {}
        for intent, keywords in INTENT_KEYWORDS.items():
            scores[intent] = sum(1 for kw in keywords if kw in request_lower)

        # Return highest scoring intent, or 'plan_job' as default
        best_intent = max(scores, key=scores.get)
        if scores[best_intent] == 0:
            return "plan_job"
        return best_intent

    def _extract_equipment_tag(self, request: str) -> str:
        """Extract equipment tag from request text using pattern matching."""
        import re
        # Match patterns like K-3101, GT-4201, P-6101, GT-3101A, GT-3101B
        pattern = r'\b(K|GT|P)-?\d{4}[A-Z]?\b'
        matches = re.findall(pattern, request, re.IGNORECASE)
        # Also match with full pattern
        full_pattern = r'\b(?:K|GT|P)-\d{4}[A-Z]?\b'
        full_matches = re.findall(full_pattern, request, re.IGNORECASE)
        if full_matches:
            return full_matches[0].upper()
        return "K-3101"  # Default for demo

    def _extract_date(self, request: str) -> str:
        """Extract a proposed start date from request text."""
        import re
        # ISO date format
        iso_match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', request)
        if iso_match:
            return iso_match.group(1)
        # Norwegian date format: "1. september 2026"
        month_map = {
            "januar": "01", "februar": "02", "mars": "03", "april": "04",
            "mai": "05", "juni": "06", "juli": "07", "august": "08",
            "september": "09", "oktober": "10", "november": "11", "desember": "12",
        }
        no_date_pattern = r'(\d{1,2})\.\s*(' + "|".join(month_map.keys()) + r')\s+(\d{4})'
        match = re.search(no_date_pattern, request.lower())
        if match:
            day = match.group(1).zfill(2)
            month = month_map.get(match.group(2), "01")
            year = match.group(3)
            return f"{year}-{month}-{day}"
        return ""

    def _determine_job_type(self, request: str, equipment: dict) -> str:
        """Determine the most appropriate job template based on request and equipment type."""
        request_lower = request.lower()
        eq_type = equipment.get("type", "").lower()

        if "bundle" in request_lower or "bundleskifte" in request_lower:
            return "bundle_change_centrifugal_compressor"
        if "boreskop" in request_lower or "borescope" in request_lower:
            return "gt_borescope_inspection"
        if "hot section" in request_lower:
            return "gt_hot_section_overhaul"
        if "tetning" in request_lower or "tettingsbytte" in request_lower:
            return "seal_replacement_centrifugal"
        if "lager" in request_lower and "bytte" in request_lower:
            return "bearing_replacement"
        if "pumpe" in request_lower or "pumperevisjon" in request_lower:
            return "pump_overhaul"
        if "overhaul" in request_lower:
            # Determine by equipment type
            if "gassturbine" in eq_type or "turbine" in eq_type:
                return "gt_hot_section_overhaul"
            if "pumpe" in eq_type:
                return "pump_overhaul"
            return "bundle_change_centrifugal_compressor"
        # Default by equipment type
        if "gassturbine" in eq_type:
            return "gt_borescope_inspection"
        if "pumpe" in eq_type:
            return "pump_overhaul"
        return "bundle_change_centrifugal_compressor"

    def _extract_vendor_name(self, request: str) -> str:
        """Extract vendor name fragment from request."""
        vendors = ["baker hughes", "siemens", "man energy", "flowserve", "john crane", "skf"]
        request_lower = request.lower()
        for v in vendors:
            if v in request_lower:
                return v
        return ""

    def _extract_delay_days(self, request: str) -> int:
        """Extract number of delay days from request text."""
        import re
        # Look for patterns like "21 dagers", "3 ukers", "21 days"
        day_match = re.search(r'(\d+)\s*dag', request.lower())
        if day_match:
            return int(day_match.group(1))
        week_match = re.search(r'(\d+)\s*uke', request.lower())
        if week_match:
            return int(week_match.group(1)) * 7
        return 21  # Default to 3 weeks if not found

    def _extract_part_id(self, request: str) -> str:
        """Extract a part ID from request text."""
        import re
        # Match patterns like NP-BDL-PCL804-001
        match = re.search(r'\b[A-Z]{2,}-[A-Z0-9\-]{5,}\b', request)
        if match:
            return match.group(0)
        return "NP-BDL-PCL804-001"  # Default for demo


def db_reader_helper_get_equipment(db_path: str, tag: str):
    """Helper to avoid circular import in orchestrator."""
    from tools import db_reader
    return db_reader.get_equipment(db_path, tag)
