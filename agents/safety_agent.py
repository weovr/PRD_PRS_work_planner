"""
SafetyAgent — validates safety prerequisites for planned jobs.
Checks crew certifications, PTW requirements, and flags expiring certs.
All logic is deterministic.
"""

from datetime import datetime, timedelta
from typing import Any
from tools import db_reader


# Required certifications for offshore work
MANDATORY_OFFSHORE_CERTS = ["GWO Basic Safety", "BOSIET", "H2S"]

# Days before job start at which a cert expiry triggers a warning
CERT_EXPIRY_WARNING_DAYS = 60


class SafetyAgent:
    """Agent responsible for safety prerequisite validation before job execution."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.agent_name = "safety"

    def run(self, params: dict) -> dict:
        """
        Main entry point.
        Expects:
          - plan: job plan dict (for PTW requirements and job dates)
          - platform_id: platform to check crew for (optional if in plan)
          - crew_person_ids: explicit list of person_ids to check (optional)
        """
        plan = params.get("plan", {})
        platform_id = params.get("platform_id") or plan.get("platform_id", "")
        crew_person_ids = params.get("crew_person_ids", [])
        job_start_str = plan.get("proposed_start", "")

        try:
            job_start = datetime.strptime(job_start_str, "%Y-%m-%d") if job_start_str else datetime.today()
        except ValueError:
            job_start = datetime.today()

        # Gather crew to check
        personnel_to_check = []
        if crew_person_ids:
            all_personnel = db_reader.get_all_personnel(self.db_path)
            for p in all_personnel:
                if p.get("person_id") in crew_person_ids:
                    personnel_to_check.append(p)
        elif platform_id:
            personnel_to_check = db_reader.get_personnel_for_platform(self.db_path, platform_id)
            # Also include vendor personnel relevant to this job
            vendor_name = plan.get("vendor", "")
            if vendor_name:
                vendor_personnel = db_reader.get_vendor_personnel(self.db_path, vendor_name.split("/")[0].strip())
                personnel_to_check.extend(vendor_personnel)

        # Run certification checks
        cert_checks = []
        warnings = []
        for person in personnel_to_check:
            checks = self._check_person_certifications(person, job_start)
            cert_checks.extend(checks)
            for check in checks:
                if check.get("status") == "warning":
                    warnings.append(
                        f"{person.get('name')} — sertifikat '{check.get('cert')}' utløper "
                        f"{check.get('expiry_date')} (innen {CERT_EXPIRY_WARNING_DAYS} dager fra jobbstart)"
                    )
                elif check.get("status") == "expired":
                    warnings.append(
                        f"KRITISK: {person.get('name')} — sertifikat '{check.get('cert')}' "
                        f"er UTLØPT ({check.get('expiry_date')})"
                    )

        # PTW check
        ptw_requirements = []
        if plan:
            job_type = plan.get("job_type", "")
            if job_type:
                template = db_reader.get_job_template(self.db_path, job_type)
                if template:
                    ptw_requirements = template.get("ptw_requirements", [])

        ptw_check = {
            "required": ptw_requirements,
            "status": "PTW-søknad må utstedes av utstedelsesmyndighet på plattform",
        }

        # Overall pass/fail
        has_expired = any(c.get("status") == "expired" for c in cert_checks)
        overall_status = "FAIL" if has_expired else "PASS"

        return {
            "status": "ok",
            "agent": self.agent_name,
            "data": {
                "overall_status": overall_status,
                "job_start": job_start_str,
                "platform_id": platform_id,
                "certification_checks": cert_checks,
                "ptw_check": ptw_check,
                "warnings": warnings,
                "personnel_checked": len(personnel_to_check),
            },
        }

    def _check_person_certifications(self, person: dict, job_start: datetime) -> list:
        """Check all mandatory certifications for a person against the job start date."""
        results = []
        cert_expiry = person.get("cert_expiry", {})
        person_name = person.get("name", "N/A")
        person_id = person.get("person_id", "N/A")

        for cert in MANDATORY_OFFSHORE_CERTS:
            expiry_str = cert_expiry.get(cert)
            if not expiry_str:
                # Cert not registered — treat as warning unless person is onshore-only
                results.append({
                    "person_id": person_id,
                    "person": person_name,
                    "cert": cert,
                    "status": "missing",
                    "expiry_date": "N/A",
                    "message": f"Sertifikat ikke registrert",
                })
                continue

            try:
                expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d")
            except ValueError:
                results.append({
                    "person_id": person_id,
                    "person": person_name,
                    "cert": cert,
                    "status": "error",
                    "expiry_date": expiry_str,
                    "message": "Ugyldig datofelt",
                })
                continue

            today = datetime.today()

            if expiry_date < today:
                status = "expired"
                message = f"Utløpt {expiry_str} — UGYLDIG"
            elif expiry_date < job_start + timedelta(days=CERT_EXPIRY_WARNING_DAYS):
                # Expires within warning window of job start
                days_after_job = (expiry_date - job_start).days
                if days_after_job < 0:
                    status = "expired_at_job_start"
                    message = f"Utløper {expiry_str} — utløpt ved jobbstart"
                else:
                    status = "warning"
                    message = f"Utløper {expiry_str} — {days_after_job} dager etter jobbstart (< {CERT_EXPIRY_WARNING_DAYS}d)"
            else:
                status = "ok"
                days_valid = (expiry_date - today).days
                message = f"Gyldig til {expiry_str} ({days_valid} dager)"

            results.append({
                "person_id": person_id,
                "person": person_name,
                "cert": cert,
                "status": status,
                "expiry_date": expiry_str,
                "message": message,
            })

        return results
