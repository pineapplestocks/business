#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from automation.crm import (  # noqa: E402
    CALL_OUTCOME_OPTIONS,
    PITCH_STATUS_OPTIONS,
    CRM_EDITABLE_FIELDS,
    crm_stats,
    export_crm_records_to_csv,
    load_crm_store,
    sync_crm_store,
    update_crm_record,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Serve the simple local CRM in your browser. The CRM syncs from generated leads "
            "and stores notes, stages, and sales results in a JSON file."
        )
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind.")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind.")
    parser.add_argument("--input", type=Path, default=Path("data/leads.generated.csv"), help="Generated lead CSV.")
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("data/crm_records.json"),
        help="CRM JSON store path.",
    )
    parser.add_argument(
        "--include-unknown-status",
        action="store_true",
        help="Include unknown-status leads in the CRM store if they otherwise qualify.",
    )
    return parser.parse_args()


def build_payload(store: dict) -> dict:
    return {
        "records": store.get("records", []),
        "stats": crm_stats(store.get("records", [])),
        "options": {
            "pitch_statuses": PITCH_STATUS_OPTIONS,
            "call_outcomes": CALL_OUTCOME_OPTIONS,
            "editable_fields": sorted(CRM_EDITABLE_FIELDS),
        },
        "updated_at": store.get("updated_at", ""),
        "source_file": store.get("source_file", ""),
    }


def build_handler(
    *,
    static_dir: Path,
    leads_path: Path,
    store_path: Path,
    include_unknown_status: bool,
):
    class CRMHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

        def _send_bytes(self, payload: bytes, *, status: int = 200, content_type: str = "text/plain") -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _send_json(self, payload: dict, *, status: int = 200) -> None:
            self._send_bytes(
                json.dumps(payload, ensure_ascii=True).encode("utf-8"),
                status=status,
                content_type="application/json; charset=utf-8",
            )

        def _read_json(self) -> dict:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                return {}
            body = self.rfile.read(length)
            return json.loads(body.decode("utf-8"))

        def _sync_store(self) -> dict:
            if not leads_path.exists():
                empty = {"source_file": str(leads_path), "records": []}
                return empty
            return sync_crm_store(
                leads_path=leads_path,
                store_path=store_path,
                include_unknown_status=include_unknown_status,
            )

        def _load_store(self) -> dict:
            if not store_path.exists() and leads_path.exists():
                return self._sync_store()
            return load_crm_store(store_path)

        def _serve_static(self, relative_path: str) -> None:
            clean = relative_path.lstrip("/") or "index.html"
            file_path = (static_dir / clean).resolve()
            if static_dir.resolve() not in file_path.parents and file_path != static_dir.resolve():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            if not file_path.exists() or not file_path.is_file():
                self.send_error(HTTPStatus.NOT_FOUND)
                return

            content_type = "text/plain; charset=utf-8"
            if file_path.suffix == ".html":
                content_type = "text/html; charset=utf-8"
            elif file_path.suffix == ".css":
                content_type = "text/css; charset=utf-8"
            elif file_path.suffix == ".js":
                content_type = "application/javascript; charset=utf-8"

            self._send_bytes(file_path.read_bytes(), content_type=content_type)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/api/records":
                self._send_json(build_payload(self._load_store()))
                return

            if parsed.path == "/api/export.csv":
                temp_path = store_path.parent / ".crm_export_tmp.csv"
                export_crm_records_to_csv(store_path, temp_path)
                self._send_bytes(temp_path.read_bytes(), content_type="text/csv; charset=utf-8")
                temp_path.unlink(missing_ok=True)
                return

            if parsed.path in {"/", "/index.html"}:
                self._serve_static("index.html")
                return

            self._serve_static(parsed.path)

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/api/sync":
                store = self._sync_store()
                self._send_json(build_payload(store))
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def do_PUT(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if not parsed.path.startswith("/api/records/"):
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            record_id = unquote(parsed.path.rsplit("/", 1)[-1])
            try:
                record = update_crm_record(store_path, record_id, self._read_json())
            except KeyError:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            self._send_json({"record": record})

    return CRMHandler


def main() -> None:
    args = parse_args()
    static_dir = REPO_ROOT / "crm"
    static_dir.mkdir(parents=True, exist_ok=True)

    if args.input.exists():
        sync_crm_store(
            leads_path=args.input,
            store_path=args.data,
            include_unknown_status=args.include_unknown_status,
        )

    server = ThreadingHTTPServer(
        (args.host, args.port),
        build_handler(
            static_dir=static_dir,
            leads_path=args.input,
            store_path=args.data,
            include_unknown_status=args.include_unknown_status,
        ),
    )

    print(f"CRM available at http://{args.host}:{args.port}")
    print(f"Lead source: {args.input}")
    print(f"CRM store: {args.data}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nCRM server stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
