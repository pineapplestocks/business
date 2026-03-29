#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import os
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from threading import Lock
from time import monotonic, strftime

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from automation.google_maps import GoogleMapsScraper, SearchQuery
from automation.models import Lead, dedupe_leads, read_leads, write_leads
from automation.website_verifier import WebsiteVerifier

PRINT_LOCK = Lock()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Scrape Google Maps search results, flag leads with and without websites, "
            "and save normalized lead data to CSV."
        )
    )
    parser.add_argument(
        "--query",
        action="append",
        default=[],
        help='Search query, for example: --query "plumber in Salt Lake City UT"',
    )
    parser.add_argument(
        "--query-file",
        type=Path,
        help="CSV file with headers: query,trade,city,state",
    )
    parser.add_argument("--trade", default="", help="Default trade for direct --query values.")
    parser.add_argument("--city", default="", help="Default city for direct --query values.")
    parser.add_argument("--state", default="", help="Default state for direct --query values.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/leads.csv"),
        help="Output CSV path for normalized leads.",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=20,
        help="Maximum results to collect per query. Use 0 for no fixed cap.",
    )
    parser.add_argument(
        "--scroll-rounds",
        type=int,
        default=12,
        help="How many consecutive no-growth scroll passes to allow before stopping a query.",
    )
    parser.add_argument(
        "--wait-ms",
        type=int,
        default=1500,
        help="Milliseconds to wait between Google Maps scroll passes.",
    )
    parser.add_argument(
        "--exhaustive",
        action="store_true",
        help="Collect as many results as Google Maps will expose by removing the result cap and increasing scroll depth.",
    )
    parser.add_argument(
        "--headful",
        action="store_true",
        help="Show the browser while scraping instead of using headless mode.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Overwrite the output file instead of merging with existing leads.",
    )
    parser.add_argument(
        "--skip-web-verification",
        action="store_true",
        help="Skip the second website check from search results. Not recommended for production qualification.",
    )
    parser.add_argument(
        "--search-results",
        type=int,
        default=5,
        help="Maximum non-directory search results to inspect per verification query.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel Google Maps browser workers to use while scraping queries.",
    )
    parser.add_argument(
        "--auto-workers",
        action="store_true",
        help="Pick a sane worker count automatically from query count and available CPU threads.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show extra per-lead progress details during website verification.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce terminal progress logging.",
    )
    parser.add_argument(
        "--save-every",
        type=int,
        default=100,
        help="Checkpoint the output CSV every N leads of scrape or verification progress. Use 0 to disable.",
    )
    return parser.parse_args()


def load_queries(args: argparse.Namespace) -> list[SearchQuery]:
    searches: list[SearchQuery] = [
        SearchQuery(query=item, trade=args.trade, city=args.city, state=args.state) for item in args.query
    ]

    if args.query_file:
        with args.query_file.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                query = (row.get("query") or "").strip()
                if not query:
                    continue
                searches.append(
                    SearchQuery(
                        query=query,
                        trade=(row.get("trade") or "").strip(),
                        city=(row.get("city") or "").strip(),
                        state=(row.get("state") or "").strip(),
                    )
                )

    if not searches:
        raise SystemExit("Provide at least one --query or a --query-file.")

    return searches


def log_progress(message: str, *, enabled: bool = True) -> None:
    if not enabled:
        return
    timestamp = strftime("%H:%M:%S")
    with PRINT_LOCK:
        print(f"[{timestamp}] {message}", flush=True)


def format_query_label(index: int, total: int, *, worker_id: int | None = None) -> str:
    label = f"[query {index}/{total}]"
    if worker_id is None:
        return label
    return f"[worker {worker_id}] {label}"


def needs_verification(lead: Lead) -> bool:
    if lead.google_maps_website_url:
        return False
    return lead.website_verification_status in {"not_checked", "search_error"}


def format_lead_brief(lead: Lead) -> str:
    location = ", ".join(part for part in [lead.city, lead.state] if part)
    trade = lead.trade or lead.category or "local_service"
    phone = f" | {lead.phone}" if lead.phone else ""
    location_text = f" | {location}" if location else ""
    return f"{lead.business_name} | {trade}{location_text}{phone}"


