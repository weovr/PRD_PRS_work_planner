# CLAUDE.md — Equinor Rotating Equipment Agent System

## Project Purpose

Build a multi-agent demonstration system in Python that shows how AI agents can collaborate to plan, coordinate, and follow up on maintenance jobs for **large rotating equipment** on Equinor offshore platforms. The system uses realistic dummy data modelled on real Equinor operations (compressors, gas turbines, pumps), with vendors like Baker Hughes / Nuovo Pignone, Siemens Energy, and MAN Energy Solutions.

This is a **concept demonstration** — the database is file-based (JSON), there is no live connection to SAP, Safran, or any Equinor system. All data is fictional but domain-realistic.

---

## Repository Structure

Create the following folder and file layout:

```
equinor-rotating-equipment-agents/
│
├── CLAUDE.md                        ← this file
├── README.md                        ← project overview and how to run
├── requirements.txt                 ← Python dependencies
│
├── agents/
│   ├── __init__.py
│   ├── orchestrator.py              ← master agent that routes tasks
│   ├── planning_agent.py            ← job session planning
│   ├── equipment_agent.py           ← equipment lookup, history, specs
│   ├── vendor_agent.py              ← vendor coordination and follow-up
│   ├── execution_agent.py           ← job progress and daily reports
│   └── safety_agent.py             ← PTW, risk assessment checks
│
├── database/
│   ├── equipment.json               ← equipment master list
│   ├── platforms.json               ← Equinor platform data
│   ├── vendors.json                 ← vendor contacts and lead times
│   ├── work_orders.json             ← SAP-style work order history
│   ├── job_templates.json           ← standard job packages per equipment type
│   ├── spare_parts.json             ← critical spare parts inventory
│   └── personnel.json               ← crew competency and certifications
│
├── tools/
│   ├── __init__.py
│   ├── db_reader.py                 ← shared utility to read/write JSON database
│   ├── report_generator.py          ← generates status reports as text output
│   └── email_drafter.py             ← drafts vendor follow-up emails
│
├── scenarios/
│   ├── scenario_01_bundle_change.py ← full compressor bundle replacement workflow
│   ├── scenario_02_gt_inspection.py ← gas turbine borescope inspection
│   └── scenario_03_vendor_delay.py  ← vendor delivery delay and re-planning
│
└── demo/
    ├── run_demo.py                  ← interactive CLI demo entry point
    └── demo_output_examples/        ← pre-generated output examples (text files)
```

---

## Technology Stack

- **Language**: Python 3.11+
- **Agent framework**: Plain Python classes (no LangChain or external agent libraries — keep it readable and deterministic)
- **Database**: JSON files (no SQL, no external database)
- **LLM calls**: Use the Anthropic Python SDK (`anthropic`) for agents that need language generation (email drafting, report summaries). Use `claude-sonnet-4-20250514`.
- **CLI interface**: Use Python's built-in `input()` and `print()` — no external CLI frameworks

Install dependencies:
```
anthropic>=0.25.0
```

---

## Database: Realistic Equinor Domain Data

Build all JSON files with realistic, domain-accurate dummy data. Use the field names and terminology that Equinor operations teams would recognize.

### `database/platforms.json`

Include at least 5 platforms:

| Platform | Type | Location | Operator area |
|----------|------|----------|---------------|
| Troll A | Semi-submersible | North Sea | Hordaland |
| Gullfaks C | Concrete GBS | North Sea | Rogaland |
| Snorre B | Semi-submersible | North Sea | Rogaland |
| Johan Sverdrup PII | Fixed jacket | North Sea | Rogaland |
| Åsgard B | Semi-submersible | Norwegian Sea | Møre |

Fields per platform:
```json
{
  "platform_id": "TROLL-A",
  "name": "Troll A",
  "type": "Semi-submersible",
  "area": "Hordaland",
  "pob_limit": 450,
  "helideck_capacity": 19,
  "maintenance_contact": "Hans Erik Larsen",
  "contact_email": "hel@equinor.com"
}
```

---

### `database/equipment.json`

Include at least 15 pieces of large rotating equipment across the platforms. Use realistic equipment tag numbers (Norwegian convention: platform prefix + equipment type code + number).

