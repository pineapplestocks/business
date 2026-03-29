#!/usr/bin/env python3
"""Sync verified no-website leads from leads.generated.csv into Zoho CRM via live API."""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from automation.models import Lead, read_leads

TOKEN_FILE = REPO_ROOT / ".zoho_token.json"
ZOHO_API_BASE = "https://www.zohoapis.com/crm/v2"
ZOHO_ACCOUNTS_URL = "https://accounts.zoho.com/oauth/v2/token"


# ── token management ─────────────────────────────────────────────────────────

def _load_token() -> dict:
    if not TOKEN_FILE.exists():
        raise SystemExit(
            f"Token file not found: {TOKEN_FILE}\n"
            "Run with --setup to perform the one-time OAuth grant."
        )
    with TOKEN_FILE.open() as f:
        return json.load(f)


def _save_token(data: dict) -> None:
    TOKEN_FILE.write_text(json.dumps(data, indent=2))


def _refresh_access_token(token_data: dict) -> dict:
    params = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "client_id": token_data["client_id"],
        "client_secret": token_data["client_secret"],
        "refresh_token": token_data["refresh_token"],
    }).encode()
    req = urllib.request.Request(ZOHO_ACCOUNTS_URL, data=params, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
    if "access_token" not in result:
        raise SystemExit(f"Token refresh failed: {result}")
    token_data["access_token"] = result["access_token"]
    token_data["expires_at"] = time.time() + int(result.get("expires_in", 3600)) - 60
    _save_token(token_data)
    return token_data


def _get_access_token() -> str:
    data = _load_token()
    if time.time() >= data.get("expires_at", 0):
        data = _refresh_access_token(data)
    return data["access_token"]


def _setup_oauth(client_id: str, client_secret: str, grant_code: str) -> None:
    params = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": grant_code,
    }).encode()
    req = urllib.request.Request(ZOHO_ACCOUNTS_URL, data=params, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
    if "refresh_token" not in result:
        raise SystemExit(f"OAuth grant failed: {result}")
    token_data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": result["refresh_token"],
        "access_token": result.get("access_token", ""),
        "expires_at": time.time() + int(result.get("expires_in", 3600)) - 60,
    }
    _save_token(token_data)
    print(f"OAuth setup complete. Token saved to {TOKEN_FILE}")


# ── Zoho API calls ────────────────────────────────────────────────────────────

def _zoho_request(method: str, path: str, *, access_token: str, body: dict | None = None) -> dict:
    url = f"{ZOHO_API_BASE}/{path.lstrip('/')}"
    data = json.dumps(body).encode() if body else None
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode(errors="replace")
        raise RuntimeError(f"Zoho API {method} {url} -> {exc.code}: {body_text}") from exc


# ── lead mapping ──────────────────────────────────────────────────────────────

def _normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return digits


def _build_description(lead: Lead) -> str:
    parts = ["Verified no-website lead — outbound pipeline."]
    if lead.trade:
        parts.append(f"Trade: {lead.trade.replace('_', ' ').title()}")
    if lead.category:
        parts.append(f"Google Maps category: {lead.category}")
    if lead.rating or lead.review_count:
        rep = " | ".join(p for p in [lead.rating, (f"{lead.review_count} reviews" if lead.review_count else "")] if p)
        parts.append(f"Reputation: {rep}")
    parts.append(f"Business status: {lead.business_status}")
    parts.append(f"Website verification: {lead.website_verification_status}")
    if lead.website_verification_notes:
        parts.append(f"Notes: {lead.website_verification_notes}")
    if lead.generated_site_url:
        parts.append(f"Demo site: {lead.generated_site_url}")
    if lead.google_maps_url:
        parts.append(f"Google Maps: {lead.google_maps_url}")
    return "\n".join(parts)


