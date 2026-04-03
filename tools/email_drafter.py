"""
Email drafting utility — generates vendor follow-up emails.
Provides both AI-generated (via Anthropic API) and template-based fallback emails.
"""

import os
from typing import Optional


def draft_vendor_mobilization_email(
    vendor_name: str,
    contact_person: str,
    contact_email: str,
    frame_agreement_id: str,
    equipment_tag: str,
    platform_name: str,
    job_description: str,
    mob_deadline: str,
    job_id: str,
) -> str:
    """
    Draft a vendor mobilization request email using the Anthropic API.
    Falls back to a template if the API call fails.
    """
    prompt_content = (
        f"Draft a professional vendor mobilization request email with the following details:\n\n"
        f"Vendor: {vendor_name}\n"
        f"Contact Person: {contact_person}\n"
        f"Frame Agreement: {frame_agreement_id}\n"
        f"Equipment Tag: {equipment_tag}\n"
        f"Platform: {platform_name}\n"
        f"Job Description: {job_description}\n"
        f"Job Reference: {job_id}\n"
        f"Required Mobilization Date: {mob_deadline}\n\n"
        f"The email should be professional, concise, and reference the frame agreement. "
        f"Do not use bullet points in the email body. "
        f"The email should request confirmation of mobilization capacity and technician names."
    )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=600,
                system=(
                    "You are an expert offshore maintenance coordinator at Equinor. "
                    "Draft a professional vendor coordination email in English. "
                    "Be concise and specific. Include: frame agreement reference, "
                    "equipment tag, platform name, required mobilization date, "
                    "and a clear action request. Do not use bullet points in the email body."
                ),
                messages=[{"role": "user", "content": prompt_content}],
            )
            return response.content[0].text
        except Exception:
            pass  # Fall through to template

    # Template-based fallback
    return _mobilization_email_template(
        vendor_name=vendor_name,
        contact_person=contact_person,
        frame_agreement_id=frame_agreement_id,
        equipment_tag=equipment_tag,
        platform_name=platform_name,
        job_description=job_description,
        mob_deadline=mob_deadline,
        job_id=job_id,
    )


def draft_vendor_delay_acknowledgment_email(
    vendor_name: str,
    contact_person: str,
    frame_agreement_id: str,
    equipment_tag: str,
    platform_name: str,
    part_description: str,
    delay_days: int,
    original_date: str,
    new_date: str,
    job_id: str,
) -> str:
    """
    Draft a vendor delay acknowledgment and escalation email using the Anthropic API.
    Falls back to a template if the API call fails.
    """
    prompt_content = (
        f"Draft a formal delay acknowledgment and escalation email with the following details:\n\n"
        f"Vendor: {vendor_name}\n"
        f"Contact Person: {contact_person}\n"
        f"Frame Agreement: {frame_agreement_id}\n"
        f"Equipment Tag: {equipment_tag}\n"
        f"Platform: {platform_name}\n"
        f"Delayed Part: {part_description}\n"
        f"Delay: {delay_days} days\n"
        f"Original Delivery Date: {original_date}\n"
        f"New Delivery Date: {new_date}\n"
        f"Job Reference: {job_id}\n\n"
        f"The email should formally acknowledge the delay, state the impact on the job schedule, "
        f"and request a formal written confirmation and escalation plan from the vendor. "
        f"Reference the frame agreement. Do not use bullet points in the email body."
    )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=700,
                system=(
                    "You are an expert offshore maintenance coordinator at Equinor. "
                    "Draft a professional vendor coordination email in English. "
                    "Be concise and specific. Include: frame agreement reference, "
                    "equipment tag, platform name, required mobilization date, "
                    "and a clear action request. Do not use bullet points in the email body."
                ),
                messages=[{"role": "user", "content": prompt_content}],
            )
            return response.content[0].text
        except Exception:
            pass  # Fall through to template

    # Template-based fallback
    return _delay_acknowledgment_template(
        vendor_name=vendor_name,
        contact_person=contact_person,
        frame_agreement_id=frame_agreement_id,
        equipment_tag=equipment_tag,
        platform_name=platform_name,
        part_description=part_description,
        delay_days=delay_days,
        original_date=original_date,
        new_date=new_date,
        job_id=job_id,
    )


def _mobilization_email_template(
    vendor_name: str,
    contact_person: str,
    frame_agreement_id: str,
    equipment_tag: str,
    platform_name: str,
    job_description: str,
    mob_deadline: str,
    job_id: str,
) -> str:
    """Template-based mobilization request email."""
    return f"""Subject: Mobilization Request — {equipment_tag} / {platform_name} / {job_id}

Dear {contact_person},

I am writing to request mobilization of field service technicians for upcoming maintenance work on {platform_name}, in accordance with Frame Agreement {frame_agreement_id}.

The scope of work is: {job_description} on equipment tag {equipment_tag}. This work is classified as high-priority maintenance and is scheduled to commence {mob_deadline}, with an estimated duration of 14–15 days offshore.

We request that you confirm availability of the required field service team (4 technicians including a lead engineer) no later than 7 days prior to the mobilization date. Please provide the names, certifications (BOSIET, H2S, GWO), and offshore experience profiles for all proposed personnel.

All work shall be executed in accordance with Equinor's offshore safety requirements, applicable PTW procedures, and the vendor's approved maintenance procedures. Scope details and technical documentation will be shared via Equinor's document control system upon confirmation.

Please acknowledge receipt of this request and confirm mobilization capacity at your earliest convenience. Reference job number {job_id} in all correspondence.

Best regards,

Equinor — Offshore Maintenance Coordination
Roterende Utstyr / Rotating Equipment Department
"""


def _delay_acknowledgment_template(
    vendor_name: str,
    contact_person: str,
    frame_agreement_id: str,
    equipment_tag: str,
    platform_name: str,
    part_description: str,
    delay_days: int,
    original_date: str,
    new_date: str,
    job_id: str,
) -> str:
    """Template-based delay acknowledgment email."""
    return f"""Subject: FORMAL NOTICE — Delivery Delay / {equipment_tag} / {platform_name} / {job_id}

Dear {contact_person},

We formally acknowledge receipt of your notification regarding a {delay_days}-day delivery delay for {part_description}, associated with job {job_id} on {platform_name} (equipment tag: {equipment_tag}), under Frame Agreement {frame_agreement_id}.

The original delivery date was {original_date}. The revised delivery date per your notification is {new_date}. This delay has a direct impact on the planned maintenance window and requires immediate replanning of the job schedule, crew mobilization, and POB allocation on {platform_name}.

We require a formal written Root Cause Analysis and escalation plan from {vendor_name} within 5 business days, including measures to prevent further delays. We also request a commitment to priority handling of the delivery and a named accountable contact for daily status updates until the part is delivered and confirmed fit for purpose.

Please be advised that under Frame Agreement {frame_agreement_id}, Equinor reserves the right to apply applicable contractual remedies should the delay result in demonstrable production or cost impact.

We expect your written confirmation and escalation plan by return.

Best regards,

Equinor — Offshore Maintenance Coordination
Roterende Utstyr / Rotating Equipment Department
"""