Equipment types to cover:
- **Kompressorer** (gas compressors): K-3101, K-3102, K-4201, K-5301
- **Gassturbiner** (gas turbines/drivers): GT-3101A, GT-3101B, GT-4201
- **Injeksjonspumper** (injection pumps): P-6101, P-6102
- **Brannvannspumper** (firewater pumps): P-9201, P-9202
- **Hjelpekompressorer** (utility compressors): K-8101, K-8102

Fields per equipment item:
```json
{
  "tag": "K-3101",
  "platform_id": "TROLL-A",
  "description": "Eksportkompressor 1. trinn",
  "type": "Sentrifugalkompressor",
  "manufacturer": "Baker Hughes / Nuovo Pignone",
  "model": "PCL804/S",
  "serial_number": "NP-2004-0817",
  "installation_year": 2005,
  "design_pressure_bar": 185,
  "design_flow_mmsm3d": 12.5,
  "driver_tag": "GT-3101A",
  "driver_type": "Solar Turbines Mars 100",
  "last_overhaul": "2022-09-14",
  "next_planned_overhaul": "2026-09-01",
  "running_hours": 42800,
  "oh_interval_hours": 48000,
  "criticality": "Safety Critical",
  "sap_equipment_id": "10023456",
  "maintenance_strategy": "TBM",
  "vendor_frame_agreement": "Baker Hughes FA-2024-NP-001"
}
```

---

### `database/vendors.json`

Include at least 6 vendors with realistic contact information and lead times:

| Vendor | Speciality | Frame Agreement |
|--------|-----------|-----------------|
| Baker Hughes / Nuovo Pignone | Centrifugal compressors, gas turbines | Yes |
| Siemens Energy | Gas turbines (SGT-series), generators | Yes |
| MAN Energy Solutions | Reciprocating compressors | Yes |
| Flowserve | Pumps and seals | Yes |
| John Crane | Mechanical seals | Yes |
| SKF | Bearings and condition monitoring | Yes |

Fields per vendor:
```json
{
  "vendor_id": "BH-NP",
  "name": "Baker Hughes / Nuovo Pignone",
  "short_name": "BHNP",
  "contact_person": "Marco Rossi",
  "contact_email": "marco.rossi@bakerhughes.com",
  "contact_phone": "+39 055 423 211",
  "technical_contact": "Lars Isaksen",
  "technical_email": "lars.isaksen@bakerhughes.com",
  "country": "Italy / Norway",
  "lead_time_days_standard": 90,
  "lead_time_days_critical": 30,
  "frame_agreement_id": "FA-2024-NP-001",
  "frame_agreement_expiry": "2027-12-31",
  "specialities": ["Sentrifugalkompressorer", "Gassturbiner", "Bundle-overhaul"],
  "mob_time_days": 14
}
```

---

### `database/work_orders.json`

Include at least 20 historical work orders across platforms. Use SAP-style structure with Norwegian field labels:

```json
{
  "wo_number": "10456789",
  "wo_type": "PM02",
  "description": "Bundle-skifte K-3101 - 48000t overhaul",
  "platform_id": "TROLL-A",
  "equipment_tag": "K-3101",
  "sap_equipment_id": "10023456",
  "priority": "Haster",
  "status": "TECO",
  "start_date": "2022-09-01",
  "finish_date": "2022-09-14",
  "planned_hours": 480,
  "actual_hours": 512,
  "vendor": "BH-NP",
  "technicians_vendor": 4,
  "technicians_equinor": 2,
  "pob_days": 14,
  "cost_nok": 3800000,
  "work_description": "Fullstendig bundleskifte inkl. lager, tetninger og alignment. Balansering av ny bundle offshore.",
  "findings": "Lager BA konstatert slitt. Sekundærtetting OK. Ny bundle installert og alignert.",
  "completion_notes": "Jobb utført i henhold til plan. Maskinen startet uten avvik.",
  "safran_activity_id": "ACT-2022-K3101-OH"
}
```

Work order types to include:
- **PM01**: Preventiv vedlikehold (planned preventive)
- **PM02**: Korrektivt vedlikehold (corrective)
- **PM03**: Inspeksjon (inspection)

