"""
Scenario 01 — Full compressor bundle change workflow on Troll A.

Workflow:
  1. User request: Plan bundle change K-3101 Troll A, start 1 September 2026
  2. EquipmentAgent: fetch K-3101 specs and maintenance history
  3. PlanningAgent: create full job plan from bundle_change_centrifugal_compressor template
  4. SafetyAgent: validate crew certifications for proposed job start
  5. VendorAgent: draft mobilization request email to Baker Hughes
  6. Final output: full job plan + vendor email
"""

import sys
import os

# Ensure project root is on path when running directly
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
    print("  Scenario 01: Bundleskifte K-3101, Troll A")
    print("=" * 65)

    user_request = "Planlegg bundleskifte K-3101 Troll A, oppstart 1. september 2026"
    print(f"\n  Brukerforespørsel: \"{user_request}\"")
    print()

    orchestrator = OrchestratorAgent(db_path=DB_PATH)

    # --- Step 1: Equipment lookup ---
    print(section_header("STEG 1 — UTSTYRSAGENT: K-3101 Oppslag", width=65))
    eq_agent = orchestrator.agents["equipment"]
    eq_result = eq_agent.run({"tag": "K-3101"})

    if eq_result.get("status") != "ok":
        print(f"  FEIL: {eq_result['data'].get('message')}")
        return

    print(format_equipment_summary(eq_result["data"]))

    equipment = eq_result["data"]["equipment"]

    # --- Step 2: Job planning ---
    print(section_header("STEG 2 — PLANLEGGINGSAGENT: Jobbplan", width=65))
    plan_agent = orchestrator.agents["planning"]
    plan_result = plan_agent.run({
        "tag": "K-3101",
        "job_type": "bundle_change_centrifugal_compressor",
        "proposed_start": "2026-09-01",
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
        "platform_id": "TROLL-A",
    })

    print(format_safety_report(safety_result["data"]))

    # --- Step 4: Vendor lookup and email ---
    print(section_header("STEG 4 — LEVERANDØRAGENT: Baker Hughes Koordinering", width=65))
    vendor_agent = orchestrator.agents["vendor"]

    vendor_lookup = vendor_agent.run({
        "action": "lookup",
        "vendor_id": "BH-NP",
        "job_start_date": plan["proposed_start"],
    })
    print(format_vendor_info(vendor_lookup["data"]))

    print(sub_header("E-post utkast — Mobiliseringsforespørsel", width=65))
    email_result = vendor_agent.run({
        "action": "draft_mobilization_email",
        "plan": plan,
    })

    if email_result.get("status") == "ok":
        print(email_result["data"]["email_text"])
    else:
        print(f"  FEIL ved e-postutkast: {email_result['data'].get('message')}")

    # --- Final summary ---
    print(section_header("SCENARIO 01 FULLFØRT", width=65))
    overall = safety_result["data"].get("overall_status", "UKJENT")
    print(f"  Jobbplan opprettet   : {plan['job_id']}")
    print(f"  Foreslått oppstart   : {plan['proposed_start']}")
    print(f"  Mob.-frist leverandør: {plan['vendor_mob_deadline']}")
    print(f"  Sikkerhetsstatus     : {overall}")
    warnings = safety_result["data"].get("warnings", [])
    if warnings:
        print(f"  Advarsler ({len(warnings)}):")
        for w in warnings:
            print(f"    ! {w}")
    print()


if __name__ == "__main__":
    run_scenario()