def resolve_worker_count(args: argparse.Namespace, query_count: int) -> tuple[int, str | None]:
    if query_count < 1:
        return 0, None
    if args.headful:
        if args.auto_workers:
            return 1, "Auto-workers selected 1 worker because --headful only supports a single visible browser."
        return min(args.workers, query_count), None
    if not args.auto_workers:
        return min(args.workers, query_count), None

    cpu_count = os.cpu_count() or 4
    cpu_target = max(1, cpu_count // 2)
    worker_count = min(query_count, max(1, min(8, cpu_target)))
    return (
        worker_count,
        (
            f"Auto-workers selected {worker_count} worker(s) for {query_count} querie(s) "
            f"using {cpu_count} detected CPU thread(s)."
        ),
    )


def print_pitchable_preview(leads: list[Lead], *, heading: str, limit: int = 10) -> None:
    if not leads:
        return
    print(heading)
    for lead in leads[:limit]:
        print(f"- {format_lead_brief(lead)}")
    remaining = len(leads) - limit
    if remaining > 0:
        print(f"- ... and {remaining} more")


def print_pitchable_groups(
    leads: list[Lead],
    *,
    heading: str,
    max_groups: int = 8,
    leads_per_group: int = 5,
) -> None:
    if not leads:
        return

    grouped: dict[tuple[str, str, str], list[Lead]] = {}
    for lead in sorted(leads, key=lambda item: (item.city, item.state, item.trade, item.business_name)):
        key = (lead.city, lead.state, lead.trade)
        grouped.setdefault(key, []).append(lead)

    ranked_groups = sorted(
        grouped.items(),
        key=lambda item: (-len(item[1]), item[0][0], item[0][1], item[0][2]),
    )

    print(heading)
    for (city, state, trade), group_leads in ranked_groups[:max_groups]:
        location = ", ".join(part for part in [city, state] if part) or "Unknown location"
        print(f"{location} | {trade} ({len(group_leads)})")
        for lead in group_leads[:leads_per_group]:
            phone = f" | {lead.phone}" if lead.phone else ""
            print(f"  - {lead.business_name}{phone}")
        remaining = len(group_leads) - leads_per_group
        if remaining > 0:
            print(f"  - ... and {remaining} more")

    extra_groups = len(ranked_groups) - max_groups
    if extra_groups > 0:
        print(f"... and {extra_groups} more city/trade group(s)")


@dataclass(slots=True)
class CheckpointState:
    output: Path
    existing: list[Lead]
    save_every: int
    quiet: bool
    scraped: list[Lead] = field(default_factory=list)
    seen_existing_keys: set[str] = field(default_factory=set)
    scrape_processed: int = 0
    verify_processed: int = 0
    _last_scrape_save_at: int = 0
    _last_verify_save_at: int = 0
    _lock: Lock = field(default_factory=Lock)
    _existing_by_key: dict[str, Lead] = field(init=False, default_factory=dict)

    def __post_init__(self) -> None:
        self._existing_by_key = {lead.dedupe_key(): lead for lead in self.existing}

    def snapshot(self) -> list[Lead]:
        return dedupe_leads([*self.existing, *self.scraped])

    def record_scrape_result(self, leads: list[Lead], seen_existing_keys: set[str], *, seen_on: str) -> None:
        if not leads and not seen_existing_keys:
            return

        with self._lock:
            if leads:
                for lead in leads:
                    lead.ensure_seen_defaults(seen_on)
                self.scraped.extend(leads)
                self.scrape_processed += len(leads)

            newly_seen_existing = seen_existing_keys - self.seen_existing_keys
            for key in newly_seen_existing:
                existing_lead = self._existing_by_key.get(key)
                if existing_lead is None:
                    continue
                existing_lead.mark_seen(seen_on)
            self.seen_existing_keys.update(seen_existing_keys)

            self._maybe_checkpoint_locked(
                processed=self.scrape_processed,
                stage="scrape",
                save_attr="_last_scrape_save_at",
                reason=f"checkpoint after {self.scrape_processed} scraped lead(s)",
            )

    def record_verification_progress(self, *, stage_label: str) -> None:
        with self._lock:
            self.verify_processed += 1
            self._maybe_checkpoint_locked(
                processed=self.verify_processed,
                stage="verify",
                save_attr="_last_verify_save_at",
                reason=f"checkpoint after {self.verify_processed} verified lead(s) during {stage_label}",
            )

    def save(self, *, reason: str) -> int:
        with self._lock:
            snapshot = self.snapshot()
            write_leads(self.output, snapshot)
            log_progress(
                f"Checkpoint saved to {self.output} ({len(snapshot)} total leads, {reason})",
                enabled=not self.quiet,
            )
            return len(snapshot)

    def _maybe_checkpoint_locked(self, *, processed: int, stage: str, save_attr: str, reason: str) -> None:
        if self.save_every <= 0:
            return
        last_saved_at = getattr(self, save_attr)
        if processed - last_saved_at < self.save_every:
            return

        snapshot = self.snapshot()
        write_leads(self.output, snapshot)
        setattr(self, save_attr, processed)
        log_progress(
            f"Checkpoint saved to {self.output} ({len(snapshot)} total leads, {reason})",
            enabled=not self.quiet,
        )


def scrape_batch(
    batch: list[tuple[int, SearchQuery]],
    *,
    worker_id: int | None,
    total_queries: int,
    headless: bool,
    max_results: int,
    scroll_rounds: int,
    wait_ms: int,
    quiet: bool,
    existing_keys: set[str],
    checkpoint_state: CheckpointState | None,
    seen_on: str,
) -> list[tuple[int, list[Lead], set[str]]]:
    results: list[tuple[int, list[Lead], set[str]]] = []
    with GoogleMapsScraper(
        headless=headless,
        max_results=max_results,
        scroll_rounds=scroll_rounds,
        wait_ms=wait_ms,
    ) as scraper:
        for index, search in batch:
            label = format_query_label(index, total_queries, worker_id=worker_id)
            log_progress(f"{label} Starting {search.query}", enabled=not quiet)
            started = monotonic()

            def progress_callback(event: str, payload: dict[str, object]) -> None:
                if quiet:
                    return

                elapsed = monotonic() - started
                if event == "collect_progress":
                    round_number = int(payload.get("round", 0))
                    url_count = int(payload.get("url_count", 0))
                    new_urls = int(payload.get("new_urls", 0))
                    stall_count = int(payload.get("stall_rounds", 0))
                    stall_limit = int(payload.get("stall_limit", scroll_rounds))
                    seen_before_count = int(payload.get("seen_existing_count", 0))
                    if new_urls == 0 and stall_count == 0 and round_number % 5 != 0:
                        return
                    log_progress(
                        (
                            f"{label} Collecting cards -> {url_count} found, "
                            f"{new_urls} new this round, {seen_before_count} seen before, "
                            f"stall {stall_count}/{stall_limit}, round {round_number}, {elapsed:.1f}s"
                        )
                    )
                elif event == "collect_complete":
                    url_count = int(payload.get("url_count", 0))
                    seen_before_count = int(payload.get("seen_existing_count", 0))
                    log_progress(
                        f"{label} Collection done -> {url_count} new cards, {seen_before_count} seen before, {elapsed:.1f}s"
                    )
                elif event == "extract_progress":
                    done = int(payload.get("done", 0))
                    total = int(payload.get("total", 0))
                    if total <= 5 or done in {1, total} or done % 10 == 0:
                        log_progress(f"{label} Extracting details {done}/{total} ({elapsed:.1f}s)")

            try:
                query_result = scraper.scrape_query(
                    search,
                    existing_keys=existing_keys,
                    progress_callback=progress_callback,
                )
            except Exception as exc:
                elapsed = monotonic() - started
                log_progress(
                    f"{label} Failed {search.query} after {elapsed:.1f}s: {exc}",
                    enabled=True,
                )
                raise

            elapsed = monotonic() - started
            leads = query_result.leads
            google_maps_websites = sum(1 for lead in leads if lead.google_maps_website_url)
            missing_websites = len(leads) - google_maps_websites
            seen_before = len(query_result.seen_existing_keys)
            log_progress(
                (
                    f"{label} Finished {search.query} -> {len(leads)} leads, "
                    f"{google_maps_websites} with sites on Maps, "
                    f"{missing_websites} without, {seen_before} seen before, {elapsed:.1f}s"
                ),
                enabled=not quiet,
            )
            if checkpoint_state is not None:
                checkpoint_state.record_scrape_result(leads, query_result.seen_existing_keys, seen_on=seen_on)
            results.append((index, leads, query_result.seen_existing_keys))
    return results


def scrape_queries(
    searches: list[SearchQuery],
    args: argparse.Namespace,
    *,
    existing_keys: set[str],
    checkpoint_state: CheckpointState | None,
    seen_on: str,
) -> tuple[list[Lead], set[str]]:
    worker_count, worker_message = resolve_worker_count(args, len(searches))
    result_limit_label = "all available" if args.max_results <= 0 else str(args.max_results)
    if worker_message:
        log_progress(worker_message, enabled=not args.quiet)
    log_progress(
        (
            f"Loaded {len(searches)} queries. "
            f"Scraping with {worker_count} worker(s), max {result_limit_label} result(s) per query, "
            f"scroll-rounds {args.scroll_rounds}, wait {args.wait_ms}ms."
        ),
        enabled=not args.quiet,
    )

    indexed_searches = list(enumerate(searches, start=1))
    if worker_count == 1:
        ordered_results = scrape_batch(
            indexed_searches,
            worker_id=None,
            total_queries=len(searches),
            headless=not args.headful,
            max_results=args.max_results,
            scroll_rounds=args.scroll_rounds,
            wait_ms=args.wait_ms,
            quiet=args.quiet,
            existing_keys=existing_keys,
            checkpoint_state=checkpoint_state,
            seen_on=seen_on,
        )
    else:
        batches: list[list[tuple[int, SearchQuery]]] = [[] for _ in range(worker_count)]
        for offset, item in enumerate(indexed_searches):
            batches[offset % worker_count].append(item)

        ordered_results = []
        with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="maps-scraper") as executor:
            futures = [
                executor.submit(
                    scrape_batch,
                    batch,
                    worker_id=worker_id,
                    total_queries=len(searches),
                    headless=not args.headful,
                    max_results=args.max_results,
                    scroll_rounds=args.scroll_rounds,
                    wait_ms=args.wait_ms,
                    quiet=args.quiet,
                    existing_keys=existing_keys,
                    checkpoint_state=checkpoint_state,
                    seen_on=seen_on,
                )
                for worker_id, batch in enumerate(batches, start=1)
                if batch
            ]
            for future in as_completed(futures):
                ordered_results.extend(future.result())

        ordered_results.sort(key=lambda item: item[0])

    scraped: list[Lead] = []
    seen_existing_keys: set[str] = set()
    for _, leads, query_seen_existing_keys in ordered_results:
        scraped.extend(leads)
        seen_existing_keys.update(query_seen_existing_keys)

    deduped = dedupe_leads(scraped)
    log_progress(
        (
            f"Scraping complete: {len(scraped)} raw new lead rows, {len(deduped)} after dedupe, "
            f"{len(seen_existing_keys)} existing lead(s) skipped."
        ),
        enabled=not args.quiet,
    )
    return deduped, seen_existing_keys


