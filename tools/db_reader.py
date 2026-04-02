"""
Shared utility for reading and writing the JSON database files.
All agents use this module to access data — no direct file reads outside this module.
"""

import json
import os
from typing import Any, Optional


def load_json(db_path: str, filename: str) -> list | dict:
    """Load a JSON database file from the database directory."""
    filepath = os.path.join(db_path, "database", filename)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"status": "error", "message": f"Databasefil ikke funnet: {filename}"}
    except json.JSONDecodeError as e:
        return {"status": "error", "message": f"JSON-feil i {filename}: {str(e)}"}


def get_equipment(db_path: str, tag: str) -> Optional[dict]:
    """Fetch a single equipment record by tag number."""
    equipment_list = load_json(db_path, "equipment.json")
    if isinstance(equipment_list, dict):  # error dict returned
        return None
    for item in equipment_list:
        if item.get("tag", "").upper() == tag.upper():
            return item
    return None


def get_all_equipment(db_path: str) -> list:
    """Fetch all equipment records."""
    result = load_json(db_path, "equipment.json")
    if isinstance(result, dict):
        return []
    return result


def get_platform(db_path: str, platform_id: str) -> Optional[dict]:
    """Fetch a single platform record by platform_id."""
    platforms = load_json(db_path, "platforms.json")
    if isinstance(platforms, dict):
        return None
    for p in platforms:
        if p.get("platform_id", "").upper() == platform_id.upper():
            return p
    return None


def get_vendor(db_path: str, vendor_id: str) -> Optional[dict]:
    """Fetch a single vendor record by vendor_id."""
    vendors = load_json(db_path, "vendors.json")
    if isinstance(vendors, dict):
        return None
    for v in vendors:
        if v.get("vendor_id", "").upper() == vendor_id.upper():
            return v
    return None


def get_vendor_by_name(db_path: str, name_fragment: str) -> Optional[dict]:
    """Fetch a vendor by partial name match (case-insensitive)."""
    vendors = load_json(db_path, "vendors.json")
    if isinstance(vendors, dict):
        return None
    name_lower = name_fragment.lower()
    for v in vendors:
        if name_lower in v.get("name", "").lower() or name_lower in v.get("short_name", "").lower():
            return v
    return None


def get_all_vendors(db_path: str) -> list:
    """Fetch all vendor records."""
    result = load_json(db_path, "vendors.json")
    if isinstance(result, dict):
        return []
    return result


def get_work_orders_for_equipment(db_path: str, tag: str, limit: int = 5) -> list:
    """Fetch work orders for a given equipment tag, sorted by start_date descending."""
    work_orders = load_json(db_path, "work_orders.json")
    if isinstance(work_orders, dict):
        return []
    matching = [wo for wo in work_orders if wo.get("equipment_tag", "").upper() == tag.upper()]
    # Sort by start_date descending (nulls last)
    matching.sort(key=lambda x: x.get("start_date") or "0000-00-00", reverse=True)
    return matching[:limit]


def get_all_work_orders(db_path: str) -> list:
    """Fetch all work order records."""
    result = load_json(db_path, "work_orders.json")
    if isinstance(result, dict):
        return []
    return result


def get_open_work_orders(db_path: str) -> list:
    """Fetch work orders with status not TECO or CLSD (i.e., still active)."""
    work_orders = load_json(db_path, "work_orders.json")
    if isinstance(work_orders, dict):
        return []
    closed_statuses = {"TECO", "CLSD"}
    return [wo for wo in work_orders if wo.get("status") not in closed_statuses]


def get_job_template(db_path: str, template_id: str) -> Optional[dict]:
    """Fetch a job template by template_id."""
    templates = load_json(db_path, "job_templates.json")
    if isinstance(templates, dict) and "status" in templates:
        return None
    return templates.get(template_id)


def get_spare_parts_for_equipment(db_path: str, tag: str) -> list:
    """Fetch all spare parts associated with a given equipment tag."""
    parts = load_json(db_path, "spare_parts.json")
    if isinstance(parts, dict):
        return []
    return [p for p in parts if tag.upper() in [t.upper() for t in p.get("equipment_tags", [])]]


def get_spare_part(db_path: str, part_id: str) -> Optional[dict]:
    """Fetch a single spare part by part_id."""
    parts = load_json(db_path, "spare_parts.json")
    if isinstance(parts, dict):
        return None
    for p in parts:
        if p.get("part_id", "").upper() == part_id.upper():
            return p
    return None


def get_personnel_for_platform(db_path: str, platform_id: str) -> list:
    """Fetch all personnel assigned to a platform."""
    personnel = load_json(db_path, "personnel.json")
    if isinstance(personnel, dict):
        return []
    return [p for p in personnel if p.get("platform_id") == platform_id]


def get_all_personnel(db_path: str) -> list:
    """Fetch all personnel records."""
    result = load_json(db_path, "personnel.json")
    if isinstance(result, dict):
        return []
    return result


def get_vendor_personnel(db_path: str, vendor_name_fragment: str) -> list:
    """Fetch vendor personnel by company name fragment."""
    personnel = load_json(db_path, "personnel.json")
    if isinstance(personnel, dict):
        return []
    name_lower = vendor_name_fragment.lower()
    return [
        p for p in personnel
        if p.get("vendor_personnel") and name_lower in p.get("company", "").lower()
    ]
