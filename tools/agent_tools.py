"""
Tool definitions and implementations for the Equinor Rotating Equipment Agent.

These are the functions Claude calls when it needs to look up data or perform calculations.
Claude decides which tools to call and in what order — the tools themselves are pure data access.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Optional
from tools import db_reader


# ─────────────────────────────────────────────
#  Tool definitions (sent to Claude API)
# ─────────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "name": "get_equipment",
        "description": (
            "Henter teknisk informasjon om et roterende utstyr basert på utstyrstagg. "
            "Returnerer spesifikasjoner, driftstimer, overhaul-status og neste planlagte vedlikehold."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "tag": {
                    "type": "string",
                    "description": "Utstyrstagg, f.eks. K-3101, GT-4201, P-6101",
                }
            },
            "required": ["tag"],
        },
    },
    {
        "name": "get_work_order_history",
        "description": (
            "Henter arbeidsordrehistorikk (SAP) for et spesifikt utstyr. "
            "Viser siste vedlikeholdsjobber med funn, utførte aktiviteter og kostnader."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "tag": {"type": "string", "description": "Utstyrstagg"},
                "limit": {
                    "type": "integer",
                    "description": "Maks antall arbeidsordre å returnere (standard 5)",
                    "default": 5,
                },
            },
            "required": ["tag"],
        },
    },
    {
        "name": "get_open_work_orders",
        "description": (
            "Henter alle åpne/aktive arbeidsordre (status ikke TECO eller CLSD). "
            "Kan filtreres på plattform. Viser om noen er forsinket."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "platform_id": {
                    "type": "string",
                    "description": "Filtrer på plattform-ID, f.eks. TROLL-A (valgfri)",
                }
            },
        },
    },
    {
        "name": "get_vendor",
        "description": (
            "Henter leverandørinformasjon inkl. kontaktpersoner, rammekontrakt-ID, "
            "ledetider og mobiliseringstid. Søk på navn eller ID."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "vendor_id": {
                    "type": "string",
                    "description": "Leverandør-ID, f.eks. BH-NP, SE, MAN-ES, FS, JC, SKF",
                },
                "vendor_name": {
                    "type": "string",
                    "description": "Leverandørnavn eller del av navn, f.eks. 'Baker Hughes', 'Siemens'",
                },
            },
        },
    },
    {
        "name": "get_spare_parts",
        "description": (
            "Henter reservedelsstatus for et utstyr: lagerbeholdning, lagerlokasjon, "
            "ledetider og kritikalitet."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "tag": {"type": "string", "description": "Utstyrstagg"},
            },
            "required": ["tag"],
        },
    },
    {
        "name": "get_job_template",
        "description": (
            "Henter en standardisert jobbmal med aktivitetsliste, bemanningskrav, "
            "PTW-krav, reservedelsliste og estimert varighet/kostnad. "
            "Tilgjengelige maler: bundle_change_centrifugal_compressor, "
            "gt_borescope_inspection, gt_hot_section_overhaul, "
            "seal_replacement_centrifugal, bearing_replacement, pump_overhaul."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "template_id": {
                    "type": "string",
                    "description": "Mal-ID, f.eks. bundle_change_centrifugal_compressor",
                }
            },
            "required": ["template_id"],
        },
    },
    {
        "name": "get_platform",
        "description": "Henter plattforminformasjon: type, POB-grense, helikopterdekk, kontaktpersoner.",
        "input_schema": {
            "type": "object",
            "properties": {
                "platform_id": {
                    "type": "string",
                    "description": "Plattform-ID, f.eks. TROLL-A, GULLFAKS-C, SNORRE-B, JSV-PII, ASGARD-B",
                }
            },
            "required": ["platform_id"],
        },
    },
    {
        "name": "get_personnel",
        "description": (
            "Henter personell med sertifikater og kompetanse. "
            "Kan filtrere på plattform eller inkludere leverandørpersonell. "
            "Beregner automatisk om sertifikater er gyldige ved en gitt dato."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "platform_id": {
                    "type": "string",
                    "description": "Filtrer på plattform-ID (valgfri)",
                },
                "include_vendor_personnel": {
                    "type": "boolean",
                    "description": "Inkluder leverandørpersonell (standard false)",
                    "default": False,
                },
                "check_date": {
                    "type": "string",
                    "description": "Dato for sertifikatsjekk (ISO-format YYYY-MM-DD, standard i dag)",
                },
            },
        },
    },
    {
        "name": "calculate_job_timeline",
        "description": (
            "Beregner tidsplan for en vedlikeholdsjobb: "
            "oppstartsdato, ferdigdato, mob-frist for leverandør. "
            "Tar hensyn til leverandørens mobiliseringstid."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "proposed_start": {
                    "type": "string",
                    "description": "Foreslått oppstartsdato (YYYY-MM-DD)",
                },
                "pob_days": {
                    "type": "integer",
                    "description": "Estimert antall POB-dager (fra jobbmal)",
                },
                "vendor_mob_days": {
                    "type": "integer",
                    "description": "Leverandørens mobiliseringstid i dager",
                },
            },
            "required": ["proposed_start", "pob_days", "vendor_mob_days"],
        },
    },
    {
        "name": "calculate_revised_timeline",
        "description": (
            "Beregner revidert tidsplan etter en forsinkelse. "
            "Forskyver oppstart, ferdigdato og mob-frist med antall forsinkelsesdager."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "original_start": {
                    "type": "string",
                    "description": "Opprinnelig oppstartsdato (YYYY-MM-DD)",
                },
                "original_finish": {
                    "type": "string",
                    "description": "Opprinnelig ferdigdato (YYYY-MM-DD)",
                },
                "original_mob_deadline": {
                    "type": "string",
                    "description": "Opprinnelig mob-frist (YYYY-MM-DD)",
                },
                "delay_days": {
                    "type": "integer",
                    "description": "Antall forsinkelsesdager",
                },
            },
            "required": ["original_start", "original_finish", "original_mob_deadline", "delay_days"],
        },
    },
]


# ─────────────────────────────────────────────
#  Tool execution dispatcher
# ─────────────────────────────────────────────

def execute_tool(db_path: str, tool_name: str, tool_input: dict) -> str:
    """Dispatch a tool call from Claude to the appropriate function and return JSON string."""
    handlers = {
        "get_equipment": _get_equipment,
        "get_work_order_history": _get_work_order_history,
        "get_open_work_orders": _get_open_work_orders,
        "get_vendor": _get_vendor,
        "get_spare_parts": _get_spare_parts,
        "get_job_template": _get_job_template,
        "get_platform": _get_platform,
        "get_personnel": _get_personnel,
        "calculate_job_timeline": _calculate_job_timeline,
        "calculate_revised_timeline": _calculate_revised_timeline,
    }
    handler = handlers.get(tool_name)
    if not handler:
        return json.dumps({"feil": f"Ukjent verktøy: {tool_name}"}, ensure_ascii=False)
    result = handler(db_path, tool_input)
    return json.dumps(result, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────
#  Tool implementations
# ─────────────────────────────────────────────

def _get_equipment(db_path: str, params: dict) -> dict:
    tag = params.get("tag", "").upper()
    equipment = db_reader.get_equipment(db_path, tag)
    if not equipment:
        return {"feil": f"Utstyr ikke funnet: {tag}"}

    running = equipment.get("running_hours", 0) or 0
    interval = equipment.get("oh_interval_hours", 0) or 0
    hours_remaining = max(0, interval - running)
    overdue = running > interval

    return {
        **equipment,
        "overhaul_analyse": {
            "timer_igjen_til_overhaul": hours_remaining,
            "overhaul_forfalt": overdue,
            "prosent_brukt": round((running / interval * 100) if interval else 0, 1),
        },
    }


def _get_work_order_history(db_path: str, params: dict) -> dict:
    tag = params.get("tag", "").upper()
    limit = params.get("limit", 5)
    orders = db_reader.get_work_orders_for_equipment(db_path, tag, limit=limit)
    if not orders:
        return {"melding": f"Ingen arbeidsordre funnet for {tag}", "arbeidsordre": []}
    return {"utstyr": tag, "antall": len(orders), "arbeidsordre": orders}


def _get_open_work_orders(db_path: str, params: dict) -> dict:
    platform_id = params.get("platform_id")
    orders = db_reader.get_open_work_orders(db_path)
    if platform_id:
        orders = [wo for wo in orders if wo.get("platform_id") == platform_id.upper()]

    today = datetime.today()
    for wo in orders:
        start_str = wo.get("start_date")
        if start_str:
            try:
                start = datetime.strptime(start_str, "%Y-%m-%d")
                wo["dager_siden_oppstart"] = (today - start).days
                wo["forsinket"] = (today - start).days > 60 and not wo.get("finish_date")
            except ValueError:
                wo["forsinket"] = False
        else:
            wo["forsinket"] = False

    return {
        "antall_åpne": len(orders),
        "antall_forsinket": sum(1 for wo in orders if wo.get("forsinket")),
        "arbeidsordre": orders,
    }


def _get_vendor(db_path: str, params: dict) -> dict:
    vendor_id = params.get("vendor_id")
    vendor_name = params.get("vendor_name")
    vendor = None
    if vendor_id:
        vendor = db_reader.get_vendor(db_path, vendor_id)
    elif vendor_name:
        vendor = db_reader.get_vendor_by_name(db_path, vendor_name)
    if not vendor:
        return {"feil": f"Leverandør ikke funnet: {vendor_id or vendor_name}"}
    return vendor


def _get_spare_parts(db_path: str, params: dict) -> dict:
    tag = params.get("tag", "").upper()
    parts = db_reader.get_spare_parts_for_equipment(db_path, tag)
    if not parts:
        return {"melding": f"Ingen reservedeler registrert for {tag}", "deler": []}

    for p in parts:
        p["på_lager"] = (p.get("stock_quantity") or 0) > 0
        p["under_reordernivå"] = (p.get("stock_quantity") or 0) < (p.get("reorder_level") or 0)

    kritiske_mangler = [p for p in parts if p.get("criticality") == "Kritisk" and not p["på_lager"]]
    return {
        "utstyr": tag,
        "totalt_deler": len(parts),
        "kritiske_mangler": len(kritiske_mangler),
        "deler": parts,
    }


def _get_job_template(db_path: str, params: dict) -> dict:
    template_id = params.get("template_id", "")
    template = db_reader.get_job_template(db_path, template_id)
    if not template:
        return {
            "feil": f"Jobbmal ikke funnet: {template_id}",
            "tilgjengelige_maler": [
                "bundle_change_centrifugal_compressor",
                "gt_borescope_inspection",
                "gt_hot_section_overhaul",
                "seal_replacement_centrifugal",
                "bearing_replacement",
                "pump_overhaul",
            ],
        }
    return template


def _get_platform(db_path: str, params: dict) -> dict:
    platform_id = params.get("platform_id", "").upper()
    platform = db_reader.get_platform(db_path, platform_id)
    if not platform:
        return {"feil": f"Plattform ikke funnet: {platform_id}"}
    return platform


def _get_personnel(db_path: str, params: dict) -> dict:
    platform_id = params.get("platform_id")
    include_vendor = params.get("include_vendor_personnel", False)
    check_date_str = params.get("check_date")

    try:
        check_date = datetime.strptime(check_date_str, "%Y-%m-%d") if check_date_str else datetime.today()
    except ValueError:
        check_date = datetime.today()

    all_personnel = db_reader.get_all_personnel(db_path)
    results = []
    for p in all_personnel:
        if platform_id and p.get("platform_id") != platform_id.upper() and not p.get("vendor_personnel"):
            continue
        if p.get("vendor_personnel") and not include_vendor:
            continue

        cert_status = []
        for cert, expiry_str in (p.get("cert_expiry") or {}).items():
            try:
                expiry = datetime.strptime(expiry_str, "%Y-%m-%d")
                days_until = (expiry - check_date).days
                if days_until < 0:
                    status = "UTLØPT"
                elif days_until < 60:
                    status = f"UTLØPER_SNART ({days_until} dager)"
                else:
                    status = f"Gyldig ({days_until} dager)"
                cert_status.append({"sertifikat": cert, "utløper": expiry_str, "status": status})
            except ValueError:
                cert_status.append({"sertifikat": cert, "utløper": expiry_str, "status": "ukjent"})

        results.append({**p, "sertifikatstatus": cert_status})

    return {"sjekket_dato": check_date.strftime("%Y-%m-%d"), "antall": len(results), "personell": results}


def _calculate_job_timeline(db_path: str, params: dict) -> dict:
    proposed_start_str = params.get("proposed_start", "")
    pob_days = params.get("pob_days", 14)
    mob_days = params.get("vendor_mob_days", 14)

    try:
        start = datetime.strptime(proposed_start_str, "%Y-%m-%d")
    except ValueError:
        return {"feil": f"Ugyldig dato: {proposed_start_str}"}

    finish = start + timedelta(days=pob_days)
    mob_deadline = start - timedelta(days=mob_days)

    return {
        "oppstartsdato": start.strftime("%Y-%m-%d"),
        "ferdigdato": finish.strftime("%Y-%m-%d"),
        "mob_frist_leverandør": mob_deadline.strftime("%Y-%m-%d"),
        "pob_dager": pob_days,
        "mob_tid_dager": mob_days,
        "dager_til_oppstart": (start - datetime.today()).days,
    }


def _calculate_revised_timeline(db_path: str, params: dict) -> dict:
    delay_days = params.get("delay_days", 0)
    delta = timedelta(days=delay_days)

    results = {}
    for field in ("original_start", "original_finish", "original_mob_deadline"):
        val = params.get(field, "")
        try:
            original = datetime.strptime(val, "%Y-%m-%d")
            revised = original + delta
            key = field.replace("original_", "revidert_")
            results[field.replace("original_", "opprinnelig_")] = val
            results[key] = revised.strftime("%Y-%m-%d")
        except ValueError:
            results[field] = f"ugyldig dato: {val}"

    results["forsinkelse_dager"] = delay_days
    results["forsinkelse_uker"] = round(delay_days / 7, 1)
    results["konsekvens"] = (
        f"Opprinnelig oppstart {params.get('original_start')} forskyves til "
        f"{results.get('revidert_start', 'N/A')}. "
        f"Ferdigstillelse forskyves tilsvarende {delay_days} dager."
    )
    return results