def should_log_verification(index: int, total: int, *, verbose: bool) -> bool:
    if verbose or total <= 25:
        return True
    return index in {1, total} or index % 10 == 0


def verify_with_progress(
    leads: list[Lead],
    args: argparse.Namespace,
    *,
    checkpoint_state: CheckpointState | None = None,
    stage_label: str = "verification",
) -> list[Lead]:
    total = len(leads)
    if total == 0:
        return leads

    if args.skip_web_verification:
        log_progress("Skipping website verification.", enabled=not args.quiet)
        return leads

    verifier = WebsiteVerifier(max_results_per_query=args.search_results)
    log_progress(
        f"Starting website verification for {total} lead(s).",
        enabled=not args.quiet,
    )

    verified: list[Lead] = []
    for index, lead in enumerate(leads, start=1):
        should_log = not args.quiet and should_log_verification(index, total, verbose=args.verbose)
        location = ", ".join(part for part in [lead.city, lead.state] if part)
        location_suffix = f" ({location})" if location else ""
        if should_log:
            log_progress(f"[verify {index}/{total}] {lead.business_name}{location_suffix}")

        started = monotonic()
        verified_lead = verifier.verify_lead(lead)
        verified.append(verified_lead)
        if checkpoint_state is not None:
            checkpoint_state.record_verification_progress(stage_label=stage_label)

        if should_log:
            elapsed = monotonic() - started
            log_progress(
                f"[verify {index}/{total}] -> {verified_lead.website_verification_status} in {elapsed:.1f}s"
            )
        if verified_lead.qualifies_for_pitch():
            log_progress(
                f"[verify {index}/{total}] Pitchable no-website lead found: {format_lead_brief(verified_lead)}",
                enabled=not args.quiet,
            )

    return verified


