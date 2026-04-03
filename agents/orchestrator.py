"""
OrchestratorAgent — the core of the Equinor Rotating Equipment Agent System.

This is a real AI agent: Claude receives the user's request, decides which
tools to call (and in what order), reads the results, and formulates a response
in Norwegian. There is no hardcoded routing or keyword matching.

The agentic loop continues until Claude has gathered all the information it needs
and is ready to give a complete answer.
"""

import os
import json
import anthropic
from typing import Optional
from tools.agent_tools import TOOL_DEFINITIONS, execute_tool


SYSTEM_PROMPT = """\
Du er en AI-assistent for Equinors vedlikeholdsavdeling for roterende utstyr (PSR-avdelingen).
Du hjelper med planlegging, koordinering og oppfølging av vedlikeholdsjobber på store roterende
maskiner på Equinors offshore-plattformer i Nordsjøen og Norskehavet.

Du har tilgang til databaser via verktøy (tools). Bruk disse til å hente faktainformasjon
før du svarer — aldri gjett eller dikte opp tekniske data, personnavn eller datoer.

Databasene inneholder:
- Roterende utstyr: kompressorer (PCL804, MCL606, BCL505), gassturbiner (SGT-600, SGT-500, Mars 100), pumper
- Plattformer: Troll A, Gullfaks C, Snorre B, Johan Sverdrup PII, Åsgard B
- Leverandører: Baker Hughes/Nuovo Pignone, Siemens Energy, MAN Energy Solutions, Flowserve, John Crane, SKF
- SAP-arbeidsordre (PM01/PM02/PM03), Safran-aktiviteter
- Reservedeler med lagerstatus og ledetider
- Personell med sertifikatstatus (GWO, BOSIET, H2S)
- Standardiserte jobbmaler med aktivitetslister og bemanningskrav

Slik jobber du:
1. Les brukerens forespørsel nøye
2. Kall relevante verktøy for å hente faktainformasjon — start alltid med utstyrsoppslag
3. Kall gjerne flere verktøy i rekkefølge basert på hva du finner
4. Sett sammen et strukturert, profesjonelt svar på norsk bokmål
5. Bruk korrekt fagspråk: overhaul, bundleskifte, boreskopinspeksjon, tettingsbytte,
   POB, hastegrad, SAP PM01/PM02/PM03, Safran, LOTO, PTW

Når du planlegger en vedlikeholdsjobb:
- Slå alltid opp utstyret og sjekk driftstimer vs. overhaul-intervall
- Hent de siste arbeidsordre for historisk kontekst
- Sjekk reservedelsstatus for kritiske deler i jobbtemplaten
- Beregn tidsplan (start, slutt, mob-frist for leverandør)
- Sjekk sertifikatstatus for relevant personell
- Informer om leverandørkontakt og rammekontrakt

Når du håndterer en leverandørforsinkelse:
- Finn berørt arbeidsordre
- Beregn revidert tidsplan med de nye datoene
- Skriv en profesjonell norsk e-post med formell forsinkelsesbekreftelse
- Inkluder krav om skriftlig RCA og eskaleringsplan fra leverandøren
- Henvis til rammekontrakten

Svar alltid på norsk bokmål. Vær konkret og handlingsorientert.
Formater svar med klare seksjoner og overskrifter der det er nyttig.
"""


class OrchestratorAgent:
    """
    AI agent that uses Claude with tool_use to answer questions about
    rotating equipment maintenance. Claude decides what to look up and
    how to respond — no hardcoded logic.
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY mangler. "
                "Sett miljøvariabelen: export ANTHROPIC_API_KEY=din_nøkkel"
            )
        self.client = anthropic.Anthropic(api_key=api_key)
        self.conversation_history: list[dict] = []

    def chat(
        self,
        user_message: str,
        on_tool_call: Optional[callable] = None,
    ) -> str:
        """
        Send a message to the agent and get a response.

        Args:
            user_message: The user's question or instruction in any language.
            on_tool_call: Optional callback called when Claude uses a tool,
                          receives (tool_name, tool_input) — used to show progress.

        Returns:
            The agent's response as a string (in Norwegian).
        """
        self.conversation_history.append({"role": "user", "content": user_message})
        messages = list(self.conversation_history)

        while True:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                # Claude is done — extract the text response
                text = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        text = block.text
                        break
                # Save to conversation history for multi-turn support
                self.conversation_history.append(
                    {"role": "assistant", "content": response.content}
                )
                return text

            if response.stop_reason == "tool_use":
                # Claude wants to call one or more tools
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        # Notify caller so the demo can print progress
                        if on_tool_call:
                            on_tool_call(block.name, block.input)

                        # Execute the tool and get results
                        result_json = execute_tool(self.db_path, block.name, block.input)
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result_json,
                            }
                        )

                # Feed tool results back to Claude and continue the loop
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})

    def reset(self) -> None:
        """Clear conversation history to start a new session."""
        self.conversation_history = []
