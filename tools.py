"""
Database tools exposed to Claude.
Claude calls these to look up real data — it decides which ones to use and when.
"""

import json
import os
from datetime import datetime, timedelta

DB = os.path.join(os.path.dirname(__file__), "database")


def _load(filename):
    with open(os.path.join(DB, filename), encoding="utf-8") as f:
        return json.load(f)


# ── Tool definitions Claude receives ─────────────────────────────────────────

TOOLS = [
    {
        "name": "get_equipment",
        "description": "Hent teknisk informasjon og driftstimestatus for et roterende utstyr (kompressor, gassturbine, pumpe) basert på utstyrstagg.",
        "input_schema": {
            "type": "object",
            "properties": {"tag": {"type": "string", "description": "Utstyrstagg, f.eks. K-3101, GT-4201, P-6101"}},
            "required": ["tag"],
        },
    },
    {
        "name": "get_maintenance_history",
        "description": "Hent vedlikeholdshistorikk (SAP-arbeidsordre) for et utstyr — hva er gjort, når, av hvem og hva ble funnet.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tag": {"type": "string", "description": "Utstyrstagg"},
                "antall": {"type": "integer", "description": "Maks antall arbeidsordre (standard 5)", "default": 5},
            },
            "required": ["tag"],
        },
    },
    {
        "name": "get_open_work_orders",
        "description": "Hent alle åpne og aktive arbeidsordre på tvers av plattformer. Viser hva som pågår akkurat nå.",
        "input_schema": {
            "type": "object",
            "properties": {
                "plattform": {"type": "string", "description": "Filtrer på plattform-ID, f.eks. TROLL-A (valgfri)"}
            },
        },
    },
    {
        "name": "get_vendor",
        "description": "Hent leverandørinformasjon: kontaktpersoner, rammekontrakt, ledetider og mobiliseringstid.",
        "input_schema": {
            "type": "object",
            "properties": {
                "søk": {"type": "string", "description": "Leverandør-ID (BH-NP, SE, MAN-ES, FS, JC, SKF) eller navn (Baker Hughes, Siemens, osv.)"}
            },
            "required": ["søk"],
        },
    },
    {
        "name": "get_spare_parts",
        "description": "Sjekk reservedelsstatus for et utstyr: hva er på lager, hva mangler, ledetider på kritiske deler.",
        "input_schema": {
            "type": "object",
            "properties": {"tag": {"type": "string", "description": "Utstyrstagg"}},
            "required": ["tag"],
        },
    },
    {
        "name": "get_job_template",
        "description": "Hent standardisert jobbmal med aktivitetsliste, PTW-krav, bemanningsbehov og estimert kostnad/varighet.",
        "input_schema": {
            "type": "object",
            "properties": {
                "mal": {
                    "type": "string",
                    "description": "Mal-ID: bundle_change_centrifugal_compressor | gt_borescope_inspection | gt_hot_section_overhaul | seal_replacement_centrifugal | bearing_replacement | pump_overhaul",
                }
            },
            "required": ["mal"],
        },
    },
    {
        "name": "get_personnel",
        "description": "Hent personell og sertifikatstatus. Kan sjekke om sertifikater er gyldige ved en bestemt dato (for planlegging).",
        "input_schema": {
            "type": "object",
            "properties": {
                "plattform": {"type": "string", "description": "Plattform-ID (valgfri)"},
                "inkluder_leverandør": {"type": "boolean", "description": "Inkluder leverandørpersonell"},
                "sjekk_dato": {"type": "string", "description": "Dato for sertifikatvalidering (YYYY-MM-DD)"},
            },
        },
    },
    {
        "name": "beregn_tidslinje",
        "description": "Beregn jobbplan: ferdigdato og mob-frist for leverandør basert på oppstartsdato og jobbmal.",
        "input_schema": {
            "type": "object",
            "properties": {
                "oppstart": {"type": "string", "description": "Planlagt oppstartsdato (YYYY-MM-DD)"},
                "pob_dager": {"type": "integer", "description": "Estimert antall POB-dager"},
                "mob_dager": {"type": "integer", "description": "Leverandørens mobiliseringstid i dager"},
            },
            "required": ["oppstart", "pob_dager", "mob_dager"],
        },
    },
    {
        "name": "beregn_revidert_tidslinje",
        "description": "Beregn ny tidsplan etter en forsinkelse — forskyver alle datoer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "opprinnelig_oppstart": {"type": "string"},
                "opprinnelig_slutt": {"type": "string"},
                "opprinnelig_mob_frist": {"type": "string"},
                "forsinkelse_dager": {"type": "integer"},
            },
            "required": ["opprinnelig_oppstart", "opprinnelig_slutt", "opprinnelig_mob_frist", "forsinkelse_dager"],
        },
    },
]


# ── Tool implementations ──────────────────────────────────────────────────────

def run_tool(name: str, inputs: dict) -> str:
    try:
        result = {
            "get_equipment":            _get_equipment,
            "get_maintenance_history":  _get_maintenance_history,
            "get_open_work_orders":     _get_open_work_orders,
            "get_vendor":               _get_vendor,
            "get_spare_parts":          _get_spare_parts,
            "get_job_template":         _get_job_template,
            "get_personnel":            _get_personnel,
            "beregn_tidslinje":         _beregn_tidslinje,
            "beregn_revidert_tidslinje": _beregn_revidert_tidslinje,
        }[name](inputs)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"feil": str(e)}, ensure_ascii=False)