def main() -> None:
    args = parse_args()
    if args.exhaustive:
        args.max_results = 0
        args.scroll_rounds = max(args.scroll_rounds, 60)
        args.wait_ms = max(args.wait_ms, 2000)
    if args.workers < 1:
        raise SystemExit("--workers must be at least 1.")
    if args.scroll_rounds < 1:
        raise SystemExit("--scroll-rounds must be at least 1.")
    if args.wait_ms < 100:
        raise SystemExit("--wait-ms must be at least 100.")
    if args.save_every < 0:
        raise SystemExit("--save-every must be 0 or greater.")
    if args.headful and args.workers > 1 and not args.auto_workers:
        raise SystemExit("--headful only supports --workers 1 to avoid launching multiple visible browsers.")

    searches = load_queries(args)
    today = date.today().isoformat()

    existing: list[Lead] = []
    if args.output.exists() and not args.replace:
        existing = read_leads(args.output)
        for lead in existing:
            lead.ensure_seen_defaults()
        log_progress(
            f"Loaded {len(existing)} existing lead(s) from {args.output} for merge.",
            enabled=not args.quiet,
        )

    checkpoint_state = CheckpointState(
        output=args.output,
        existing=existing,
        save_every=args.save_every,
        quiet=args.quiet,
    )
    existing_keys = {lead.dedupe_key() for lead in existing}
    pending_existing = [lead for lead in existing if needs_verification(lead)]
    if pending_existing:
        log_progress(
            f"Resuming website verification for {len(pending_existing)} previously saved lead(s).",
            enabled=not args.quiet,
        )

    scraped, seen_existing_keys = scrape_queries(
        searches,
        args,
        existing_keys=existing_keys,
        checkpoint_state=checkpoint_state,
        seen_on=today,
    )

    if seen_existing_keys:
        log_progress(
            f"Marked {len(seen_existing_keys)} existing lead(s) as seen again on this run.",
            enabled=not args.quiet,
        )

    verified_existing = verify_with_progress(
        pending_existing,
        args,
        checkpoint_state=checkpoint_state,
        stage_label="existing leads",
    )
    verified_new = verify_with_progress(
        scraped,
        args,
        checkpoint_state=checkpoint_state,
        stage_label="new leads",
    )
    merged = dedupe_leads([*existing, *verified_new])
    log_progress(
        (
            f"Merged lead set contains {len(merged)} unique lead(s), including "
            f"{len(verified_new)} new lead(s) and {len(verified_existing)} resumed verification lead(s)."
        ),
        enabled=not args.quiet,
    )

    write_leads(args.output, merged)
    log_progress(f"Wrote lead CSV to {args.output}", enabled=not args.quiet)

    new_leads = len(verified_new)
    new_pitchable = [lead for lead in verified_new if lead.qualifies_for_pitch()]
    total_pitchable = [lead for lead in merged if lead.qualifies_for_pitch()]
    new_manual_review = [lead for lead in verified_new if lead.website_verification_status == "needs_manual_review"]
    new_search_error = [lead for lead in verified_new if lead.website_verification_status == "search_error"]
    new_has_website = [lead for lead in verified_new if lead.has_website]
    no_website = sum(1 for lead in merged if not lead.has_website)
    open_leads = sum(1 for lead in merged if lead.business_status == "open")
    verification_counts = Counter(lead.website_verification_status for lead in merged)
    verified_no_website = sum(1 for lead in merged if lead.is_verified_no_website())

    print(f"Wrote {len(merged)} total leads to {args.output}")
    print(f"New leads added this run: {new_leads}")
    print(f"Previously saved leads resumed for verification: {len(verified_existing)}")
    print(f"Existing leads skipped this run: {len(seen_existing_keys)}")
    print(f"Pitchable leads ready now: {len(total_pitchable)}")
    print(f"New pitchable no-website leads this run: {len(new_pitchable)}")
    print(f"New leads needing manual review: {len(new_manual_review)}")
    print(f"New leads with search errors: {len(new_search_error)}")
    print(f"New leads that already had websites: {len(new_has_website)}")
    print(f"Open leads: {open_leads}")
    print(f"Leads without websites by any check: {no_website}")
    print(f"Verified no-website leads: {verified_no_website}")
    print(f"Website verification summary: {dict(sorted(verification_counts.items()))}")
    print_pitchable_preview(new_pitchable, heading="Pitchable no-website leads found this run:")
    print_pitchable_groups(total_pitchable, heading="Pitchable no-website leads by city/trade:")


if __name__ == "__main__":
    main()
