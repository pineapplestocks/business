from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from .crm import (
    CRM_EDITABLE_FIELDS,
    CRM_RECORD_FIELDS,
    build_crm_store_from_leads,
    build_public_crm_snapshot,
    crm_stats,
    export_records_to_csv,
    load_crm_store,
    now_iso,
    save_crm_store,
)
from .models import read_leads


SQLITE_TIMEOUT_SECONDS = 30


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path, timeout=SQLITE_TIMEOUT_SECONDS)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def ensure_crm_db(db_path: Path) -> None:
    with _connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS crm_records (
                record_id TEXT PRIMARY KEY,
                active INTEGER NOT NULL DEFAULT 1,
                business_name TEXT NOT NULL DEFAULT '',
                trade TEXT NOT NULL DEFAULT '',
                city TEXT NOT NULL DEFAULT '',
                state TEXT NOT NULL DEFAULT '',
                phone TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT '',
                source_query TEXT NOT NULL DEFAULT '',
                google_maps_url TEXT NOT NULL DEFAULT '',
                generated_site_url TEXT NOT NULL DEFAULT '',
                website_verification_status TEXT NOT NULL DEFAULT '',
                website_verification_notes TEXT NOT NULL DEFAULT '',
                pitch_status TEXT NOT NULL DEFAULT 'new',
                call_outcome TEXT NOT NULL DEFAULT 'not_called',
                last_called_on TEXT NOT NULL DEFAULT '',
                next_follow_up_on TEXT NOT NULL DEFAULT '',
                owner_name TEXT NOT NULL DEFAULT '',
                owner_email TEXT NOT NULL DEFAULT '',
                quoted_price TEXT NOT NULL DEFAULT '',
                sale_amount TEXT NOT NULL DEFAULT '',
                sale_date TEXT NOT NULL DEFAULT '',
                call_summary TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT '',
                synced_at TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS crm_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL DEFAULT ''
            );

            CREATE INDEX IF NOT EXISTS idx_crm_records_active_stage_city
            ON crm_records(active, pitch_status, city, business_name);
            """
        )


def _normalize_record_for_db(record: dict[str, Any]) -> dict[str, Any]:
    normalized = {field: record.get(field, "") for field in CRM_RECORD_FIELDS}
    normalized["active"] = 1 if record.get("active", True) else 0
    return normalized


def _row_to_record(row: sqlite3.Row) -> dict[str, Any]:
    record = {field: row[field] for field in CRM_RECORD_FIELDS}
    record["active"] = bool(record.get("active", 1))
    return record


def _meta(connection: sqlite3.Connection, key: str, default: str = "") -> str:
    row = connection.execute("SELECT value FROM crm_meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def _set_meta(connection: sqlite3.Connection, key: str, value: str) -> None:
    connection.execute(
        """
        INSERT INTO crm_meta(key, value)
        VALUES(?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )


