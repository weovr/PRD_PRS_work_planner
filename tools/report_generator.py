"""
Report generator utility — produces formatted text output for console display.
Uses Equinor operations terminology and Norwegian language for user-facing text.
"""

from typing import Any


def section_header(title: str, width: int = 60) -> str:
    """Return a top-level section header with = underline."""
    line = "=" * width
    return f"\n{line}\n  {title}\n{line}"


def sub_header(title: str, width: int = 60) -> str:
    """Return a sub-section header with - underline."""
    line = "-" * width
    return f"\n{title}\n{line}"


def format_job_plan(plan: dict) -> str:
    """Format a job plan dict as a readable console report."""
    lines = []
    lines.append(section_header(f"JOBBPLAN: {plan.get('title', 'N/A')}"))
    lines.append(f"  Jobb-ID          : {plan.get('job_id', 'N/A')}")
    lines.append(f"  Utstyr           : {plan.get('equipment_tag', 'N/A')}")
    lines.append(f"  Plattform        : {plan.get('platform', 'N/A')}")
    lines.append(f"  Jobbtype         : {plan.get('job_type', 'N/A')}")
    lines.append(f"  SAP Ordretype    : {plan.get('sap_wo_type', 'N/A')}")
    lines.append(f"  Safran aktivitet : {plan.get('safran_activity', 'N/A')}")
    lines.append(f"  Foreslått start  : {plan.get('proposed_start', 'N/A')}")
    lines.append(f"  Foreslått slutt  : {plan.get('proposed_finish', 'N/A')}")
    lines.append(f"  POB-dager        : {plan.get('pob_days', 'N/A')}")
    lines.append(f"  Risikonivå       : {plan.get('risk_level', 'N/A')}")
    lines.append(f"  Est. kostnad     : NOK {plan.get('estimated_cost_nok', 0):,.0f}".replace(",", " "))

    lines.append(sub_header("Bemanning"))
    crew = plan.get("crew_required", {})
    lines.append(f"  Equinor teknikere   : {crew.get('equinor_technicians', 0)}")
    lines.append(f"  Leverandørteknikere : {crew.get('vendor_technicians', 0)}")
    lines.append(f"  Disiplinleder       : {crew.get('discipline_lead', 0)}")

    lines.append(sub_header("Leverandør"))
    lines.append(f"  Leverandør          : {plan.get('vendor', 'N/A')}")
    lines.append(f"  Mob.-frist          : {plan.get('vendor_mob_deadline', 'N/A')}")

    lines.append(sub_header("Reservedeler"))
    critical_parts = plan.get("critical_parts", [])
    if critical_parts:
        for part in critical_parts:
            lines.append(f"  - {part}")
    else:
        lines.append("  Ingen kritiske reservedeler registrert")
    lines.append(f"  Status              : {plan.get('parts_status', 'N/A')}")

    lines.append(sub_header("PTW / Arbeidstillatelse"))
    ptw = plan.get("ptw_type", "N/A")
    lines.append(f"  Krav: {ptw}")

    lines.append(sub_header("Aktivitetssekvens"))
    for activity in plan.get("activities", []):
        lines.append(f"  {activity}")

    return "\n".join(lines)


def format_equipment_summary(data: dict) -> str:
    """Format equipment data as a readable console report."""
    eq = data.get("equipment", {})
    history = data.get("maintenance_history", [])
    parts = data.get("spare_parts", [])

    lines = []
    lines.append(section_header(f"UTSTYRSINFO: {eq.get('tag', 'N/A')}"))
    lines.append(f"  Beskrivelse      : {eq.get('description', 'N/A')}")
    lines.append(f"  Plattform        : {eq.get('platform_id', 'N/A')}")
    lines.append(f"  Type             : {eq.get('type', 'N/A')}")
    lines.append(f"  Fabrikant        : {eq.get('manufacturer', 'N/A')}")
    lines.append(f"  Modell           : {eq.get('model', 'N/A')}")
    lines.append(f"  Serienummer      : {eq.get('serial_number', 'N/A')}")
    lines.append(f"  Installert       : {eq.get('installation_year', 'N/A')}")
    lines.append(f"  Kritikalitet     : {eq.get('criticality', 'N/A')}")
    lines.append(f"  SAP utstyr-ID    : {eq.get('sap_equipment_id', 'N/A')}")

    lines.append(sub_header("Driftstimer og overhaul"))
    lines.append(f"  Driftstimer      : {eq.get('running_hours', 0):,}".replace(",", " "))
    lines.append(f"  Overhaul-intervall: {eq.get('oh_interval_hours', 0):,} t".replace(",", " "))
    hours_to_oh = (eq.get("oh_interval_hours", 0) or 0) - (eq.get("running_hours", 0) or 0)
    lines.append(f"  Timer til neste  : {max(0, hours_to_oh):,} t".replace(",", " "))
    lines.append(f"  Siste overhaul   : {eq.get('last_overhaul', 'N/A')}")
    lines.append(f"  Neste planlagt   : {eq.get('next_planned_overhaul', 'N/A')}")

    lines.append(sub_header("Vedlikeholdshistorikk (siste 5)"))
    if history:
        for wo in history:
            status_marker = "[ÅPEN]" if wo.get("status") not in ("TECO", "CLSD") else "[TECO]"
            lines.append(f"  {status_marker} {wo.get('wo_number')} | {wo.get('start_date', 'N/A')} | {wo.get('description', '')}")
    else:
        lines.append("  Ingen historikk funnet")

    lines.append(sub_header("Kritiske reservedeler"))
    if parts:
        for p in parts[:5]:
            stock_status = "På lager" if p.get("stock_quantity", 0) > 0 else "IKKE PÅ LAGER"
            lines.append(f"  [{stock_status}] {p.get('description', 'N/A')} — {p.get('stock_location', 'N/A')}")
    else:
        lines.append("  Ingen reservedeler registrert")

    return "\n".join(lines)