def _lead_to_zoho(lead: Lead) -> dict:
    name = (lead.business_name.strip() or lead.slug or "Local Business")
    return {
        "Company": name,
        "Last_Name": name,
        "Phone": _normalize_phone(lead.phone),
        "Street": lead.address or "",
        "City": lead.city or "",
        "State": lead.state or "",
        "Lead_Source": "Google Maps — No-Website Pipeline",
        "Lead_Status": "Not Contacted",
        "Description": _build_description(lead),
        "Website": lead.generated_site_url or "",
    }


# ── sync logic ────────────────────────────────────────────────────────────────

def _filter_leads(leads: list[Lead]) -> list[Lead]:
    return [
        lead for lead in leads
        if lead.is_verified_no_website()
        and lead.phone
        and lead.business_status == "open"
        and lead.generated_site_url
    ]


def _upsert_batch(batch: list[Lead], *, access_token: str, dry_run: bool) -> tuple[int, int]:
    """Upsert a batch of leads. Returns (created, updated)."""
    zoho_leads = [_lead_to_zoho(lead) for lead in batch]
    if dry_run:
        for lead in batch:
            print(f"  [dry-run] Would upsert: {lead.business_name} ({lead.city}, {lead.state}) — {lead.phone}")
        return len(batch), 0

    payload = {"data": zoho_leads, "duplicate_check_fields": ["Phone"]}
    result = _zoho_request("POST", "/Leads/upsert", access_token=access_token, body=payload)

    created = updated = 0
    for item in result.get("data", []):
        action = (item.get("details") or {}).get("Modified_Time") and item.get("code") == "SUCCESS"
        # Zoho upsert returns "RECORD_ADDED" or "RECORD_UPDATED" in message or code
        code = item.get("code", "")
        msg = str(item.get("message", "")).lower()
        if code == "SUCCESS":
            if "duplicate" in msg or "update" in msg:
                updated += 1
            else:
                created += 1
        else:
            print(f"  [warn] Zoho response: {item}", file=sys.stderr)
    return created, updated


def sync(leads_path: Path, *, dry_run: bool = False, batch_size: int = 100) -> None:
    leads = read_leads(leads_path)
    pitchable = _filter_leads(leads)

    print(f"Loaded {len(leads)} leads from {leads_path}")
    print(f"Pitchable (verified no-website, open, has phone, has demo site): {len(pitchable)}")
    if not pitchable:
        print("Nothing to sync.")
        return

    access_token = "" if dry_run else _get_access_token()

    total_created = total_updated = 0
    for start in range(0, len(pitchable), batch_size):
        batch = pitchable[start: start + batch_size]
        print(f"Syncing batch {start + 1}–{start + len(batch)} of {len(pitchable)}…")
        created, updated = _upsert_batch(batch, access_token=access_token, dry_run=dry_run)
        total_created += created
        total_updated += updated
        if not dry_run and start + batch_size < len(pitchable):
            time.sleep(0.5)  # stay well under Zoho rate limits

    print(f"\nDone. Created: {total_created} | Updated: {total_updated} | Total synced: {len(pitchable)}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync verified leads to Zoho CRM via live API.")
    parser.add_argument("--input", type=Path, default=Path("data/leads.generated.csv"),
                        help="Generated leads CSV (default: data/leads.generated.csv)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be synced without calling the Zoho API.")
    parser.add_argument("--setup", action="store_true",
                        help="Perform one-time OAuth grant code exchange.")
    parser.add_argument("--client-id", default="",
                        help="Zoho client ID (required with --setup).")
    parser.add_argument("--client-secret", default="",
                        help="Zoho client secret (required with --setup).")
    parser.add_argument("--grant-code", default="",
                        help="Zoho OAuth grant code (required with --setup).")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.setup:
        if not all([args.client_id, args.client_secret, args.grant_code]):
            raise SystemExit("--setup requires --client-id, --client-secret, and --grant-code.")
        _setup_oauth(args.client_id, args.client_secret, args.grant_code)
        return

    sync(args.input, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