def load_crm_store_from_db(db_path: Path) -> dict[str, Any]:
    ensure_crm_db(db_path)
    with _connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM crm_records
            ORDER BY active DESC, pitch_status ASC, city ASC, business_name ASC
            """
        ).fetchall()
        return {
            "source_file": _meta(connection, "source_file", ""),
            "updated_at": _meta(connection, "updated_at", ""),
            "records": [_row_to_record(row) for row in rows],
        }


def save_crm_store_to_db(db_path: Path, store: dict[str, Any]) -> dict[str, Any]:
    ensure_crm_db(db_path)
    timestamp = now_iso()
    with _connect(db_path) as connection:
        connection.execute("DELETE FROM crm_records")
        connection.executemany(
            """
            INSERT INTO crm_records (
                record_id,
                active,
                business_name,
                trade,
                city,
                state,
                phone,
                category,
                source_query,
                google_maps_url,
                generated_site_url,
                website_verification_status,
                website_verification_notes,
                pitch_status,
                call_outcome,
                last_called_on,
                next_follow_up_on,
                owner_name,
                owner_email,
                quoted_price,
                sale_amount,
                sale_date,
                call_summary,
                notes,
                created_at,
                updated_at,
                synced_at
            ) VALUES (
                :record_id,
                :active,
                :business_name,
                :trade,
                :city,
                :state,
                :phone,
                :category,
                :source_query,
                :google_maps_url,
                :generated_site_url,
                :website_verification_status,
                :website_verification_notes,
                :pitch_status,
                :call_outcome,
                :last_called_on,
                :next_follow_up_on,
                :owner_name,
                :owner_email,
                :quoted_price,
                :sale_amount,
                :sale_date,
                :call_summary,
                :notes,
                :created_at,
                :updated_at,
                :synced_at
            )
            """,
            [_normalize_record_for_db(record) for record in store.get("records", [])],
        )
        _set_meta(connection, "source_file", store.get("source_file", ""))
        _set_meta(connection, "updated_at", timestamp)
        connection.commit()

    next_store = dict(store)
    next_store["updated_at"] = timestamp
    return next_store


def import_json_store_to_db(*, store_path: Path, db_path: Path) -> dict[str, Any]:
    store = load_crm_store(store_path)
    return save_crm_store_to_db(db_path, store)


def sync_crm_database(
    *,
    leads_path: Path,
    db_path: Path,
    include_unknown_status: bool = False,
) -> dict[str, Any]:
    leads = read_leads(leads_path)
    existing_store = load_crm_store_from_db(db_path)
    next_store = build_crm_store_from_leads(
        leads=leads,
        existing_records=existing_store.get("records", []),
        source_file=str(leads_path),
        include_unknown_status=include_unknown_status,
    )
    return save_crm_store_to_db(db_path, next_store)


def update_crm_record_in_db(db_path: Path, record_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    ensure_crm_db(db_path)
    allowed_updates = {key: value for key, value in updates.items() if key in CRM_EDITABLE_FIELDS}
    if not allowed_updates:
        store = load_crm_store_from_db(db_path)
        for record in store.get("records", []):
            if record.get("record_id") == record_id:
                return record
        raise KeyError(record_id)

    with _connect(db_path) as connection:
        row = connection.execute(
            "SELECT * FROM crm_records WHERE record_id = ?",
            (record_id,),
        ).fetchone()
        if not row:
            raise KeyError(record_id)

        record = _row_to_record(row)
        record.update(allowed_updates)
        record["updated_at"] = now_iso()

        connection.execute(
            """
            UPDATE crm_records
            SET
                pitch_status = :pitch_status,
                call_outcome = :call_outcome,
                last_called_on = :last_called_on,
                next_follow_up_on = :next_follow_up_on,
                owner_name = :owner_name,
                owner_email = :owner_email,
                quoted_price = :quoted_price,
                sale_amount = :sale_amount,
                sale_date = :sale_date,
                call_summary = :call_summary,
                notes = :notes,
                updated_at = :updated_at
            WHERE record_id = :record_id
            """,
            _normalize_record_for_db(record),
        )
        _set_meta(connection, "updated_at", now_iso())
        connection.commit()
        return record


def write_public_snapshot(
    *,
    leads_path: Path,
    snapshot_path: Path,
    include_unknown_status: bool = False,
) -> dict[str, Any]:
    leads = read_leads(leads_path)
    snapshot = build_public_crm_snapshot(
        leads=leads,
        source_file=str(leads_path),
        include_unknown_status=include_unknown_status,
    )
    save_crm_store(snapshot_path, snapshot)
    return snapshot


def export_crm_database_to_csv(db_path: Path, output_path: Path) -> None:
    store = load_crm_store_from_db(db_path)
    export_records_to_csv(store.get("records", []), output_path)


def crm_database_stats(db_path: Path) -> dict[str, Any]:
    return crm_stats(load_crm_store_from_db(db_path).get("records", []))
