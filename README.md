# Equinor Rotating Equipment Agent System

## What This Is

A concept demonstration of a **multi-agent AI system** for planning, coordinating, and following up on maintenance jobs for large rotating equipment on Equinor offshore platforms.

The system shows how specialized AI agents can collaborate to handle realistic offshore maintenance workflows — from job planning and vendor coordination to safety checks and delay management.

> **Disclaimer**: This system uses **fictional dummy data** modelled on real Equinor operations. It has **no connection** to any Equinor system (SAP, Safran, or otherwise). All equipment tags, personnel, work orders, and vendor contacts are fabricated for demonstration purposes only.

---

## What It Demonstrates

- **Multi-agent orchestration**: A master OrchestratorAgent routes requests to specialist agents and assembles structured results
- **Deterministic job planning**: Job plans are built from standardized templates and database lookups — no hallucination
- **Vendor coordination**: Lead time checks, mobilization deadline calculation, and professional email drafting (via Anthropic Claude API)
- **Safety validation**: Crew certification checks with expiry warnings against job start dates
- **Execution tracking**: Open work order monitoring with overdue flagging
- **Vendor delay handling**: Timeline recalculation and escalation email drafting when delivery delays occur
- **Realistic domain data**: Equipment tags, SAP work order types, Safran activity IDs, Norwegian offshore terminology

---

## Agent Overview

| Agent | Role |
|-------|------|
| **OrchestratorAgent** | Parses user intent, routes to specialist agents, assembles results |
| **EquipmentAgent** | Looks up equipment specs, maintenance history, running hours, spare parts |
| **PlanningAgent** | Creates complete job plans from templates; recalculates timelines after delays |
| **VendorAgent** | Looks up vendors, checks lead times, drafts mobilization and delay emails |
| **SafetyAgent** | Validates crew certifications, flags expiring certs, confirms PTW requirements |
| **ExecutionAgent** | Tracks open/overdue work orders, generates daily status summaries |

---

## Equipment Types Covered

- **Sentrifugalkompressorer** (Centrifugal compressors): Baker Hughes / Nuovo Pignone PCL804, MCL606, BCL505
- **Gassturbiner** (Gas turbines): Siemens Energy SGT-600, SGT-500; Solar Turbines Mars 100
- **Injeksjonspumper** (Injection pumps): Flowserve DVMX series
- **Brannvannspumper** (Firewater pumps): Flowserve LNN series
- **Hjelpekompressorer** (Utility compressors): MAN Energy Solutions L-type reciprocating

---

## Platforms

| Platform | Type | Area |
|----------|------|------|
| Troll A | Semi-submersible | Hordaland |
| Gullfaks C | Concrete GBS | Rogaland |
| Snorre B | Semi-submersible | Rogaland |
| Johan Sverdrup PII | Fixed jacket | Rogaland |
| Åsgard B | Semi-submersible | Møre |

---

## How to Install

1. **Clone or download the repository**

2. **Install Python dependencies** (Python 3.11+ required):
   ```bash
   pip install -r requirements.txt
   ```

3. **Set the Anthropic API key** (optional — enables AI-generated emails and summaries):
   ```bash
   export ANTHROPIC_API_KEY=your_api_key_here
   ```
   Without the API key, the system uses template-based emails and summaries (fully functional).

---

## How to Run

### Interactive demo

```bash
python demo/run_demo.py
```

Select a scenario from the menu:
- **[1]** Bundle change K-3101, Troll A
- **[2]** Borescope inspection GT-4201, Gullfaks C
- **[3]** Vendor delay and replanning
- **[4]** Equipment status check (interactive)
- **[5]** Show all open work orders
- **[6]** Free-text request

### Run individual scenarios

```bash
python scenarios/scenario_01_bundle_change.py
python scenarios/scenario_02_gt_inspection.py
python scenarios/scenario_03_vendor_delay.py
```

---

## Project Structure

```
equinor-rotating-equipment-agents/
├── agents/              Agent classes (Orchestrator, Planning, Equipment, Vendor, Safety, Execution)
├── database/            JSON database files (equipment, vendors, work orders, personnel, etc.)
├── tools/               Shared utilities (db_reader, report_generator, email_drafter)
├── scenarios/           Three end-to-end runnable workflow scenarios
├── demo/                Interactive CLI entry point
├── requirements.txt     Python dependencies
└── README.md            This file
```

---

## Scenarios

### Scenario 01 — Bundle Change (K-3101, Troll A)
Full workflow for planning a centrifugal compressor bundle replacement:
EquipmentAgent → PlanningAgent → SafetyAgent → VendorAgent (email)

### Scenario 02 — GT Borescope Inspection (GT-4201, Gullfaks C)
Borescope inspection planning for a Siemens Energy SGT-600 gas turbine:
EquipmentAgent → PlanningAgent → SafetyAgent → VendorAgent (contact lookup)

### Scenario 03 — Vendor Delay and Replanning
Baker Hughes reports 21-day delivery delay on a compressor bundle.
ExecutionAgent → PlanningAgent (revised timeline) → VendorAgent (2 emails)

---

## Technology

- **Language**: Python 3.11+
- **Agent framework**: Plain Python classes — no LangChain or external agent libraries
- **Database**: JSON files — no SQL, no external database
- **LLM calls**: Anthropic Python SDK (`anthropic`) — `claude-sonnet-4-20250514`
  - Only `VendorAgent.draft_email()` and `ExecutionAgent.summarize_findings()` use the API
  - Both fall back gracefully to template output if API is unavailable
- **CLI**: Python built-in `input()` / `print()`
