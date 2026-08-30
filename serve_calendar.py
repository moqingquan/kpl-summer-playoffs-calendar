#!/usr/bin/env python3
"""Serve the generated ICS file for iOS calendar subscription."""

from __future__ import annotations

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class CalendarHandler(SimpleHTTPRequestHandler):
    calendar_name = "kpl-summer-playoffs.ics"
    root = Path.cwd()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(self.root), **kwargs)

    def do_GET(self) -> None:  # noqa: N802 - required by http.server
        if self.path.split("?", 1)[0].rstrip("/") in {"", "/"}:
            self.send_response(302)
            self.send_header("Location", f"/{self.calendar_name}")
            self.end_headers()
            return
        if self.path.split("?", 1)[0] == f"/{self.calendar_name}":
            super().do_GET()
            return
        self.send_error(404, "Only the KPL calendar feed is available")

    def end_headers(self) -> None:
        if self.path.split("?", 1)[0] == f"/{self.calendar_name}":
            self.send_header("Content-Type", "text/calendar; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
        super().end_headers()


def main() -> None:
    parser = argparse.ArgumentParser(description="提供KPL ICS订阅地址")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    calendar = root / CalendarHandler.calendar_name
    if not calendar.exists():
        raise SystemExit(f"找不到 {calendar}，请先运行 update_calendar.py")
    CalendarHandler.root = root
    server = ThreadingHTTPServer((args.host, args.port), CalendarHandler)
    print(f"订阅地址: http://<本机IP>:{args.port}/{CalendarHandler.calendar_name}")
    print("按 Ctrl+C 停止服务")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

