from __future__ import annotations

import html
import re
from pathlib import Path
from urllib.parse import urlparse


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "untitled-business"


def parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "y"}


def bool_to_csv(value: bool) -> str:
    return "yes" if value else "no"


def digits_only(value: str) -> str:
    return re.sub(r"\D+", "", value or "")


def tel_href(value: str) -> str:
    digits = digits_only(value)
    return f"tel:{digits}" if digits else "#"


def html_escape(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def directory_url(base_url: str | None, slug: str) -> str:
    if not base_url:
        return ""
    return f"{base_url.rstrip('/')}/{slug}/"


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def infer_trade(raw_trade: str, category: str = "", source_query: str = "") -> str:
    haystack = " ".join(part.lower() for part in [raw_trade, category, source_query] if part)
    if any(token in haystack for token in ["landscape", "lawn", "yard", "hardscape", "garden"]):
        return "landscaper"
    if any(
        token in haystack
        for token in [
            "water heater",
            "tankless",
            "heating",
            "cooling",
            "hvac",
            "air conditioning",
        ]
    ):
        return "water_heater_repair"
    if "plumb" in haystack or "drain" in haystack or "sewer" in haystack or "rooter" in haystack:
        return "plumber"
    return "local_service"


def normalize_business_status(value: str) -> str:
    text = (value or "").strip().lower().replace(" ", "_")
    if text in {"open", "unknown", "temporarily_closed", "permanently_closed"}:
        return text
    if not text:
        return "unknown"
    return "unknown"


def normalize_website_verification_status(value: str) -> str:
    text = (value or "").strip().lower().replace(" ", "_")
    allowed = {
        "not_checked",
        "found_on_google_maps",
        "found_by_search",
        "verified_no_website",
        "needs_manual_review",
        "search_error",
    }
    if text in allowed:
        return text
    if not text:
        return "not_checked"
    return "needs_manual_review"


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", (value or "").lower())).strip()


def tokenize_business_name(value: str) -> list[str]:
    legal_suffixes = {
        "llc",
        "inc",
        "co",
        "corp",
        "corporation",
        "company",
        "ltd",
        "pllc",
        "pc",
    }
    tokens = [token for token in normalize_text(value).split() if len(token) >= 3]
    return [token for token in tokens if token not in legal_suffixes]


def domain_from_url(url: str) -> str:
    parsed = urlparse((url or "").strip())
    netloc = parsed.netloc.lower()
    if not netloc and parsed.path and "://" not in parsed.path:
        netloc = parsed.path.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc
