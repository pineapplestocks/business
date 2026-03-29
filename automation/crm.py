from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import Lead, read_leads


CRM_EDITABLE_FIELDS = {
    "pitch_status",
    "call_outcome",
    "last_called_on",
    "next_follow_up_on",
    "owner_name",
    "owner_email",
    "quoted_price",
    "sale_amount",
    "sale_date",
    "call_summary",
    "notes",
}

PITCH_STATUS_OPTIONS = [
    "new",
    "attempting_contact",
    "contacted",
    "follow_up",
    "interested",
    "proposal_sent",
    "won",
    "lost",
    "do_not_call",
]

CALL_OUTCOME_OPTIONS = [
    "not_called",
    "no_answer",
    "left_voicemail",
    "bad_number",
    "spoke_needs_follow_up",
    "not_interested",
    "demo_sent",
    "sold",
]


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def crm_record_id(lead: Lead) -> str:
    key = lead.google_maps_url or "|".join(
        [
            lead.business_name.strip().lower(),
            lead.phone.strip(),
            lead.city.strip().lower(),
            lead.state.strip().lower(),
        ]
    )
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def base_record_from_lead(lead: Lead) -> dict[str, Any]:
    timestamp = now_iso()
    return {
        "record_id": crm_record_id(lead),
        "active": True,
        "business_name": lead.business_name,
        "trade": lead.trade,
        "city": lead.city,
        "state": lead.state,
        "phone": lead.phone,
        "category": lead.category,
        "source_query": lead.source_query,
        "google_maps_url": lead.google_maps_url,
        "generated_site_url": lead.generated_site_url,
        "website_verification_status": lead.website_verification_status,
        "website_verification_notes": lead.website_verification_notes,
        "pitch_status": lead.pitch_status or "new",
        "call_outcome": "not_called",
        "last_called_on": "",
        "next_follow_up_on": "",
        "owner_name": "",
        "owner_email": "",
        "quoted_price": "",
        "sale_amount": "",
        "sale_date": "",
        "call_summary": "",
        "notes": lead.notes,
        "created_at": timestamp,
        "updated_at": timestamp,
        "synced_at": timestamp,
    }


def _preserve_existing_fields(record: dict[str, Any], existing: dict[str, Any]) -> dict[str, Any]:
    merged = dict(record)
    for field in CRM_EDITABLE_FIELDS:
        if field in existing:
            merged[field] = existing[field]
    merged["created_at"] = existing.get("created_at") or merged["created_at"]
    merged["updated_at"] = existing.get("updated_at") or merged["updated_at"]
    merged["synced_at"] = now_iso()
    return merged


def load_crm_store(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"updated_at": "", "records": []}
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, list):
        return {"updated_at": "", "records": data}
    data.setdefault("records", [])
    return data


def save_crm_store(path: Path, store: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(store)
    payload["updated_at"] = now_iso()
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True)
        handle.write("\n")


def sync_crm_store(
    *,
    leads_path: Path,
    store_path: Path,
    include_unknown_status: bool = False,
) -> dict[str, Any]:
    leads = read_leads(leads_path)
    qualifying = [lead for lead in leads if lead.qualifies_for_pitch(include_unknown_status=include_unknown_status)]

    store = load_crm_store(store_path)
    existing_by_id = {record["record_id"]: record for record in store.get("records", [])}
    active_ids: set[str] = set()
    records: list[dict[str, Any]] = []

    for lead in sorted(qualifying, key=lambda item: (item.city, item.trade, item.business_name)):
        base = base_record_from_lead(lead)
        record_id = base["record_id"]
        active_ids.add(record_id)
        if record_id in existing_by_id:
            base = _preserve_existing_fields(base, existing_by_id[record_id])
        records.append(base)

    for record_id, existing in existing_by_id.items():
        if record_id in active_ids:
            continue
        archived = dict(existing)
        archived["active"] = False
        archived["synced_at"] = now_iso()
        records.append(archived)

    next_store = {
        "source_file": str(leads_path),
        "records": sorted(
            records,
            key=lambda record: (
                not record.get("active", True),
                record.get("pitch_status", ""),
                record.get("city", ""),
                record.get("business_name", ""),
            ),
        ),
    }
    save_crm_store(store_path, next_store)
    return next_store


def update_crm_record(store_path: Path, record_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    store = load_crm_store(store_path)
    allowed_updates = {key: value for key, value in updates.items() if key in CRM_EDITABLE_FIELDS}

    for record in store.get("records", []):
        if record.get("record_id") != record_id:
            continue
        record.update(allowed_updates)
        record["updated_at"] = now_iso()
        save_crm_store(store_path, store)
        return record

    raise KeyError(record_id)


def crm_stats(records: list[dict[str, Any]]) -> dict[str, Any]:
    active_records = [record for record in records if record.get("active", True)]
    pitch_counter = Counter(record.get("pitch_status", "new") for record in active_records)
    won = sum(1 for record in active_records if record.get("pitch_status") == "won")
    follow_up = sum(1 for record in active_records if record.get("next_follow_up_on"))
    return {
        "total": len(active_records),
        "won": won,
        "follow_up": follow_up,
        "by_pitch_status": dict(sorted(pitch_counter.items())),
    }


def export_crm_records_to_csv(store_path: Path, output_path: Path) -> None:
    store = load_crm_store(store_path)
    fields = [
        "business_name",
        "trade",
        "city",
        "state",
        "phone",
        "pitch_status",
        "call_outcome",
        "last_called_on",
        "next_follow_up_on",
        "sale_amount",
        "google_maps_url",
        "generated_site_url",
        "notes",
        "call_summary",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in store.get("records", []):
            if not record.get("active", True):
                continue
            writer.writerow({field: record.get(field, "") for field in fields})