def _get_equipment(p):
    tag = p["tag"].upper()
    items = _load("equipment.json")
    eq = next((e for e in items if e["tag"].upper() == tag), None)
    if not eq:
        return {"feil": f"Utstyr ikke funnet: {tag}"}
    rh = eq.get("running_hours") or 0
    iv = eq.get("oh_interval_hours") or 0
    eq["timer_igjen_til_overhaul"] = max(0, iv - rh)
    eq["overhaul_forfalt"] = rh > iv
    return eq


def _get_maintenance_history(p):
    tag = p["tag"].upper()
    n = p.get("antall", 5)
    orders = _load("work_orders.json")
    matching = [o for o in orders if o.get("equipment_tag", "").upper() == tag]
    matching.sort(key=lambda x: x.get("start_date") or "", reverse=True)
    return {"utstyr": tag, "arbeidsordre": matching[:n]}


def _get_open_work_orders(p):
    plattform = (p.get("plattform") or "").upper()
    orders = _load("work_orders.json")
    open_orders = [o for o in orders if o.get("status") not in ("TECO", "CLSD")]
    if plattform:
        open_orders = [o for o in open_orders if o.get("platform_id", "").upper() == plattform]
    today = datetime.today()
    for o in open_orders:
        try:
            start = datetime.strptime(o["start_date"], "%Y-%m-%d")
            o["dager_åpen"] = (today - start).days
        except Exception:
            pass
    return {"antall_åpne": len(open_orders), "arbeidsordre": open_orders}


def _get_vendor(p):
    søk = p["søk"].upper()
    vendors = _load("vendors.json")
    v = next((v for v in vendors if v["vendor_id"].upper() == søk or søk in v["name"].upper()), None)
    if not v:
        return {"feil": f"Leverandør ikke funnet: {p['søk']}"}
    return v


def _get_spare_parts(p):
    tag = p["tag"].upper()
    parts = _load("spare_parts.json")
    relevant = [pt for pt in parts if tag in [t.upper() for t in pt.get("equipment_tags", [])]]
    for pt in relevant:
        pt["på_lager"] = (pt.get("stock_quantity") or 0) > 0
    return {"utstyr": tag, "antall": len(relevant), "deler": relevant}


def _get_job_template(p):
    templates = _load("job_templates.json")
    t = templates.get(p["mal"])
    if not t:
        return {"feil": f"Mal ikke funnet: {p['mal']}", "tilgjengelige": list(templates.keys())}
    return t


def _get_personnel(p):
    plattform = (p.get("plattform") or "").upper()
    inkl_leverandør = p.get("inkluder_leverandør", False)
    sjekk_dato_str = p.get("sjekk_dato")
    try:
        sjekk_dato = datetime.strptime(sjekk_dato_str, "%Y-%m-%d") if sjekk_dato_str else datetime.today()
    except Exception:
        sjekk_dato = datetime.today()

    all_p = _load("personnel.json")
    result = []
    for person in all_p:
        person_platform = (person.get("platform_id") or "").upper()
        if plattform and person_platform != plattform and not person.get("vendor_personnel"):
            continue
        if person.get("vendor_personnel") and not inkl_leverandør:
            continue
        sertifikater = []
        for cert, dato_str in (person.get("cert_expiry") or {}).items():
            try:
                exp = datetime.strptime(dato_str, "%Y-%m-%d")
                dager = (exp - sjekk_dato).days
                status = "UTLØPT" if dager < 0 else ("UTLØPER_SNART" if dager < 60 else "OK")
            except Exception:
                status = "ukjent"
                dager = None
            sertifikater.append({"sertifikat": cert, "utløper": dato_str, "status": status, "dager_igjen": dager})
        result.append({**person, "sertifikatstatus": sertifikater})
    return {"sjekket_dato": sjekk_dato.strftime("%Y-%m-%d"), "personell": result}


def _beregn_tidslinje(p):
    start = datetime.strptime(p["oppstart"], "%Y-%m-%d")
    slutt = start + timedelta(days=p["pob_dager"])
    mob = start - timedelta(days=p["mob_dager"])
    return {
        "oppstart": start.strftime("%Y-%m-%d"),
        "ferdig": slutt.strftime("%Y-%m-%d"),
        "mob_frist": mob.strftime("%Y-%m-%d"),
        "dager_til_oppstart": (start - datetime.today()).days,
    }


def _beregn_revidert_tidslinje(p):
    d = timedelta(days=p["forsinkelse_dager"])
    def shift(s):
        return (datetime.strptime(s, "%Y-%m-%d") + d).strftime("%Y-%m-%d")
    return {
        "ny_oppstart": shift(p["opprinnelig_oppstart"]),
        "ny_slutt": shift(p["opprinnelig_slutt"]),
        "ny_mob_frist": shift(p["opprinnelig_mob_frist"]),
        "forsinkelse_dager": p["forsinkelse_dager"],
        "opprinnelig_oppstart": p["opprinnelig_oppstart"],
        "opprinnelig_slutt": p["opprinnelig_slutt"],
    }
