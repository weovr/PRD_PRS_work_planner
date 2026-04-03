"""
Interactive CLI demo entry point for the Equinor Rotating Equipment Agent System.
Run with: python demo/run_demo.py
"""

import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator import OrchestratorAgent
from tools.report_generator import (
    section_header, sub_header,
    format_equipment_summary, format_job_plan,
    format_safety_report, format_vendor_info,
    format_execution_status,
)

DB_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BANNER = """
===================================================================
  EQUINOR — Roterende Utstyr Agent System (Demo)
  Roterende utstyr | Offshore vedlikeholdsplanlegging
===================================================================
  ADVARSEL: Kun demonstrasjonssystem med fiktive data.
  Ingen tilknytning til Equinors systemer (SAP, Safran, o.l.)
===================================================================
"""

MENU = """
Velg ett av følgende scenarioer:
  [1] Planlegg bundleskifte K-3101, Troll A
  [2] Planlegg boreskopinspeksjon GT-4201, Gullfaks C
  [3] Leverandørforsinkelse og replanning (Baker Hughes / K-3101)
  [4] Sjekk utstyrsstatus (fritekst eksempel: K-4201)
  [5] Vis åpne arbeidsordre
  [6] Egendefinert forespørsel (fritekst)
  [q] Avslutt

Ditt valg: """


def run_scenario_1():
    """Run scenario 01 inline."""
    import scenarios.scenario_01_bundle_change as s1
    s1.run_scenario()


def run_scenario_2():
    """Run scenario 02 inline."""
    import scenarios.scenario_02_gt_inspection as s2
    s2.run_scenario()


def run_scenario_3():
    """Run scenario 03 inline."""
    import scenarios.scenario_03_vendor_delay as s3
    s3.run_scenario()


def run_equipment_check():
    """Interactive equipment check."""
    tag = input("\n  Skriv inn utstyrstagg (f.eks. K-4201, GT-3101A, P-6101): ").strip().upper()
    if not tag:
        print("  Ingen tagg oppgitt.")
        return

    orchestrator = OrchestratorAgent(db_path=DB_PATH)
    eq_result = orchestrator.agents["equipment"].run({"tag": tag})

    if eq_result.get("status") == "ok":
        print(format_equipment_summary(eq_result["data"]))
    elif eq_result.get("status") == "not_found":
        print(f"\n  Utstyr ikke funnet: {tag}")
        print(f"  Tilgjengelige tagger inkluderer: K-3101, K-3102, K-4201, K-5301,")
        print(f"  GT-3101A, GT-3101B, GT-4201, GT-5401, P-6101, P-6102,")
        print(f"  P-9201, P-9202, K-7101, K-8101, K-8102")
    else:
        print(f"\n  Feil: {eq_result['data'].get('message')}")


def run_open_work_orders():
    """Show all open work orders."""
    orchestrator = OrchestratorAgent(db_path=DB_PATH)
    exec_result = orchestrator.agents["execution"].run({"action": "status"})
    print(format_execution_status(exec_result["data"]))


def run_freetext_request():
    """Run a free-text user request through the orchestrator."""
    print("\n  Eksempler:")
    print("    - Planlegg bundleskifte K-3101 Troll A oppstart 2026-09-01")
    print("    - Boreskopinspeksjon GT-5401 Åsgard B")
    print("    - Sjekk leverandør Baker Hughes")
    print("    - Pumperevisjon P-6101 Troll A")
    print()
    request = input("  Din forespørsel: ").strip()
    if not request:
        print("  Ingen forespørsel oppgitt.")
        return

    orchestrator = OrchestratorAgent(db_path=DB_PATH)
    print(f"\n  Behandler: \"{request}\"")
    print()

    results = orchestrator.run(request)
    intent = results.get("intent", "ukjent")
    print(f"  Tolket forespørsel som: {intent}")
    print(f"  Utstyrstagg: {results.get('equipment_tag', 'N/A')}")
    print()

    agent_results = results.get("agent_results", {})

    if "equipment" in agent_results:
        eq = agent_results["equipment"]
        if eq.get("status") == "ok":
            print(format_equipment_summary(eq["data"]))

    if "planning" in agent_results:
        plan_r = agent_results["planning"]
        if plan_r.get("status") == "ok":
            print(format_job_plan(plan_r["data"]["plan"]))

    if "safety" in agent_results:
        safety_r = agent_results["safety"]
        if safety_r.get("status") == "ok":
            print(format_safety_report(safety_r["data"]))

    if "vendor_lookup" in agent_results:
        vl = agent_results["vendor_lookup"]
        if vl.get("status") == "ok":
            print(format_vendor_info(vl["data"]))

    if "vendor_email" in agent_results:
        ve = agent_results["vendor_email"]
        if ve.get("status") == "ok":
            print(sub_header("E-post utkast — Mobiliseringsforespørsel"))
            print(ve["data"]["email_text"])

    if "execution" in agent_results:
        er = agent_results["execution"]
        if er.get("status") == "ok":
            print(format_execution_status(er["data"]))

    if "vendor" in agent_results:
        vr = agent_results["vendor"]
        if vr.get("status") == "ok":
            print(format_vendor_info(vr["data"]))

    if "error" in agent_results:
        print(f"\n  Feil: {agent_results['error'].get('message')}")


def main():
    print(BANNER)

    while True:
        choice = input(MENU).strip().lower()

        if choice == "1":
            run_scenario_1()
        elif choice == "2":
            run_scenario_2()
        elif choice == "3":
            run_scenario_3()
        elif choice == "4":
            run_equipment_check()
        elif choice == "5":
            run_open_work_orders()
        elif choice == "6":
            run_freetext_request()
        elif choice in ("q", "quit", "exit", "avslutt"):
            print("\n  Avslutter Equinor Roterende Utstyr Agent System. Ha en god arbeidsdag!\n")
            sys.exit(0)
        else:
            print(f"  Ugyldig valg: '{choice}'. Velg 1-6 eller q.")

        input("\n  Trykk Enter for å fortsette...")
        print()


if __name__ == "__main__":
    main()
