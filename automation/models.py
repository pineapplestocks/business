from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .utils import (
    bool_to_csv,
    infer_trade,
    normalize_business_status,
    normalize_website_verification_status,
    parse_bool,
    slugify,
)


CSV_FIELDS = [
    "source",
    "source_query",
    "trade",
    "business_name",
    "slug",
    "phone",
    "category",
    "rating",
    "review_count",
    "address",
    "city",
    "state",
    "google_maps_url",
    "google_maps_website_url",
    "search_query",
    "search_website_url",
    "search_website_title",
    "search_website_snippet",
    "search_has_website",
    "website_url",
    "has_website",
    "website_verification_status",
    "website_verification_notes",
    "business_status",
    "generated_site_url",
    "generated_site_path",
    "pitch_status",
    "last_called_on",
    "notes",
]


@dataclass(slots=True)
class Lead:
    source: str = "google_maps"
    source_query: str = ""
    trade: str = ""
    business_name: str = ""
    slug: str = ""
    phone: str = ""
    category: str = ""
    rating: str = ""
    review_count: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    google_maps_url: str = ""
    google_maps_website_url: str = ""
    search_query: str = ""
    search_website_url: str = ""
    search_website_title: str = ""
    search_website_snippet: str = ""
    search_has_website: bool = False
    website_url: str = ""
    has_website: bool = False
    website_verification_status: str = "not_checked"
    website_verification_notes: str = ""
    business_status: str = "unknown"
    generated_site_url: str = ""
    generated_site_path: str = ""
    pitch_status: str = "new"
    last_called_on: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        self.slug = self.slug or slugify(self.business_name)
        self.trade = infer_trade(self.trade, self.category, self.source_query)
        self.business_status = normalize_business_status(self.business_status)
        self.website_verification_status = normalize_website_verification_status(self.website_verification_status)
        self.refresh_website_fields()

    def refresh_website_fields(self) -> None:
        legacy_url = self.website_url.strip()
        if not self.google_maps_website_url and self.has_website and legacy_url and not self.search_website_url:
            self.google_maps_website_url = legacy_url

        resolved_url = ""
        if self.google_maps_website_url:
            resolved_url = self.google_maps_website_url
        elif self.search_website_url:
            resolved_url = self.search_website_url
        elif legacy_url:
            resolved_url = legacy_url

        self.website_url = resolved_url
        self.search_has_website = bool(self.search_has_website or self.search_website_url)
        self.has_website = bool(
            self.google_maps_website_url or self.search_website_url or self.search_has_website or legacy_url
        )

        if self.google_maps_website_url:
            self.website_verification_status = "found_on_google_maps"
        elif self.search_website_url:
            self.website_verification_status = "found_by_search"
        else:
            self.website_verification_status = normalize_website_verification_status(self.website_verification_status)

    def is_verified_no_website(self) -> bool:
        return self.website_verification_status == "verified_no_website" and not self.has_website

    def qualifies_for_pitch(self, *, include_unknown_status: bool = False) -> bool:
        allowed_statuses = {"open"}
        if include_unknown_status:
            allowed_statuses.add("unknown")
        return (
            self.phone != ""
            and self.business_status in allowed_statuses
            and self.is_verified_no_website()
        )

    @classmethod
    def from_row(cls, row: dict[str, str]) -> "Lead":
        return cls(
            source=row.get("source") or "google_maps",
            source_query=row.get("source_query") or "",
            trade=row.get("trade") or "",
            business_name=row.get("business_name") or "",
            slug=row.get("slug") or "",
            phone=row.get("phone") or "",
            category=row.get("category") or "",
            rating=row.get("rating") or "",
            review_count=row.get("review_count") or "",
            address=row.get("address") or "",
            city=row.get("city") or "",
            state=row.get("state") or "",
            google_maps_url=row.get("google_maps_url") or "",
            google_maps_website_url=(
                row.get("google_maps_website_url") or (row.get("website_url") or "")
            ),
            search_query=row.get("search_query") or "",
            search_website_url=row.get("search_website_url") or "",
            search_website_title=row.get("search_website_title") or "",
            search_website_snippet=row.get("search_website_snippet") or "",
            search_has_website=parse_bool(row.get("search_has_website") or ""),
            website_url=row.get("website_url") or "",
            has_website=parse_bool(row.get("has_website") or ""),
            website_verification_status=row.get("website_verification_status") or "not_checked",
            website_verification_notes=row.get("website_verification_notes") or "",
            business_status=row.get("business_status") or "unknown",
            generated_site_url=row.get("generated_site_url") or "",
            generated_site_path=row.get("generated_site_path") or "",
            pitch_status=row.get("pitch_status") or "new",
            last_called_on=row.get("last_called_on") or "",
            notes=row.get("notes") or "",
        )

    def to_row(self) -> dict[str, str]:
        return {
            "source": self.source,
            "source_query": self.source_query,
            "trade": self.trade,
            "business_name": self.business_name,
            "slug": self.slug,
            "phone": self.phone,
            "category": self.category,
            "rating": self.rating,
            "review_count": self.review_count,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "google_maps_url": self.google_maps_url,
            "google_maps_website_url": self.google_maps_website_url,
            "search_query": self.search_query,
            "search_website_url": self.search_website_url,
            "search_website_title": self.search_website_title,
            "search_website_snippet": self.search_website_snippet,
            "search_has_website": bool_to_csv(self.search_has_website),
            "website_url": self.website_url,
            "has_website": bool_to_csv(self.has_website),
            "website_verification_status": self.website_verification_status,
            "website_verification_notes": self.website_verification_notes,
            "business_status": self.business_status,
            "generated_site_url": self.generated_site_url,
            "generated_site_path": self.generated_site_path,
            "pitch_status": self.pitch_status,
            "last_called_on": self.last_called_on,
            "notes": self.notes,
        }


def read_leads(path: Path) -> list[Lead]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [Lead.from_row(row) for row in reader]


def write_leads(path: Path, leads: Iterable[Lead]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for lead in leads:
            writer.writerow(lead.to_row())


def dedupe_leads(leads: Iterable[Lead]) -> list[Lead]:
    seen: set[str] = set()
    unique: list[Lead] = []
    for lead in leads:
        dedupe_key = lead.google_maps_url or f"{lead.business_name.lower()}::{lead.phone}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        unique.append(lead)
    return unique