Status codes: `CRTD`, `REL`, `PCNF`, `CNF`, `TECO`, `CLSD`

---

### `database/job_templates.json`

Include standard job packages for the most common overhaul types. These are deterministic checklists — not AI-generated. Each template has:

- Required vendor technicians
- Required Equinor personnel
- Estimated POB-days
- Required spare parts list
- Mandatory documentation
- PTW requirements
- Typical sequence of activities

Example templates to include:
1. `bundle_change_centrifugal_compressor` — Sentrifugalkompressor bundleskifte
2. `gt_borescope_inspection` — Gassturbine boreskopinspeksjon
3. `gt_hot_section_overhaul` — Gassturbine hot section overhaul
4. `seal_replacement_centrifugal` — Tettingsbytte sentrifugalkompressor
5. `bearing_replacement` — Lagerbytte roterende utstyr
6. `pump_overhaul` — Pumperevisjon

---

### `database/spare_parts.json`

Include at least 30 spare parts entries. Each part must have:

```json
{
  "part_id": "NP-BDL-PCL804-001",
  "description": "Komplett bundle PCL804/S",
  "equipment_tags": ["K-3101", "K-3102"],
  "vendor_id": "BH-NP",
  "part_number_vendor": "NP-PCL804-BDL-S-2022",
  "lead_time_days": 120,
  "unit_price_nok": 2800000,
  "stock_location": "Equinor Mongstad base",
  "stock_quantity": 1,
  "reorder_level": 1,
  "last_used": "2022-09-14",
  "criticality": "Kritisk"
}
```

---

### `database/personnel.json`

Include at least 15 personnel entries (mix of Equinor and vendor):

```json
{
  "person_id": "EQ-HAL-001",
  "name": "Håkon Andreassen",
  "company": "Equinor",
  "role": "Disiplinleder Roterende",
  "platform_id": "TROLL-A",
  "certifications": ["GWO Basic Safety", "NOGEPA", "H2S", "BOSIET"],
  "cert_expiry": {
    "GWO": "2026-11-15",
    "BOSIET": "2027-03-22"
  },
  "competencies": ["Sentrifugalkompressorer", "Gassturbiner", "Alignment"],
  "vendor_personnel": false,
  "currently_offshore": true,
  "current_platform": "TROLL-A"
}
```

---

## Agent Specifications

Each agent is a Python class with a clear, deterministic `run()` method. Agents call each other through the orchestrator — they do not call each other directly.

### `agents/orchestrator.py` — OrchestratorAgent

This is the entry point. It receives a user request as a plain text string, determines which agents to activate and in what order, and returns a structured response.

```python
class OrchestratorAgent:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.agents = {
            "planning": PlanningAgent(db_path),
            "equipment": EquipmentAgent(db_path),
            "vendor": VendorAgent(db_path),
            "execution": ExecutionAgent(db_path),
            "safety": SafetyAgent(db_path)
        }

    def run(self, user_request: str) -> dict:
        # Parse intent from user_request
        # Route to appropriate agents
        # Collect and assemble results
        # Return structured output dict
        pass
```

The orchestrator must handle these intents:
- `plan_job` — create a job session plan for a given equipment tag and job type
- `check_equipment` — look up equipment specs, history, and current status
- `check_vendor` — look up vendor availability, frame agreement, lead times
- `check_parts` — verify spare parts availability for a job
- `draft_vendor_email` — draft a coordination email to a vendor
- `execution_status` — report on active or recent work orders
- `check_crew` — verify crew certifications and availability

---

### `agents/planning_agent.py` — PlanningAgent

Creates a complete job session plan based on:
- Equipment tag and job type
- Platform POB limit
- Vendor mobilization time
- Spare parts availability
- Crew availability and certifications

Output format (always deterministic, based on templates and database):

