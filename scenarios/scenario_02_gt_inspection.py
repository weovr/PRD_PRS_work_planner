"""
Scenario 02 — Gas turbine borescope inspection workflow on Gullfaks C.

Workflow:
  1. User request: Plan borescope inspection GT-4201 Gullfaks C
  2. EquipmentAgent: fetch GT-4201 data
  3. PlanningAgent: create inspection plan from gt_borescope_inspection template
  4. SafetyAgent: verify certifications for proposed crew
  5. Output: inspection plan with Siemens Energy contact and required personnel
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator import OrchestratorAgent
from tools.report_generator import (
    section_header, sub_header,
    format_equipment_summary, format_job_plan,
    format_safety_report, format_vendor_info,
)

DB_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_scenario():
    print(section_header("EQUINOR — ROTERENDE UTSTYR AGENT SYSTEM", width=65))
    print("  Scenario 02: Boreskopinspeksjon GT-4201, Gullfaks C")
    print("=" * 65)

    user_request = "Planlegg boreskopinspeksjon GT-4201 Gullfaks C"
    print(f"\n  Brukerforespørsel: \"{user_request}\"")
    print()

    orchestrator = OrchestratorAgent(db_path=DB_PATH)

    # --- Step 1: Equipment lookup ---
    print(section_header("STEG 1 — UTSTYRSAGENT: GT-4201 Oppslag", width=65))
    eq_agent = orchestrator.agents["equipment"]
    eq_result = eq_agent.run({"tag": "GT-4201"})

    if eq_result.get("status") != "ok":
        print(f"  FEIL: {eq_result['data'].get('message')}")
        return

    print(format_equipment_summary(eq_result["data"]))
    equipment = eq_result["data"]["equipment"]

    # Check overhaul status
    oh_status = eq_result["data"]["overhaul_status"]
    print(sub_header("Overhaul-status"))
    if oh_status["overhaul_overdue"]:
        print(f"  *** ADVARSEL: Overhaul-intervall overskredet med "
              f"{abs(oh_status['hours_remaining'])} timer! ***")
    else:
        print(f"  Driftstimer ved siste overhaul: {oh_status['running_hours']:,}".replace(",", " "))
        print(f"  Timer til neste overhaul: {oh_status['hours_remaining']:,}".replace(",", " "))
        print(f"  Neste planlagt: {oh_status.get('next_planned_overhaul', 'N/A')}")

    # --- Step 2: Inspection planning ---
    print(section_header("STEG 2 — PLANLEGGINGSAGENT: Inspeksjonsplan", width=65))
    plan_agent = orchestrator.agents["planning"]
    plan_result = plan_agent.run({
        "tag": "GT-4201",
        "job_type": "gt_borescope_inspection",
        "proposed_start": "2025-06-01",
        "equipment_data": equipment,
    })

    if plan_result.get("status") != "ok":
        print(f"  FEIL: {plan_result['data'].get('message')}")
        return

    plan = plan_result["data"]["plan"]
    print(format_job_plan(plan))

    # --- Step 3: Safety check ---
    print(section_header("STEG 3 — SIKKERHETSAGENT: Sertifikatvalidering", width=65))
    safety_agent = orchestrator.agents["safety"]
    safety_result = safety_agent.run({
        "plan": plan,
        "platform_id": "GULLFAKS-C",
    })
    print(format_safety_report(safety_result["data"]))

    # --- Step 4: Vendor information ---
    print(section_header("STEG 4 — LEVERANDØRAGENT: Siemens Energy Kontakt", width=65))
    vendor_agent = orchestrator.agents["vendor"]
    vendor_lookup = vendor_agent.run({
        "action": "lookup",
        "vendor_id": "SE",
        "job_start_date": plan["proposed_start"],
    })
    print(format_vendor_info(vendor_lookup["data"]))

    print(sub_header("Nødvendig bemanning for inspeksjon", width=65))
    crew = plan.get("crew_required", {})
    print(f"  Equinor teknikere   : {crew.get('equinor_technicians', 0)}")
    print(f"  Leverandørteknikere : {crew.get('vendor_technicians', 0)} (Siemens Energy boreskopspesialist)")
    print(f"  Disiplinleder       : {crew.get('discipline_lead', 0)}")
    print(f"  Totalt POB-dager    : {plan.get('pob_days', 'N/A')}")

    # --- Final summary ---
    print(section_header("SCENARIO 02 FULLFØRT", width=65))
    print(f"  Inspeksjonsplan opprettet  : {plan['job_id']}")
    print(f"  Foreslått inspeksjonsdato  : {plan['proposed_start']} → {plan['proposed_finish']}")
    print(f"  Leverandør                 : {plan['vendor']}")
    print(f"  Sikkerhetsstatus           : {safety_result['data'].get('overall_status', 'N/A')}")
    warnings = safety_result["data"].get("warnings", [])
    if warnings:
        print(f"  Sikkerhetadvarsler ({len(warnings)}):")
        for w in warnings:
            print(f"    ! {w}")
    print()


if __name__ == "__main__":
    run_scenario()
