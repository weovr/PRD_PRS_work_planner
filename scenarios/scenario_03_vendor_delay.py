"""
Scenario 03 — Leverandørforsinkelse og replanning

Baker Hughes melder 21 dagers forsinkelse på bundledel til K-3101.
Agenten finner berørt arbeidsordre, beregner ny tidsplan og skriver
formelle e-poster til leverandøren.

Kjør: python scenarios/scenario_03_vendor_delay.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator import OrchestratorAgent

DB_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TOOL_LABELS = {
    "get_equipment":              "Slår opp utstyrsinformasjon...",
    "get_work_order_history":     "Henter arbeidsordrehistorikk...",
    "get_open_work_orders":       "Henter åpne arbeidsordre...",
    "get_vendor":                 "Slår opp leverandørinformasjon...",
    "get_spare_parts":            "Sjekker reservedelsstatus...",
    "get_job_template":           "Henter jobbmal og sjekkliste...",
    "get_platform":               "Henter plattforminformasjon...",
    "get_personnel":              "Sjekker personell og sertifikater...",
    "calculate_job_timeline":     "Beregner jobbplan og tidsfrister...",
    "calculate_revised_timeline": "Beregner revidert tidsplan...",
}


def on_tool_call(tool_name: str, tool_input: dict) -> None:
    label = TOOL_LABELS.get(tool_name, f"Kaller: {tool_name}...")
    detail = ""
    if "tag" in tool_input:
        detail = f" [{tool_input['tag']}]"
    elif "vendor_id" in tool_input or "vendor_name" in tool_input:
        detail = f" [{tool_input.get('vendor_id') or tool_input.get('vendor_name')}]"
    print(f"  ⟳ {label}{detail}", flush=True)


def main():
    print("=" * 66)
    print("  EQUINOR — Scenario 03: Leverandørforsinkelse og replanning")
    print("=" * 66)

    forespørsel = (
        "Baker Hughes melder 21 dagers forsinkelse på bundle NP-BDL-PCL804-001 "
        "til K-3101 på Troll A. Opprinnelig planlagt oppstart var 1. september 2026. "
        "Beregn revidert tidsplan og skriv to formelle e-poster: "
        "én forsinkelsesbekreftelse til kontaktpersonen hos Baker Hughes, "
        "og én eskalering til teknisk kontakt med krav om RCA og eskaleringsplan. "
        "Henvis til rammekontrakten."
    )

    print(f"\n  Forespørsel: \"{forespørsel}\"\n")
    print("  Agenten arbeider...")
    print("-" * 66)

    try:
        agent = OrchestratorAgent(db_path=DB_PATH)
    except EnvironmentError as e:
        print(f"\n  FEIL: {e}\n")
        sys.exit(1)

    response = agent.chat(forespørsel, on_tool_call=on_tool_call)
    print()
    print(response)
    print("\n" + "=" * 66)


if __name__ == "__main__":
    main()