```python
{
  "job_id": "JOB-2026-K3101-001",
  "title": "Bundle-skifte K-3101, Troll A",
  "equipment_tag": "K-3101",
  "platform": "Troll A",
  "job_type": "bundle_change_centrifugal_compressor",
  "proposed_start": "2026-09-01",
  "proposed_finish": "2026-09-15",
  "pob_days": 15,
  "crew_required": {
    "equinor_technicians": 2,
    "vendor_technicians": 4,
    "discipline_lead": 1
  },
  "vendor": "Baker Hughes / Nuovo Pignone",
  "vendor_mob_deadline": "2026-08-15",
  "critical_parts": ["NP-BDL-PCL804-001"],
  "parts_status": "På lager — Mongstad",
  "ptw_type": "Hot Work + Confined Space",
  "safran_activity": "ACT-2026-K3101-OH",
  "sap_wo_type": "PM02",
  "estimated_cost_nok": 4200000,
  "risk_level": "Høy",
  "activities": [
    "1. Avslutning og isolering",
    "2. Åpning og inspeksjon",
    "3. Utfjerning av gammel bundle",
    "4. Installasjon av ny bundle",
    "5. Alignment og mekanisk ferdigstillelse",
    "6. Tetthetsprøving",
    "7. Oppstart og driftsverifikasjon"
  ]
}
```

---

### `agents/equipment_agent.py` — EquipmentAgent

Looks up equipment from the database and returns:
- Current technical specs
- Maintenance history (last 5 work orders)
- Running hours vs. overhaul interval
- Next planned maintenance
- Associated spare parts

---

### `agents/vendor_agent.py` — VendorAgent

Handles all vendor-related queries:
- Look up vendor frame agreement and contact info
- Calculate mobilization deadlines based on job start date
- Check lead times for required parts
- Draft follow-up / coordination emails using the Anthropic API

For email drafting, call the Anthropic API with a structured prompt that includes: vendor name, contact person, job description, equipment tag, platform, required mobilization date, and frame agreement reference. The email should be professional, written in English, and reference the frame agreement number.

---

### `agents/execution_agent.py` — ExecutionAgent

Tracks ongoing and recently completed jobs:
- List open work orders (status not TECO or CLSD)
- Flag work orders that are overdue
- Calculate actual vs. planned hours
- Generate daily status report text

---

### `agents/safety_agent.py` — SafetyAgent

Validates safety prerequisites before a job can be planned:
- Checks crew certifications vs. expiry dates
- Confirms required PTW types for job template
- Flags any certifications expiring within 60 days of the job
- Returns a pass/fail status with details

---

## Scenarios

Build three runnable scenario scripts. Each script imports the OrchestratorAgent and runs a complete end-to-end workflow, printing the result step by step to the console.

### `scenarios/scenario_01_bundle_change.py`

Full workflow for planning a compressor bundle change on Troll A:

1. User request: `"Planlegg bundleskifte K-3101 Troll A, oppstart 1. september 2026"`
2. Orchestrator routes to: EquipmentAgent → PlanningAgent → SafetyAgent → VendorAgent
3. Equipment agent: fetches K-3101 specs and last overhaul history
4. Planning agent: creates full job plan from `bundle_change_centrifugal_compressor` template
5. Safety agent: validates crew certs for proposed crew
6. Vendor agent: drafts mobilization request email to Baker Hughes
7. Final output: full job plan + vendor email printed to console

Print each agent's intermediate output clearly labelled, so the user can follow the workflow.

---

### `scenarios/scenario_02_gt_inspection.py`

Borescope inspection workflow for a gas turbine on Gullfaks C:

1. User request: `"Planlegg boreskopinspeksjon GT-4201 Gullfaks C"`
2. Equipment agent: fetches GT-4201 data
3. Planning agent: creates inspection plan
4. Safety agent: verifies certifications
5. Output: inspection plan with Siemens Energy contact and required personnel

---

### `scenarios/scenario_03_vendor_delay.py`

Vendor delay scenario and re-planning:

1. Starting state: Job `JOB-2026-K3101-001` is in progress, vendor informs of 3-week delivery delay for spare part
2. Orchestrator receives: `"Baker Hughes melder 21 dagers forsinkelse på bundle NP-BDL-PCL804-001"`
3. Execution agent: finds affected work order
4. Planning agent: recalculates timeline, new proposed dates
5. Vendor agent: drafts formal delay notification acknowledgment and escalation email
6. Output: revised job plan + two draft emails

---

## Demo Entry Point

