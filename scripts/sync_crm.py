#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from automation.crm import crm_stats
from automation.crm_db import sync_crm_database, write_public_snapshot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Sync the central CRM database from the generated lead CSV while preserving "
            "notes, deal stage, and call history, then write a public snapshot for the static CRM view."
        )
    )
    parser.add_argument("--input", type=Path, default=Path("data/leads.generated.csv"), help="Generated lead CSV.")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/crm.sqlite3"),
        help="CRM SQLite database path.",
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=Path("data/crm_records.json"),
        help="Public CRM snapshot JSON path used by the static CRM view.",
    )
    parser.add_argument(
        "--include-unknown-status",
        action="store_true",
        help="Include unknown-status leads in the CRM store if they otherwise qualify.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    store = sync_crm_database(
        leads_path=args.input,
        db_path=args.db,
        include_unknown_status=args.include_unknown_status,
    )
    write_public_snapshot(
        leads_path=args.input,
        snapshot_path=args.snapshot,
        include_unknown_status=args.include_unknown_status,
    )
    stats = crm_stats(store["records"])
    print(f"Synced CRM database to {args.db}")
    print(f"Wrote public CRM snapshot to {args.snapshot}")
    print(f"Active records: {stats['total']}")
    print(f"Won deals: {stats['won']}")
    print(f"Follow-ups scheduled: {stats['follow_up']}")


if __name__ == "__main__":
    main()
