"""
Scenario 03 — Vendor delivery delay and re-planning.

Workflow:
  1. Starting state: Job JOB-2026-K3101-001 is in progress
  2. Baker Hughes reports 21-day delivery delay on bundle NP-BDL-PCL804-001
  3. ExecutionAgent: finds the affected work order
  4. PlanningAgent: recalculates timeline with new dates
  5. VendorAgent: drafts formal delay acknowledgment email
  6. VendorAgent: drafts escalation email
  7. Output: revised job plan + two draft emails
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator import OrchestratorAgent
from agents.execution_agent import ExecutionAgent
from agents.planning_agent import PlanningAgent
from agents.vendor_agent import VendorAgent
from tools.report_generator import section_header, sub_header, format_job_plan
from tools import db_reader

DB_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_scenario():
    print(section_header("EQUINOR — ROTERENDE UTSTYR AGENT SYSTEM", width=65))
    print("  Scenario 03: Leverandørforsinkelse og replanning")
    print("=" * 65)

    user_request = "Baker Hughes melder 21 dagers forsinkelse på bundle NP-BDL-PCL804-001"
    print(f"\n  Brukerforespørsel: \"{user_request}\"")
    print(f"\n  Bakgrunn: Jobbplan JOB-2026-K3101 er opprettet og aktiv.")
    print(f"  Baker Hughes varsler forsinket leveranse av bundledel.")
    print()

    execution_agent = ExecutionAgent(db_path=DB_PATH)
    planning_agent = PlanningAgent(db_path=DB_PATH)
    vendor_agent = VendorAgent(db_path=DB_PATH)

    delay_days = 21
    part_id = "NP-BDL-PCL804-001"

    # --- Step 1: Find affected work order ---
    print(section_header("STEG 1 — UTFØRELSESAGENT: Finn berørt arbeidsordre", width=65))
    exec_result = execution_agent.run({
        "action": "find_by_equipment",
        "tag": "K-3101",
    })

    open_wos = exec_result.get("data", {}).get("open_work_orders", [])
    all_matching = exec_result.get("data", {}).get("matching_work_orders", [])

    print(f"  Søker etter åpne arbeidsordre for K-3101...")
    print(f"  Totalt funnet: {len(all_matching)} arbeidsordre for K-3101")
    print(f"  Åpne (ikke TECO/CLSD): {len(open_wos)}")

    if open_wos:
        wo = open_wos[0]
        print(sub_header(f"Berørt arbeidsordre: {wo.get('wo_number')}", width=65))
        print(f"  Beskrivelse   : {wo.get('description', 'N/A')}")
        print(f"  Status        : {wo.get('status', 'N/A')}")
        print(f"  Planlagt start: {wo.get('start_date', 'N/A')}")
        print(f"  Leverandør    : {wo.get('vendor', 'N/A')}")
        print(f"  Safran aktivitet: {wo.get('safran_activity_id', 'N/A')}")

        # Build original plan from work order
        original_plan = {
            "job_id": wo.get("safran_activity_id", f"ACT-2026-K3101-OH"),
            "title": wo.get("description", "Bundle-skifte K-3101"),
            "equipment_tag": "K-3101",
            "platform": "Troll A",
            "platform_id": "TROLL-A",
            "proposed_start": wo.get("start_date", "2026-09-01"),
            "proposed_finish": "2026-09-15",
            "vendor_mob_deadline": "2026-08-15",
            "vendor": "Baker Hughes / Nuovo Pignone",
            "vendor_id": "BH-NP",
            "pob_days": wo.get("pob_days", 15),
            "crew_required": {
                "equinor_technicians": wo.get("technicians_equinor", 2),
                "vendor_technicians": wo.get("technicians_vendor", 4),
                "discipline_lead": 1,
            },
            "critical_parts": [part_id],
            "parts_status": "Forsinket leveranse — 21 dager",
            "ptw_type": "Hot Work + Confined Space Entry + LOTO",
            "safran_activity": wo.get("safran_activity_id", "ACT-2026-K3101-OH"),
            "sap_wo_type": wo.get("wo_type", "PM02"),
            "estimated_cost_nok": wo.get("cost_nok", 4200000),
            "risk_level": "Høy",
            "activities": [
                "1. Avslutning og trykkavlastning",
                "2. Isolasjon og låsing (LOTO)",
                "3. Åpning kompressorhus og visuell inspeksjon",
                "4. Løfting og utfjerning av gammel bundle",
                "5. Installasjon av ny bundle",
                "6. Alignment og mekanisk ferdigstillelse",
                "7. Tetthetsprøving",
                "8. Oppstart og driftsverifikasjon",
            ],
        }
    else:
        # No open WO found — use a known planned WO from database
        print("  Ingen åpne WO funnet via open_work_orders. Søker i alle WO...")
        # Use the CRTD work order for K-3101 2026
        original_plan = {
            "job_id": "ACT-2026-K3101-OH",
            "title": "Bundle-skifte K-3101 Troll A - 2026 overhaul",
            "equipment_tag": "K-3101",
            "platform": "Troll A",
            "platform_id": "TROLL-A",
            "proposed_start": "2026-09-01",
            "proposed_finish": "2026-09-15",
            "vendor_mob_deadline": "2026-08-15",
            "vendor": "Baker Hughes / Nuovo Pignone",
            "vendor_id": "BH-NP",
            "pob_days": 15,
            "crew_required": {
                "equinor_technicians": 2,
                "vendor_technicians": 4,
                "discipline_lead": 1,
            },
            "critical_parts": [part_id],
            "parts_status": "Forsinket leveranse — 21 dager",
            "ptw_type": "Hot Work + Confined Space Entry + LOTO",
            "safran_activity": "ACT-2026-K3101-OH",
            "sap_wo_type": "PM02",
            "estimated_cost_nok": 4200000,
            "risk_level": "Høy",
            "activities": [
                "1. Avslutning og trykkavlastning",
                "2. Isolasjon og låsing (LOTO)",
                "3. Åpning og inspeksjon",
                "4. Utfjerning av gammel bundle",
                "5. Installasjon av ny bundle",
                "6. Alignment og mekanisk ferdigstillelse",
                "7. Tetthetsprøving",
                "8. Oppstart og driftsverifikasjon",
            ],
        }
        print(f"  Bruker planlagt arbeidsordre: {original_plan['job_id']}")

    print(sub_header("Original jobbplan (FØR forsinkelse)", width=65))
    print(f"  Oppstart    : {original_plan['proposed_start']}")
    print(f"  Ferdigstilt : {original_plan['proposed_finish']}")
    print(f"  Mob.-frist  : {original_plan['vendor_mob_deadline']}")

    # --- Step 2: Recalculate timeline ---
    print(section_header("STEG 2 — PLANLEGGINGSAGENT: Beregner ny tidsplan", width=65))
    print(f"  Forsinkelse: {delay_days} dager")
    print(f"  Del: {part_id}")
    print()

    revised_result = planning_agent.recalculate_timeline({
        "original_plan": original_plan,
        "delay_days": delay_days,
    })

    if revised_result.get("status") != "ok":
        print(f"  FEIL: {revised_result['data'].get('message')}")
        return

    revised_plan = revised_result["data"]["plan"]

    print(sub_header("Revidert jobbplan (ETTER forsinkelse)", width=65))
    print(f"  Opprinnelig oppstart  : {original_plan['proposed_start']}")
    print(f"  Ny oppstart           : {revised_plan['proposed_start']}")
    print(f"  Opprinnelig ferdig    : {original_plan['proposed_finish']}")
    print(f"  Ny ferdig             : {revised_plan['proposed_finish']}")
    print(f"  Ny mob.-frist         : {revised_plan['vendor_mob_deadline']}")
    print(f"  Forsinkelse lagt inn  : {revised_plan['delay_applied_days']} dager")
    print()
    print(f"  {revised_plan.get('revision_note', '')}")

    # --- Step 3: Delay acknowledgment email ---
    print(section_header("STEG 3 — LEVERANDØRAGENT: Forsinkelsesbekreftelse e-post", width=65))

    orig_start = original_plan["proposed_start"]
    new_start = revised_plan["proposed_start"]

    # Fetch part description
    part = db_reader.get_spare_part(DB_PATH, part_id)
    part_description = part.get("description", part_id) if part else part_id

    delay_email_result = vendor_agent.run({
        "action": "draft_delay_email",
        "plan": revised_plan,
        "delay_days": delay_days,
        "part_id": part_id,
        "part_description": part_description,
        "original_delivery_date": orig_start,
        "new_delivery_date": new_start,
    })

    print(sub_header("E-post 1 — Formell forsinkelsesbekreftelse", width=65))
    if delay_email_result.get("status") == "ok":
        print(f"  Til: {delay_email_result['data'].get('to', 'N/A')}")
        print(f"  Leverandør: {delay_email_result['data'].get('vendor', 'N/A')}")
        print()
        print(delay_email_result["data"]["email_text"])
    else:
        print(f"  FEIL: {delay_email_result['data'].get('message')}")

    # --- Step 4: Escalation email ---
    print(section_header("STEG 4 — LEVERANDØRAGENT: Eskalerings e-post", width=65))

    # For the second email, simulate escalation to technical lead
    escalation_result = vendor_agent.run({
        "action": "draft_delay_email",
        "plan": revised_plan,
        "delay_days": delay_days,
        "part_id": part_id,
        "part_description": part_description,
        "original_delivery_date": orig_start,
        "new_delivery_date": new_start,
    })

    print(sub_header("E-post 2 — Eskalering til teknisk kontakt", width=65))
    if escalation_result.get("status") == "ok":
        vendor = db_reader.get_vendor(DB_PATH, "BH-NP")
        tech_contact = vendor.get("technical_contact", "N/A") if vendor else "N/A"
        tech_email = vendor.get("technical_email", "N/A") if vendor else "N/A"
        print(f"  Til (teknisk kontakt): {tech_contact} <{tech_email}>")
        print(f"  Leverandør: {escalation_result['data'].get('vendor', 'N/A')}")
        print()
        print(escalation_result["data"]["email_text"])
    else:
        print(f"  FEIL: {escalation_result['data'].get('message')}")

    # --- Final summary ---
    print(section_header("SCENARIO 03 FULLFØRT", width=65))
    print(f"  Jobb-ID              : {revised_plan['job_id']}")
    print(f"  Opprinnelig oppstart : {original_plan['proposed_start']}")
    print(f"  Revidert oppstart    : {revised_plan['proposed_start']}")
    print(f"  Forsinkelse          : {delay_days} dager ({delay_days // 7} uker)")
    print(f"  Berørt del           : {part_id}")
    print(f"  E-poster sendt       : 2 (forsinkelsesbekreftelse + eskalering)")
    print()


if __name__ == "__main__":
    run_scenario()