`demo/run_demo.py` — an interactive CLI script that lets the user pick which scenario to run, or type a free-text request:

```
===================================================
  EQUINOR — Roterende Utstyr Agent System (Demo)
===================================================

Velg ett av følgende scenarioer:
  [1] Planlegg bundleskifte K-3101, Troll A
  [2] Planlegg boreskopinspeksjon GT-4201, Gullfaks C
  [3] Leverandørforsinkelse og replanning
  [4] Egendefinert forespørsel (fritekst)

Ditt valg:
```

After the user picks a scenario, run it and print all agent outputs with clear section headers.

---

## README.md Requirements

Write a clear README that includes:

1. **What this is**: A concept demonstration of multi-agent AI for offshore rotating equipment maintenance
2. **What it demonstrates**: Agent orchestration, job planning, vendor coordination, equipment database lookup
3. **Disclaimer**: Uses dummy data only — not connected to any Equinor system
4. **How to install**: `pip install -r requirements.txt`, set `ANTHROPIC_API_KEY` environment variable
5. **How to run**: `python demo/run_demo.py`
6. **Agent overview**: Brief description of each agent's role
7. **Equipment types covered**: List of rotating equipment categories

---

## Code Quality Rules

Follow these rules throughout the entire codebase:

1. **Determinism first**: All planning logic, database lookups, and calculations must be deterministic (same input → same output, always). Only `VendorAgent.draft_email()` and `ExecutionAgent.summarize_findings()` may call the Anthropic API.

2. **No hallucination of data**: Agents must only return data that exists in the JSON database. If equipment is not found, return a clear `{"status": "not_found", "message": "Utstyr ikke funnet: X"}`.

3. **Norwegian labels, English code**: Variable names and code in English. User-facing output text in Norwegian (nynorsk/bokmål). Comments in English.

4. **Clear output structure**: Every agent `run()` method returns a Python dict with at least `{"status": "ok"|"error", "agent": "agent_name", "data": {...}}`.

5. **Error handling**: Every file read must handle `FileNotFoundError` and `json.JSONDecodeError` gracefully.

6. **No circular imports**: Agents import from `tools/` only. Orchestrator imports from `agents/`. No agent imports another agent.

7. **Type hints**: Use Python type hints on all function signatures.

---

## Equinor Terminology in Output

When printing to console, use these conventions to match Equinor operations language:
- Headers: use `=` underlines for top-level sections, `-` for sub-sections
- Use the term **"Roterende utstyr"** for large rotating equipment
- Reference SAP work order types: PM01, PM02, PM03
- Reference Safran for project scheduling
- Reference POB (Personnel on Board) for offshore crew tracking
- Use Norwegian terminology throughout: hastegrad, komplettscore, vedlikehold, overhaul, boreskop, tettingsbytte, bundle-skifte

---

## Anthropic API Usage

Only two functions use the Anthropic API:

**1. `VendorAgent.draft_email()`**

System prompt:
```
You are an expert offshore maintenance coordinator at Equinor.
Draft a professional vendor coordination email in English.
Be concise and specific. Include: frame agreement reference,
equipment tag, platform name, required mobilization date,
and a clear action request. Do not use bullet points in the email body.
```

**2. `ExecutionAgent.summarize_findings()`**

System prompt:
```
You are an offshore maintenance engineer at Equinor.
Summarize the work order findings and completion notes in 2-3 sentences.
Write in Norwegian (bokmål). Be factual and technical.
```

Both functions must handle API errors gracefully and fall back to a template-based output if the API call fails.

---

## Validation Before Delivery

Before the repository is complete, verify:

- [ ] All JSON database files load without errors
- [ ] All three scenarios run end-to-end without exceptions
- [ ] `demo/run_demo.py` runs and accepts user input
- [ ] Equipment tags in `work_orders.json` match tags in `equipment.json`
- [ ] Vendor IDs in `work_orders.json` match IDs in `vendors.json`
- [ ] Platform IDs are consistent across all database files
- [ ] At least one certification expiry warning is triggered in `scenario_01`
- [ ] The vendor delay scenario produces a revised timeline with new dates
- [ ] README.md is complete and accurate