def format_safety_report(data: dict) -> str:
    """Format safety check results as a readable console report."""
    lines = []
    overall = data.get("overall_status", "UKJENT")
    status_marker = "GODKJENT" if overall == "PASS" else "IKKE GODKJENT"
    lines.append(section_header(f"SIKKERHETSKONTROLL — {status_marker}"))

    cert_checks = data.get("certification_checks", [])
    if cert_checks:
        lines.append(sub_header("Sertifikatvalidering"))
        for check in cert_checks:
            icon = "OK" if check.get("status") == "ok" else ("ADVARSEL" if check.get("status") == "warning" else "FEIL")
            lines.append(f"  [{icon}] {check.get('person', 'N/A')} — {check.get('cert', 'N/A')}: {check.get('message', '')}")

    ptw_check = data.get("ptw_check", {})
    if ptw_check:
        lines.append(sub_header("PTW / Arbeidstillatelse"))
        lines.append(f"  Krav for jobtype : {', '.join(ptw_check.get('required', []))}")
        lines.append(f"  Status           : {ptw_check.get('status', 'N/A')}")

    warnings = data.get("warnings", [])
    if warnings:
        lines.append(sub_header("Advarsler"))
        for w in warnings:
            lines.append(f"  ! {w}")

    return "\n".join(lines)


def format_execution_status(data: dict) -> str:
    """Format execution status report for open work orders."""
    lines = []
    lines.append(section_header("UTFØRELSESTATUS — ÅPNE ARBEIDSORDRE"))
    open_wos = data.get("open_work_orders", [])
    if not open_wos:
        lines.append("  Ingen åpne arbeidsordre registrert.")
        return "\n".join(lines)

    for wo in open_wos:
        lines.append(sub_header(f"AO {wo.get('wo_number')} — {wo.get('description', 'N/A')}"))
        lines.append(f"  Plattform        : {wo.get('platform_id', 'N/A')}")
        lines.append(f"  Utstyr           : {wo.get('equipment_tag', 'N/A')}")
        lines.append(f"  Status           : {wo.get('status', 'N/A')}")
        lines.append(f"  Planlagt start   : {wo.get('start_date', 'N/A')}")
        lines.append(f"  Hastegrad        : {wo.get('priority', 'N/A')}")
        overdue = data.get("overdue_flags", {}).get(wo.get("wo_number"), False)
        if overdue:
            lines.append(f"  *** FORSINKET — planlagt ferdigstillelse passert ***")

    return "\n".join(lines)


def format_vendor_info(data: dict) -> str:
    """Format vendor information as a readable console report."""
    vendor = data.get("vendor", {})
    lines = []
    lines.append(section_header(f"LEVERANDØRINFO: {vendor.get('name', 'N/A')}"))
    lines.append(f"  Leverandør-ID    : {vendor.get('vendor_id', 'N/A')}")
    lines.append(f"  Kontaktperson    : {vendor.get('contact_person', 'N/A')}")
    lines.append(f"  E-post           : {vendor.get('contact_email', 'N/A')}")
    lines.append(f"  Telefon          : {vendor.get('contact_phone', 'N/A')}")
    lines.append(f"  Teknisk kontakt  : {vendor.get('technical_contact', 'N/A')}")
    lines.append(f"  Rammekontrakt    : {vendor.get('frame_agreement_id', 'N/A')}")
    lines.append(f"  Utløper          : {vendor.get('frame_agreement_expiry', 'N/A')}")
    lines.append(f"  Ledetid standard : {vendor.get('lead_time_days_standard', 'N/A')} dager")
    lines.append(f"  Ledetid kritisk  : {vendor.get('lead_time_days_critical', 'N/A')} dager")
    lines.append(f"  Mob.-tid         : {vendor.get('mob_time_days', 'N/A')} dager")
    lines.append(sub_header("Spesialiteter"))
    for s in vendor.get("specialities", []):
        lines.append(f"  - {s}")
    mob_deadline = data.get("mob_deadline")
    if mob_deadline:
        lines.append(sub_header("Mobiliseringsdeadline"))
        lines.append(f"  Frist for mobilisering: {mob_deadline}")
    return "\n".join(lines)
