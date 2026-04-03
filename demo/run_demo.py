"""
Equinor Roterende Utstyr — AI Agent Demo

Interaktiv samtale med en AI-agent som har tilgang til utstyrs- og vedlikeholdsdatabasen.
Skriv spørsmålet ditt på norsk — agenten finner selv ut hva den trenger å slå opp.

Start: python demo/run_demo.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator import OrchestratorAgent

DB_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Labels shown when the agent calls a tool — makes AI reasoning visible
TOOL_LABELS = {
    "get_equipment":            "Slår opp utstyrsinformasjon...",
    "get_work_order_history":   "Henter arbeidsordrehistorikk...",
    "get_open_work_orders":     "Henter åpne arbeidsordre...",
    "get_vendor":               "Slår opp leverandørinformasjon...",
    "get_spare_parts":          "Sjekker reservedelsstatus...",
    "get_job_template":         "Henter jobbmal og sjekkliste...",
    "get_platform":             "Henter plattforminformasjon...",
    "get_personnel":            "Sjekker personell og sertifikater...",
    "calculate_job_timeline":   "Beregner jobbplan og tidsfrister...",
    "calculate_revised_timeline": "Beregner revidert tidsplan...",
}

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║      EQUINOR — Roterende Utstyr AI Agent (PSR Demo)        ║
╚══════════════════════════════════════════════════════════════╝

  Hei! Jeg er din AI-assistent for vedlikeholdsplanlegging av
  roterende utstyr på Equinors offshore-plattformer.

  Jeg har tilgang til databaser for utstyr, arbeidsordre,
  leverandører, reservedeler og personell.

  Eksempler på hva du kan spørre om:
    • Planlegg bundleskifte K-3101 på Troll A, oppstart 1. september 2026
    • Hva er statusen på GT-4201 på Gullfaks C?
    • Baker Hughes melder 3 ukers forsinkelse på bundle til K-3101
    • Hvilke arbeidsordre er åpne akkurat nå?
    • Hvem hos Siemens Energy kontakter vi for GT-4201?
    • Sjekk sertifikatstatus for bemanningen på Troll A

  Skriv 'ny samtale' for å starte på nytt, 'avslutt' for å avslutte.
──────────────────────────────────────────────────────────────────
"""

EKSEMPLER = """
  Scenarioer for demonstrasjon:
    [1] Planlegg bundleskifte K-3101 Troll A, oppstart 1. september 2026
    [2] Planlegg boreskopinspeksjon GT-4201 Gullfaks C
    [3] Baker Hughes melder 21 dagers forsinkelse på bundle NP-BDL-PCL804-001
    [4] Skriv eksempel (fritekst)
"""


def on_tool_call(tool_name: str, tool_input: dict) -> None:
    """Print a progress indicator when the agent calls a tool."""
    label = TOOL_LABELS.get(tool_name, f"Kaller verktøy: {tool_name}...")
    # Show key parameters so it's clear what's being looked up
    detail = ""
    if "tag" in tool_input:
        detail = f" [{tool_input['tag']}]"
    elif "vendor_id" in tool_input or "vendor_name" in tool_input:
        detail = f" [{tool_input.get('vendor_id') or tool_input.get('vendor_name')}]"
    elif "template_id" in tool_input:
        detail = f" [{tool_input['template_id']}]"
    elif "platform_id" in tool_input:
        detail = f" [{tool_input['platform_id']}]"
    print(f"  ⟳ {label}{detail}", flush=True)


def main() -> None:
    print(BANNER)

    try:
        agent = OrchestratorAgent(db_path=DB_PATH)
    except EnvironmentError as e:
        print(f"\n  FEIL: {e}\n")
        print("  Sett API-nøkkel og prøv igjen:")
        print("    export ANTHROPIC_API_KEY=din_nøkkel\n")
        sys.exit(1)

    while True:
        try:
            user_input = input("\nDu: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n  Avslutter. Ha en god arbeidsdag!\n")
            sys.exit(0)

        if not user_input:
            continue

        lower = user_input.lower()

        if lower in ("avslutt", "exit", "quit", "q"):
            print("\n  Avslutter. Ha en god arbeidsdag!\n")
            sys.exit(0)

        if lower in ("ny samtale", "reset", "ny", "start på nytt"):
            agent.reset()
            print("\n  Samtalehistorikk slettet. Klar for ny sesjon.\n")
            continue

        if lower == "hjelp" or lower == "eksempler":
            print(EKSEMPLER)
            continue

        # Run the agent — tool calls are shown as progress indicators
        print()
        response = agent.chat(user_input, on_tool_call=on_tool_call)
        print(f"\nAgent: {response}\n")
        print("──────────────────────────────────────────────────────────────────")


if __name__ == "__main__":
    main()
