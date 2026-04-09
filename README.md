# Equinor GTS — Roterende Utstyr Agent System

Et konseptdemonstrasjonssystem for vedlikeholdsplanlegging av roterende utstyr på Equinors offshore-plattformer, bygget som et **Claude Code multi-agent system**.

> **Ansvarsfraskrivelse**: Systemet bruker **fiktive demodata** modellert etter reelle Equinor-operasjoner. Det har **ingen tilknytning** til Equinors systemer (SAP, Safran eller andre). Alle utstyrstagg, personell, arbeidsordre og leverandørkontakter er fabrikkerte.

---

## Hva systemet demonstrerer

- **Multi-agent orkestrering** via Claude Code subagenter — spesialistagenter delegerer til hverandre etter behov
- **Deterministisk jobbplanlegging** fra standardmaler og JSON-databaseoppslag — ingen hallusinasjon
- **Leverandørkoordinering** — ledetidssjekk, mob-fristberegning og profesjonell e-postutkast
- **Sikkerhetsvalidering** — sertifikatsjekk mot jobboppstartsdato med advarsler for snart utløpende sertifikater
- **Utførelsessporing** — åpne SAP-arbeidsordre med forsinkelsesdeteksjon og statusoppsummering
- **Realistisk domenedata** — utstyrstagg, SAP-ordretyper, Safran-aktivitets-ID-er, norsk fagspråk

---

## Agenter

| Agent | Rolle |
|-------|-------|
| **Orkestreringsagenten** (CLAUDE.md) | Forstår brukerens forespørsel og delegerer til riktig spesialist |
| **equipment-agent** | Teknisk status, driftstimer, overhaul-vurdering, reservedelsstatus |
| **planning-agent** | Komplett jobbplan fra mal, tidslinjeberegning, revidering ved forsinkelse |
| **vendor-agent** | Leverandørkort, rammekontraktstatus, mobiliseringsforespørsel, forsinkelsesbekreftelse |
| **safety-agent** | Sertifikatvalidering per person, PTW-krav, advarsler og tiltak |
| **execution-agent** | Åpne og forsinkede arbeidsordre, daglig statusoppsummering per plattform |

---

## Utstyr som dekkes

- **Sentrifugalkompressorer**: Baker Hughes / Nuovo Pignone PCL804, MCL606, BCL505
- **Gassturbiner**: Siemens Energy SGT-600, SGT-500; Solar Turbines Mars 100
- **Injeksjonspumper**: Flowserve DVMX-serie
- **Brannvannspumper**: Flowserve LNN-serie
- **Hjelpekompressorer**: MAN Energy Solutions L-type stempelkompressor

---

## Plattformer

| Plattform | Type | Område |
|-----------|------|--------|
| Troll A | Semi-nedsenkbar | Hordaland |
| Gullfaks C | Betong GBS | Rogaland |
| Snorre B | Semi-nedsenkbar | Rogaland |
| Johan Sverdrup PII | Fast jacket | Rogaland |
| Åsgard B | Semi-nedsenkbar | Møre |

---

## Slik bruker du systemet

### Krav

- [Claude Code](https://claude.ai/code) installert
- Tilgang til Claude (Sonnet eller Opus anbefalt)

### Kom i gang

1. **Klon repoet**:
   ```bash
   git clone <repo-url>
   cd PRD_PRS_work_planner
   ```

2. **Åpne Claude Code i prosjektmappen**:
   ```bash
   claude
   ```

3. **Skriv spørsmål på norsk** — systemet håndterer resten.

### Eksempelforespørsler

```
Hva er status på kompressor K-3101 på Troll A?

Lag jobbplan for bundleskifte på K-3101, oppstart 2026-09-01.

Sjekk sertifikater for planlagt bundleskifte 2026-09-01.

Skriv mobiliseringsforespørsel til Baker Hughes for K-3101.

Vis alle åpne og forsinkede arbeidsordre.

Baker Hughes melder 21 dagers forsinkelse på bundle til K-3101.
Lag revidert tidsplan og skriv forsinkelsesbekreftelse.
```

---

## Typiske arbeidsflyter

### Planlegging av vedlikeholdsjobb
1. `equipment-agent` → teknisk status og historikk
2. `planning-agent` → komplett jobbplan
3. `safety-agent` → sertifikatsjekk for planlagt dato
4. `vendor-agent` → mobiliseringsforespørsel

### Leverandørforsinkelse
1. `execution-agent` → finn berørt arbeidsordre
2. `planning-agent` → beregn revidert tidsplan
3. `vendor-agent` → forsinkelsesbekreftelse og eskalering

### Statussjekk
1. `execution-agent` → åpne arbeidsordre per plattform
2. `equipment-agent` → detaljer ved behov

---

## Prosjektstruktur

```
PRD_PRS_work_planner/
├── .claude/
│   └── agents/
│       ├── equipment-agent.md   ← Utstyrsstatus og historikk
│       ├── planning-agent.md    ← Jobbplanlegging fra mal
│       ├── vendor-agent.md      ← Leverandørkoordinering og e-post
│       ├── safety-agent.md      ← Sertifikat- og PTW-validering
│       └── execution-agent.md   ← Arbeidsordrestatus og forsinkelser
├── database/
│   ├── equipment.json           ← 15 stykker roterende utstyr
│   ├── platforms.json           ← 5 offshore-plattformer
│   ├── vendors.json             ← 6 leverandører med rammekontrakter
│   ├── work_orders.json         ← 21 SAP-arbeidsordre
│   ├── job_templates.json       ← 6 jobbmaler med aktivitetslister
│   ├── spare_parts.json         ← 31 reservedeler med lagerstatus
│   └── personnel.json           ← 15 personell med sertifikater
├── CLAUDE.md                    ← Orkestreringsagentens instruksjoner
└── README.md                    ← Denne filen
```

---

## Teknologi

- **Plattform**: Claude Code med innebygd subagent-støtte (`.claude/agents/`)
- **Database**: JSON-filer — ingen SQL, ingen ekstern database
- **Språk**: Norsk bokmål med korrekt fagspråk for offshorebransjen
- **Ingen kode å kjøre** — Claude leser databasen og svarer direkte
