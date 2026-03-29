from __future__ import annotations

from collections.abc import Callable
import re
from dataclasses import dataclass
from urllib.parse import quote_plus

from .models import Lead, dedupe_leads
from .utils import normalize_business_status


try:
    from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright
except ImportError:  # pragma: no cover - handled at runtime with a clearer message.
    Browser = BrowserContext = Page = object  # type: ignore[assignment]
    sync_playwright = None


DETAIL_LINK_SELECTOR = 'a[href*="/maps/place/"]'
ProgressCallback = Callable[[str, dict[str, object]], None]


@dataclass(slots=True)
class SearchQuery:
    query: str
    trade: str = ""
    city: str = ""
    state: str = ""


@dataclass(slots=True)
class ScrapeQueryResult:
    leads: list[Lead]
    seen_existing_keys: set[str]


class GoogleMapsScraper:
    def __init__(
        self,
        *,
        headless: bool = True,
        max_results: int = 25,
        scroll_rounds: int = 12,
        wait_ms: int = 1500,
    ) -> None:
        self.headless = headless
        self.max_results = max_results
        self.scroll_rounds = scroll_rounds
        self.wait_ms = wait_ms
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    def _has_result_capacity(self, count: int) -> bool:
        return self.max_results <= 0 or count < self.max_results

    def _stall_limit_for_count(self, count: int) -> int:
        if self.max_results > 0:
            return self.scroll_rounds

        # In exhaustive mode, stop much sooner once we already have a healthy
        # result set and Google Maps has stopped yielding new cards.
        if count >= 100:
            return min(self.scroll_rounds, 15)
        if count >= 50:
            return min(self.scroll_rounds, 20)
        if count >= 20:
            return min(self.scroll_rounds, 30)
        return self.scroll_rounds

    def __enter__(self) -> "GoogleMapsScraper":
        if sync_playwright is None:
            raise RuntimeError(
                "Playwright is not installed. Run `pip install -r requirements.txt` "
                "and then `python3 -m playwright install chromium`."
            )
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        self._context = self._browser.new_context(
            viewport={"width": 1440, "height": 1000},
            locale="en-US",
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        if self._context is not None:
            self._context.close()
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()

    @property
    def context(self) -> BrowserContext:
        if self._context is None:
            raise RuntimeError("GoogleMapsScraper must be used as a context manager.")
        return self._context

    def scrape(self, searches: list[SearchQuery]) -> list[Lead]:
        leads: list[Lead] = []
        for search in searches:
            leads.extend(self.scrape_query(search).leads)
        return dedupe_leads(leads)

    def scrape_query(
        self,
        search: SearchQuery,
        *,
        existing_keys: set[str] | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> ScrapeQueryResult:
        search_page = self.context.new_page()
        detail_page = self.context.new_page()
        try:
            urls, seen_existing_keys = self._collect_result_urls(
                search_page,
                search.query,
                existing_keys=existing_keys,
                progress_callback=progress_callback,
            )
            if progress_callback is not None:
                progress_callback(
                    "collect_complete",
                    {
                        "query": search.query,
                        "url_count": len(urls),
                        "seen_existing_count": len(seen_existing_keys),
                    },
                )

            leads: list[Lead] = []
            total_urls = len(urls)
            for index, url in enumerate(urls, start=1):
                lead = self._extract_lead(detail_page, url, search)
                if lead is not None:
                    leads.append(lead)
                if progress_callback is not None:
                    progress_callback(
                        "extract_progress",
                        {
                            "query": search.query,
                            "done": index,
                            "total": total_urls,
                            "business_name": lead.business_name if lead is not None else "",
                        },
                    )
            return ScrapeQueryResult(
                leads=leads,
                seen_existing_keys=seen_existing_keys,
            )
        finally:
            detail_page.close()
            search_page.close()

    def _collect_result_urls(
        self,
        page: Page,
        query: str,
        *,
        existing_keys: set[str] | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> tuple[list[str], set[str]]:
        search_url = f"https://www.google.com/maps/search/{quote_plus(query)}"
        page.goto(search_url, wait_until="domcontentloaded", timeout=90_000)
        page.wait_for_timeout(3_000)

        urls: list[str] = []
        seen: set[str] = set()
        existing_keys = existing_keys or set()
        seen_existing_keys: set[str] = set()
        feed = page.locator('div[role="feed"]').first
        stall_rounds = 0
        scroll_round = 0

        if "/maps/place/" in page.url:
            cleaned = self._clean_maps_url(page.url)
            if cleaned:
                if cleaned in existing_keys:
                    return [], {cleaned}
                return [cleaned], set()

        while self._has_result_capacity(len(urls)) and stall_rounds < self._stall_limit_for_count(len(urls)):
            scroll_round += 1
            current_links = []
            try:
                current_links = page.locator(DETAIL_LINK_SELECTOR).evaluate_all(
                    "elements => elements.map((element) => element.href)"
                )
            except Exception:
                current_links = []

            before = len(urls)
            for href in current_links:
                cleaned = self._clean_maps_url(href)
                if not cleaned or cleaned in seen:
                    continue
                seen.add(cleaned)
                if cleaned in existing_keys:
                    seen_existing_keys.add(cleaned)
                    continue
                urls.append(cleaned)
                if not self._has_result_capacity(len(urls)):
                    break

            new_urls = len(urls) - before
            effective_stall_limit = self._stall_limit_for_count(len(urls))
            if not self._has_result_capacity(len(urls)):
                if progress_callback is not None:
                    progress_callback(
                        "collect_progress",
                        {
                            "query": query,
                            "round": scroll_round,
                            "new_urls": new_urls,
                            "url_count": len(urls),
                            "stall_rounds": stall_rounds,
                            "stall_limit": effective_stall_limit,
                            "seen_existing_count": len(seen_existing_keys),
                        },
                    )
                break

            if feed.count():
                try:
                    feed.evaluate("(element) => element.scrollBy(0, element.scrollHeight)")
                except Exception:
                    page.mouse.wheel(0, 5_000)
            else:
                page.mouse.wheel(0, 5_000)

            page.wait_for_timeout(self.wait_ms)
            stall_rounds = stall_rounds + 1 if len(urls) == before else 0
            effective_stall_limit = self._stall_limit_for_count(len(urls))
            if progress_callback is not None:
                progress_callback(
                    "collect_progress",
                    {
                        "query": query,
                        "round": scroll_round,
                        "new_urls": new_urls,
                        "url_count": len(urls),
                        "stall_rounds": stall_rounds,
                        "stall_limit": effective_stall_limit,
                        "seen_existing_count": len(seen_existing_keys),
                    },
                )

        if self.max_results <= 0:
            return urls, seen_existing_keys
        return urls[: self.max_results], seen_existing_keys

    def _extract_lead(self, page: Page, detail_url: str, search: SearchQuery) -> Lead | None:
        page.goto(detail_url, wait_until="domcontentloaded", timeout=90_000)
        page.wait_for_timeout(2_500)

        business_name = self._first_text(page, ["h1"])
        if not business_name:
            return None

        website_url = self._first_href(
            page,
            [
                'a[data-item-id="authority"]',
                'a[aria-label^="Website:"]',
                'a[href^="http"]:not([href*="google.com"])',
            ],
        )
        phone = self._extract_phone(page)
        address = self._first_text(page, ['button[data-item-id="address"]', 'button[aria-label^="Address:"]'])
        category = self._first_text(
            page,
            [
                'button[jsaction*="pane.rating.category"]',
                'button[aria-label*="category"]',
            ],
        )
        rating, review_count = self._extract_rating_data(page)
        city, state = self._city_state_from_address(address, search.city, search.state)
        status = normalize_business_status(self._detect_status(page))

        return Lead(
            source="google_maps",
            source_query=search.query,
            trade=search.trade or category or search.query,
            business_name=business_name,
            phone=phone,
            category=category,
            rating=rating,
            review_count=review_count,
            address=address,
            city=city,
            state=state,
            google_maps_url=self._clean_maps_url(page.url) or detail_url,
            google_maps_website_url=website_url,
            website_url=website_url,
            has_website=bool(website_url),
            website_verification_status="found_on_google_maps" if website_url else "not_checked",
            business_status=status,
            notes="Scraped from Google Maps detail page.",
        )

    def _first_text(self, page: Page, selectors: list[str]) -> str:
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if locator.count() == 0:
                    continue
                value = locator.inner_text(timeout=2_000).strip()
                if value:
                    cleaned = re.sub(r"\s+", " ", value)
                    cleaned = re.sub(r"^[^\w(]+", "", cleaned)
                    return cleaned.strip()
            except Exception:
                continue
        return ""

    def _first_href(self, page: Page, selectors: list[str]) -> str:
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if locator.count() == 0:
                    continue
                href = (locator.get_attribute("href", timeout=2_000) or "").strip()
                if href and "google.com" not in href:
                    return href
            except Exception:
                continue
        return ""

    def _extract_phone(self, page: Page) -> str:
        selectors = [
            'button[data-item-id^="phone:tel:"]',
            'button[aria-label^="Phone:"]',
        ]
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if locator.count() == 0:
                    continue
                label = locator.get_attribute("aria-label", timeout=2_000) or ""
                text = locator.inner_text(timeout=2_000) or ""
                combined = " ".join(part for part in [label, text] if part)
                match = re.search(r"(\+?1[\s.-]*)?(?:\(?\d{3}\)?[\s.-]*)\d{3}[\s.-]*\d{4}", combined)
                if match:
                    return match.group(0).strip()
            except Exception:
                continue
        return ""

    def _extract_rating_data(self, page: Page) -> tuple[str, str]:
        selectors = [
            'button[jsaction*="pane.rating.moreReviews"]',
            'span[aria-label*="stars"]',
        ]
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if locator.count() == 0:
                    continue
                combined = " ".join(
                    part
                    for part in [
                        locator.get_attribute("aria-label", timeout=2_000) or "",
                        locator.inner_text(timeout=2_000) or "",
                    ]
                    if part
                )
                rating_match = re.search(r"([0-5]\.?[0-9]?)", combined)
                reviews_match = re.search(r"([\d,]+)\s+reviews?", combined, re.IGNORECASE)
                rating = rating_match.group(1) if rating_match else ""
                review_count = reviews_match.group(1).replace(",", "") if reviews_match else ""
                if rating or review_count:
                    return rating, review_count
            except Exception:
                continue
        return "", ""

    def _detect_status(self, page: Page) -> str:
        try:
            body_text = page.locator("body").inner_text(timeout=2_000).lower()
        except Exception:
            return "unknown"
        if "permanently closed" in body_text:
            return "permanently_closed"
        if "temporarily closed" in body_text:
            return "temporarily_closed"
        if body_text:
            return "open"
        return "unknown"

    def _city_state_from_address(self, address: str, fallback_city: str, fallback_state: str) -> tuple[str, str]:
        match = re.search(r",\s*([^,]+),\s*([A-Z]{2})\b", address or "")
        if match:
            return match.group(1).strip(), match.group(2).strip()
        return fallback_city.strip(), fallback_state.strip()

    def _clean_maps_url(self, href: str) -> str:
        href = (href or "").strip()
        if not href:
            return ""
        if "/maps/place/" not in href:
            return ""
        return href.split("&", 1)[0]
