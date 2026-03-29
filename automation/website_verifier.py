from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from typing import Iterable
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen

from .models import Lead
from .utils import domain_from_url, normalize_text, tokenize_business_name


IGNORED_WEBSITE_DOMAINS = {
    "angi.com",
    "bbb.org",
    "birdeye.com",
    "bizapedia.com",
    "bestprosintown.com",
    "chamberofcommerce.com",
    "direct.us",
    "duckduckgo.com",
    "facebook.com",
    "foursquare.com",
    "homeadvisor.com",
    "houzz.com",
    "instagram.com",
    "linkedin.com",
    "mapquest.com",
    "manta.com",
    "nextdoor.com",
    "porch.com",
    "superpages.com",
    "thumbtack.com",
    "tripadvisor.com",
    "x.com",
    "yelp.com",
    "yellowpages.com",
    "youtube.com",
}

IGNORED_WEBSITE_DOMAIN_FRAGMENTS = {
    "direct.us",
    "hardhat.com",
}

DIRECTORY_TITLE_MARKERS = {
    "angi",
    "bestprosintown",
    "birdeye",
    "chamber of commerce",
    "facebook",
    "mapquest",
    "nextdoor",
    "thumbtack",
    "yelp",
    "yellow pages",
}


@dataclass(slots=True)
class SearchResult:
    title: str = ""
    url: str = ""
    snippet: str = ""
    domain: str = ""


class DuckDuckGoHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[SearchResult] = []
        self.current: SearchResult | None = None
        self.active_field: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        classes = set((attr_map.get("class") or "").split())
        if tag == "a" and "result__a" in classes:
            if self.current and self.current.url:
                self.results.append(self.current)
            self.current = SearchResult(url=_decode_duckduckgo_href(attr_map.get("href") or ""))
            self.active_field = "title"
            return
        if tag == "a" and "result__snippet" in classes and self.current:
            self.active_field = "snippet"
            return

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            self.active_field = None

    def handle_data(self, data: str) -> None:
        if not self.current or not self.active_field:
            return
        value = unescape(data or "").strip()
        if not value:
            return
        if self.active_field == "title":
            self.current.title = f"{self.current.title} {value}".strip()
        elif self.active_field == "snippet":
            self.current.snippet = f"{self.current.snippet} {value}".strip()

    def close(self) -> list[SearchResult]:  # type: ignore[override]
        super().close()
        if self.current and self.current.url:
            self.results.append(self.current)
            self.current = None
        for result in self.results:
            result.domain = domain_from_url(result.url)
        return self.results


def _decode_duckduckgo_href(href: str) -> str:
    value = (href or "").strip()
    if not value:
        return ""
    if value.startswith("//"):
        value = f"https:{value}"
    parsed = urlparse(value)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        query = parse_qs(parsed.query)
        uddg = query.get("uddg", [""])[0]
        return unquote(uddg)
    return value


def _build_search_queries(lead: Lead) -> list[str]:
    location = " ".join(part for part in [lead.city, lead.state] if part).strip()
    queries = []
    if location:
        queries.append(f'"{lead.business_name}" {location}')
        queries.append(f"{lead.business_name} {location}")
    queries.append(f'"{lead.business_name}"')
    if lead.phone:
        queries.append(f'"{lead.business_name}" "{lead.phone}"')

    unique: list[str] = []
    seen: set[str] = set()
    for query in queries:
        key = query.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(query)
    return unique


def _is_ignored_domain(domain: str) -> bool:
    if any(domain == ignored or domain.endswith(f".{ignored}") for ignored in IGNORED_WEBSITE_DOMAINS):
        return True
    return any(fragment in domain for fragment in IGNORED_WEBSITE_DOMAIN_FRAGMENTS)


def _matches_official_site(lead: Lead, result: SearchResult) -> str:
    domain = result.domain
    if not domain or _is_ignored_domain(domain):
        return "ignore"

    business_tokens = tokenize_business_name(lead.business_name)
    if not business_tokens:
        return "ambiguous"

    title_text = normalize_text(result.title)
    snippet_text = normalize_text(result.snippet)
    domain_text = normalize_text(domain.replace(".", " "))
    combined = " ".join(part for part in [title_text, snippet_text, domain_text] if part)
    normalized_name = normalize_text(lead.business_name)
    token_overlap = sum(1 for token in business_tokens if token in combined)
    required_overlap = max(2, min(len(business_tokens), 3))

    if any(marker in combined for marker in DIRECTORY_TITLE_MARKERS):
        return "ignore"

    if normalized_name and normalized_name in combined:
        return "official"
    if token_overlap >= required_overlap:
        return "official"
    if token_overlap >= 1:
        return "ambiguous"
    return "ignore"


class WebsiteVerifier:
    def __init__(self, *, max_results_per_query: int = 5, timeout: int = 20) -> None:
        self.max_results_per_query = max_results_per_query
        self.timeout = timeout

    def verify_leads(self, leads: Iterable[Lead]) -> list[Lead]:
        return [self.verify_lead(lead) for lead in leads]

    def verify_lead(self, lead: Lead) -> Lead:
        lead.search_query = ""
        lead.search_website_url = ""
        lead.search_website_title = ""
        lead.search_website_snippet = ""
        lead.search_has_website = False

        if lead.google_maps_website_url:
            lead.website_verification_status = "found_on_google_maps"
            lead.website_verification_notes = "Google Maps listed a website directly."
            lead.refresh_website_fields()
            return lead

        ambiguous_result: SearchResult | None = None
        successful_queries = 0

        for query in _build_search_queries(lead):
            results = self.search(query)
            if results is None:
                continue

            successful_queries += 1
            for result in results[: self.max_results_per_query]:
                match_type = _matches_official_site(lead, result)
                if match_type == "official":
                    lead.search_query = query
                    lead.search_website_url = result.url
                    lead.search_website_title = result.title
                    lead.search_website_snippet = result.snippet
                    lead.search_has_website = True
                    lead.website_verification_status = "found_by_search"
                    lead.website_verification_notes = "Search results found a likely official website."
                    lead.refresh_website_fields()
                    return lead
                if match_type == "ambiguous" and ambiguous_result is None:
                    ambiguous_result = result

        if successful_queries == 0:
            lead.website_verification_status = "search_error"
            lead.website_verification_notes = "Search verification failed and needs a retry."
        elif ambiguous_result is not None:
            lead.search_website_url = ambiguous_result.url
            lead.search_website_title = ambiguous_result.title
            lead.search_website_snippet = ambiguous_result.snippet
            lead.website_verification_status = "needs_manual_review"
            lead.website_verification_notes = (
                "Search found a non-directory candidate that could not be confirmed automatically."
            )
        else:
            lead.website_verification_status = "verified_no_website"
            lead.website_verification_notes = (
                "No website on Google Maps and no likely official website found in web search."
            )

        lead.refresh_website_fields()
        return lead

    def search(self, query: str) -> list[SearchResult] | None:
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                html = response.read().decode("utf-8", errors="ignore")
        except Exception:
            return None

        parser = DuckDuckGoHTMLParser()
        parser.feed(html)
        results = parser.close()
        return [result for result in results if result.url]
