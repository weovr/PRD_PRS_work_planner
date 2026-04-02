"""
VendorAgent — handles vendor lookups, mobilization deadlines, frame agreement checks,
and drafts vendor coordination emails using the Anthropic API (with template fallback).
"""

from datetime import datetime, timedelta
from typing import Any, Optional
from tools import db_reader
from tools.email_drafter import (
    draft_vendor_mobilization_email,
    draft_vendor_delay_acknowledgment_email,
)


class VendorAgent:
    """Agent responsible for vendor coordination, lead time checks, and email drafting."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.agent_name = "vendor"

    def run(self, params: dict) -> dict:
        """
        Main entry point.
        Supports actions:
          - 'lookup': look up vendor by vendor_id or name
          - 'draft_mobilization_email': draft a mobilization request email
          - 'draft_delay_email': draft a delay acknowledgment and escalation email
          - 'check_lead_times': check lead times for a list of part IDs
        """
        action = params.get("action", "lookup")

        if action == "lookup":
            return self._lookup_vendor(params)
        elif action == "draft_mobilization_email":
            return self._draft_mobilization_email(params)
        elif action == "draft_delay_email":
            return self._draft_delay_email(params)
        elif action == "check_lead_times":
            return self._check_lead_times(params)
        else:
            return {
                "status": "error",
                "agent": self.agent_name,
                "data": {"message": f"Ukjent handling: {action}"},
            }

    def _lookup_vendor(self, params: dict) -> dict:
        """Look up a vendor and optionally calculate mobilization deadline."""
        vendor_id = params.get("vendor_id")
        vendor_name = params.get("vendor_name")
        job_start_date = params.get("job_start_date")

        vendor = None
        if vendor_id:
            vendor = db_reader.get_vendor(self.db_path, vendor_id)
        elif vendor_name:
            vendor = db_reader.get_vendor_by_name(self.db_path, vendor_name)

        if not vendor:
            return {
                "status": "not_found",
                "agent": self.agent_name,
                "data": {"message": f"Leverandør ikke funnet: {vendor_id or vendor_name}"},
            }

        mob_deadline = None
        if job_start_date:
            try:
                start = datetime.strptime(job_start_date, "%Y-%m-%d")
                mob_days = vendor.get("mob_time_days", 14)
                mob_deadline = (start - timedelta(days=mob_days)).strftime("%Y-%m-%d")
            except ValueError:
                pass

        return {
            "status": "ok",
            "agent": self.agent_name,
            "data": {
                "vendor": vendor,
                "mob_deadline": mob_deadline,
            },
        }

    def _draft_mobilization_email(self, params: dict) -> dict:
        """Draft a vendor mobilization request email."""
        plan = params.get("plan", {})
        vendor_id = plan.get("vendor_id") or params.get("vendor_id")
        vendor = None
        if vendor_id:
            vendor = db_reader.get_vendor(self.db_path, vendor_id)
        if not vendor:
            vendor_name = plan.get("vendor", "")
            if vendor_name:
                vendor = db_reader.get_vendor_by_name(self.db_path, vendor_name)

        if not vendor:
            return {
                "status": "error",
                "agent": self.agent_name,
                "data": {"message": "Leverandør ikke funnet for e-postutkast."},
            }

        email_text = draft_vendor_mobilization_email(
            vendor_name=vendor.get("name", "N/A"),
            contact_person=vendor.get("contact_person", "N/A"),
            contact_email=vendor.get("contact_email", "N/A"),
            frame_agreement_id=vendor.get("frame_agreement_id", "N/A"),
            equipment_tag=plan.get("equipment_tag", params.get("equipment_tag", "N/A")),
            platform_name=plan.get("platform", params.get("platform_name", "N/A")),
            job_description=plan.get("title", params.get("job_description", "N/A")),
            mob_deadline=plan.get("vendor_mob_deadline", params.get("mob_deadline", "N/A")),
            job_id=plan.get("job_id", params.get("job_id", "N/A")),
        )

        return {
            "status": "ok",
            "agent": self.agent_name,
            "data": {
                "email_type": "mobilization_request",
                "vendor": vendor.get("name"),
                "to": vendor.get("contact_email"),
                "email_text": email_text,
            },
        }

    def _draft_delay_email(self, params: dict) -> dict:
        """Draft a vendor delay acknowledgment and escalation email."""
        plan = params.get("plan", {})
        vendor_id = plan.get("vendor_id") or params.get("vendor_id")
        vendor = None
        if vendor_id:
            vendor = db_reader.get_vendor(self.db_path, vendor_id)
        if not vendor:
            vendor_name = plan.get("vendor", "") or params.get("vendor_name", "")
            if vendor_name:
                vendor = db_reader.get_vendor_by_name(self.db_path, vendor_name)

        if not vendor:
            return {
                "status": "error",
                "agent": self.agent_name,
                "data": {"message": "Leverandør ikke funnet for forsinkelsese-post."},
            }

        delay_days = params.get("delay_days", 0)
        part_id = params.get("part_id", "")
        part_description = params.get("part_description", part_id)
        original_date = params.get("original_delivery_date", plan.get("proposed_start", "N/A"))
        new_date = params.get("new_delivery_date", "N/A")

        email_text = draft_vendor_delay_acknowledgment_email(
            vendor_name=vendor.get("name", "N/A"),
            contact_person=vendor.get("contact_person", "N/A"),
            frame_agreement_id=vendor.get("frame_agreement_id", "N/A"),
            equipment_tag=plan.get("equipment_tag", params.get("equipment_tag", "N/A")),
            platform_name=plan.get("platform", params.get("platform_name", "N/A")),
            part_description=part_description,
            delay_days=delay_days,
            original_date=original_date,
            new_date=new_date,
            job_id=plan.get("job_id", params.get("job_id", "N/A")),
        )

        return {
            "status": "ok",
            "agent": self.agent_name,
            "data": {
                "email_type": "delay_acknowledgment",
                "vendor": vendor.get("name"),
                "to": vendor.get("contact_email"),
                "email_text": email_text,
            },
        }

    def _check_lead_times(self, params: dict) -> dict:
        """Check lead times for a list of part IDs against a required delivery date."""
        part_ids = params.get("part_ids", [])
        required_date_str = params.get("required_date", "")

        try:
            required_date = datetime.strptime(required_date_str, "%Y-%m-%d") if required_date_str else None
        except ValueError:
            required_date = None

        today = datetime.today()
        results = []
        for part_id in part_ids:
            part = db_reader.get_spare_part(self.db_path, part_id)
            if not part:
                results.append({
                    "part_id": part_id,
                    "status": "not_found",
                    "message": f"Del ikke funnet: {part_id}",
                })
                continue

            qty = part.get("stock_quantity", 0) or 0
            if qty > 0:
                results.append({
                    "part_id": part_id,
                    "description": part.get("description"),
                    "status": "in_stock",
                    "stock_quantity": qty,
                    "stock_location": part.get("stock_location"),
                    "delivery_risk": False,
                })
            else:
                lead_days = part.get("lead_time_days", 90)
                earliest_delivery = today + timedelta(days=lead_days)
                delivery_risk = required_date is not None and earliest_delivery > required_date
                results.append({
                    "part_id": part_id,
                    "description": part.get("description"),
                    "status": "not_in_stock",
                    "lead_time_days": lead_days,
                    "earliest_delivery": earliest_delivery.strftime("%Y-%m-%d"),
                    "delivery_risk": delivery_risk,
                })

        return {
            "status": "ok",
            "agent": self.agent_name,
            "data": {"parts_lead_time_check": results},
        }
