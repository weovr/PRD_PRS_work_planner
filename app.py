"""
Equinor PSR — Roterende Utstyr AI Agent
Kjør: streamlit run app.py
"""

import os
import json
import streamlit as st
import anthropic
from tools import TOOLS, run_tool

# ── Page setup ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Equinor PSR Agent",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .tool-badge {
        background: #f0f4f8; border-left: 3px solid #e63329;
        padding: 6px 12px; border-radius: 4px;
        font-size: 0.85em; color: #444; margin: 4px 0;
    }
    .stChatMessage { border-bottom: 1px solid #f0f0f0; }
</style>
""", unsafe_allow_html=True)

# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM = """\
Du er en AI-assistent for Equinors PSR-avdeling (roterende utstyr offshore).
Du hjelper med planlegging, koordinering og oppfølging av vedlikeholdsjobber
for kompressorer, gassturbiner og pumper på Equinors offshore-plattformer.

Du har tilgang til Equinors vedlikeholdsdatabaser via verktøy. Slå alltid opp
faktainformasjon fra databasen — aldri gjett tekniske data eller datoer.

Databaser du har tilgang til:
- Utstyr: K-3101, K-3102, K-4201, K-5301, K-7101, K-8101, K-8102,
          GT-3101A, GT-3101B, GT-4201, GT-5401, P-6101, P-6102, P-9201, P-9202
- Plattformer: Troll A, Gullfaks C, Snorre B, Johan Sverdrup PII, Åsgard B
- Leverandører: Baker Hughes/Nuovo Pignone (BH-NP), Siemens Energy (SE),
                MAN Energy Solutions (MAN-ES), Flowserve (FS), John Crane (JC), SKF
- SAP arbeidsordre (PM01/PM02/PM03), reservedeler, personell og sertifikater
- Jobbmaler: bundleskifte, boreskopinspeksjon, hot section overhaul, tettingsbytte, lagerbytte, pumperevisjon

Slik jobber du ved jobbplanlegging:
1. Slå opp utstyret — forstå teknisk status og driftstimer
2. Sjekk vedlikeholdshistorikken — hva er gjort tidligere?
3. Sjekk reservedelsstatus — er kritiske deler på lager?
4. Hent riktig jobbmal — aktivitetsliste og bemanningskrav
5. Beregn tidsplan — oppstart, ferdig, mob-frist for leverandør
6. Sjekk sertifikater for relevant personell
7. Informer om leverandørkontakt og rammekontrakt
8. Skriv mobiliseringsforespørsel til leverandøren hvis ønskelig

Ved leverandørforsinkelse:
- Finn berørt arbeidsordre og beregn revidert tidsplan
- Skriv formell forsinkelsesbekreftelse med krav om RCA og eskaleringsplan
- Henvis alltid til rammekontrakten

Svar alltid på norsk bokmål med korrekt fagspråk:
POB, SAP PM01/PM02/PM03, Safran, overhaul, bundleskifte, boreskop,
tettingsbytte, LOTO, PTW, hastegrad, komplettscore.
Vær konkret, strukturert og handlingsorientert.
"""

TOOL_LABELS = {
    "get_equipment":             "Slår opp utstyrsinformasjon",
    "get_maintenance_history":   "Henter vedlikeholdshistorikk",
    "get_open_work_orders":      "Henter åpne arbeidsordre",
    "get_vendor":                "Slår opp leverandørinformasjon",
    "get_spare_parts":           "Sjekker reservedelsstatus",
    "get_job_template":          "Henter jobbmal",
    "get_personnel":             "Sjekker personell og sertifikater",
    "beregn_tidslinje":          "Beregner jobbplan og tidsfrister",
    "beregn_revidert_tidslinje": "Beregner revidert tidsplan",
}

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚙️ Equinor PSR Agent")
    st.caption("Roterende utstyr — vedlikeholdsplanlegging")
    st.divider()

    api_key = os.environ.get("ANTHROPIC_API_KEY") or st.text_input(
        "Anthropic API-nøkkel", type="password", placeholder="sk-ant-..."
    )

    st.divider()
    st.markdown("**Eksempelspørsmål**")

    examples = [
        "Planlegg bundleskifte K-3101 Troll A, oppstart 1. september 2026",
        "Hva er statusen på GT-4201 på Gullfaks C?",
        "Hvilke arbeidsordre er åpne nå?",
        "Baker Hughes melder 21 dagers forsinkelse på bundle til K-3101",
        "Skriv mobiliseringsforespørsel til Siemens Energy for GT-4201",
        "Sjekk sertifikatstatus for bemanningen på Troll A",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True, key=ex):
            st.session_state.queued_message = ex

    st.divider()
    if st.button("🗑️ Ny samtale", use_container_width=True):
        st.session_state.messages = []
        st.session_state.api_messages = []
        st.rerun()

    st.caption("⚠️ Kun demonstrasjonsdata — ikke tilknyttet Equinors systemer.")

# ── Main chat ─────────────────────────────────────────────────────────────────

st.markdown("### 💬 Spør om vedlikehold, utstyr eller leverandører")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "api_messages" not in st.session_state:
    st.session_state.api_messages = []

# Render chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("tools_used"):
            with st.expander(f"🔧 Agenten brukte {len(msg['tools_used'])} verktøy"):
                for t in msg["tools_used"]:
                    st.markdown(f'<div class="tool-badge">📋 {t}</div>', unsafe_allow_html=True)

# Get input (from sidebar button or chat input)
user_input = st.session_state.pop("queued_message", None) or st.chat_input(
    "Skriv spørsmålet ditt her..."
)

if user_input:
    if not api_key:
        st.error("Legg inn Anthropic API-nøkkel i sidepanelet for å bruke agenten.")
        st.stop()

    # Show user message
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.api_messages.append({"role": "user", "content": user_input})

    # Run the agent
    with st.chat_message("assistant"):
        status = st.empty()
        tools_used = []
        client = anthropic.Anthropic(api_key=api_key)
        messages = list(st.session_state.api_messages)

        # Agentic loop — Claude decides what to do
        while True:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=SYSTEM,
                tools=TOOLS,
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                status.empty()
                text = next((b.text for b in response.content if hasattr(b, "text")), "")
                st.markdown(text)
                if tools_used:
                    with st.expander(f"🔧 Agenten brukte {len(tools_used)} verktøy"):
                        for t in tools_used:
                            st.markdown(f'<div class="tool-badge">📋 {t}</div>', unsafe_allow_html=True)
                # Save to history
                st.session_state.api_messages.append({"role": "assistant", "content": response.content})
                st.session_state.messages.append({"role": "assistant", "content": text, "tools_used": tools_used})
                break

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        label = TOOL_LABELS.get(block.name, block.name)
                        # Show what the agent is doing right now
                        detail = ""
                        if "tag" in block.input:
                            detail = f" — {block.input['tag']}"
                        elif "søk" in block.input:
                            detail = f" — {block.input['søk']}"
                        elif "mal" in block.input:
                            detail = f" — {block.input['mal']}"
                        status.info(f"⟳ {label}{detail}...")
                        tools_used.append(f"{label}{detail}")
                        result = run_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
