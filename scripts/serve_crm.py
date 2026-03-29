#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
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
)
from automation.crm_db import (  # noqa: E402
    export_crm_database_to_csv,
    import_json_store_to_db,
    load_crm_store_from_db,
    sync_crm_database,
    update_crm_record_in_db,
    write_public_snapshot,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Serve the CRM web app with a central SQLite-backed API. This is the shared store "
            "you want to use instead of browser-only storage."
        )
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind.")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind.")
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
        help="Public snapshot JSON path used by the static CRM view.",
    )
    parser.add_argument(
        "--include-unknown-status",
        action="store_true",
        help="Include unknown-status leads in the CRM store if they otherwise qualify.",
    )
    parser.add_argument(
        "--cors-origin",
        default="https://pineapplestocks.github.io",
        help=(
            "Allowed browser origin for cross-origin API requests. Use '*' to allow any origin, "
            "or provide a comma-separated list."
        ),
    )
    parser.add_argument(
        "--api-token",
        default=os.environ.get("CRM_API_TOKEN", ""),
        help="Optional bearer token required for CRM API requests. Defaults to CRM_API_TOKEN env var.",
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
    db_path: Path,
    snapshot_path: Path,
    include_unknown_status: bool,
    cors_origin: str,
    api_token: str,
):
    allowed_origins = {origin.strip() for origin in cors_origin.split(",") if origin.strip()}
    allow_all_origins = "*" in allowed_origins

    class CRMHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

        def _cors_origin_value(self) -> str:
            origin = self.headers.get("Origin", "")
            if allow_all_origins:
                return origin or "*"
            if origin and origin in allowed_origins:
                return origin
            return ""

        def _send_bytes(self, payload: bytes, *, status: int = 200, content_type: str = "text/plain") -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(payload)

        def _send_cors_headers(self) -> None:
            origin = self._cors_origin_value()
            if origin:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Token")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")

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

        def _request_token(self) -> str:
            authorization = self.headers.get("Authorization", "")
            if authorization.startswith("Bearer "):
                return authorization[7:].strip()
            return self.headers.get("X-API-Token", "").strip()

        def _require_api_auth(self) -> bool:
            if not api_token:
                return True
            if self._request_token() == api_token:
                return True
            self.send_response(HTTPStatus.UNAUTHORIZED)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("WWW-Authenticate", "Bearer")
            self._send_cors_headers()
            payload = json.dumps({"error": "unauthorized"}, ensure_ascii=True).encode("utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return False

        def _sync_store(self) -> dict:
            if leads_path.exists():
                store = sync_crm_database(
                    leads_path=leads_path,
                    db_path=db_path,
                    include_unknown_status=include_unknown_status,
                )
                write_public_snapshot(
                    leads_path=leads_path,
                    snapshot_path=snapshot_path,
                    include_unknown_status=include_unknown_status,
                )
                return store
            return load_crm_store_from_db(db_path)

        def _load_store(self) -> dict:
            return load_crm_store_from_db(db_path)

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

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(HTTPStatus.NO_CONTENT)
            self._send_cors_headers()
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)

            if parsed.path == "/api/health":
                self._send_json({"ok": True})
                return

            if parsed.path == "/api/config":
                self._send_json(
                    {
                        "auth_required": bool(api_token),
                        "storage": "sqlite",
                        "snapshot_path": str(snapshot_path),
                    }
                )
                return

            if parsed.path == "/api/records":
                if not self._require_api_auth():
                    return
                self._send_json(build_payload(self._load_store()))
                return

            if parsed.path == "/api/export.csv":
                if not self._require_api_auth():
                    return
                temp_path = snapshot_path.parent / ".crm_export_tmp.csv"
                export_crm_database_to_csv(db_path, temp_path)
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
                if not self._require_api_auth():
                    return
                store = self._sync_store()
                self._send_json(build_payload(store))
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def do_PUT(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if not parsed.path.startswith("/api/records/"):
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            if not self._require_api_auth():
                return

            record_id = unquote(parsed.path.rsplit("/", 1)[-1])
            try:
                record = update_crm_record_in_db(db_path, record_id, self._read_json())
            except KeyError:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            self._send_json({"record": record})

    return CRMHandler


def main() -> None:
    args = parse_args()
    static_dir = REPO_ROOT / "crm"
    static_dir.mkdir(parents=True, exist_ok=True)

    if not args.db.exists() and args.snapshot.exists():
        import_json_store_to_db(store_path=args.snapshot, db_path=args.db)

    if args.input.exists():
        sync_crm_database(
            leads_path=args.input,
            db_path=args.db,
            include_unknown_status=args.include_unknown_status,
        )
        write_public_snapshot(
            leads_path=args.input,
            snapshot_path=args.snapshot,
            include_unknown_status=args.include_unknown_status,
        )

    server = ThreadingHTTPServer(
        (args.host, args.port),
        build_handler(
            static_dir=static_dir,
            leads_path=args.input,
            db_path=args.db,
            snapshot_path=args.snapshot,
            include_unknown_status=args.include_unknown_status,
            cors_origin=args.cors_origin,
            api_token=args.api_token,
        ),
    )

    print(f"CRM available at http://{args.host}:{args.port}")
    print(f"Lead source: {args.input}")
    print(f"CRM database: {args.db}")
    print(f"Public snapshot: {args.snapshot}")
    print(f"CORS origin: {args.cors_origin}")
    if args.api_token:
        print("API auth: enabled")
    else:
        print("API auth: disabled")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nCRM server stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
