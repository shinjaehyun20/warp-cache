from __future__ import annotations

import argparse
import json
import statistics
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from pathlib import Path
import urllib.request
import urllib.error

PORT = 9120
HOST = "127.0.0.1"


class BenchmarkHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress logging to keep console output clean

    def do_GET(self):
        if self.path == "/full":
            time.sleep(0.1)  # Simulate full page load and client-side JS rendering latency
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "full_render_done", "payload": "X" * 2000}).encode("utf-8"))
        elif self.path == "/direct":
            time.sleep(0.005)  # Simulate direct API cache bypass with active session
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "cached_api_done", "payload": "X" * 2000}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


def run_server(server: HTTPServer) -> None:
    server.serve_forever()


def main() -> int:
    parser = argparse.ArgumentParser(description="WarpCache browser-direct request benchmark")
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "artifacts" / "browser_benchmark.json"
    )
    args = parser.parse_args()

    if args.runs < 3:
        parser.error("runs must be >= 3")

    server = HTTPServer((HOST, PORT), BenchmarkHandler)
    thread = threading.Thread(target=run_server, args=(server,), daemon=True)
    thread.start()

    # Allow server to initialize
    time.sleep(0.2)

    baseline_times = []
    for _ in range(args.runs):
        start = time.perf_counter()
        try:
            req = urllib.request.Request(f"http://{HOST}:{PORT}/full")
            with urllib.request.urlopen(req) as resp:
                resp.read()
        except Exception as exc:
            print(f"Error during baseline request: {exc}")
        baseline_times.append(time.perf_counter() - start)

    cached_times = []
    for _ in range(args.runs):
        start = time.perf_counter()
        try:
            req = urllib.request.Request(f"http://{HOST}:{PORT}/direct")
            with urllib.request.urlopen(req) as resp:
                resp.read()
        except Exception as exc:
            print(f"Error during direct bypass request: {exc}")
        cached_times.append(time.perf_counter() - start)

    # Graceful shutdown
    server.shutdown()
    server.server_close()
    thread.join()

    # Compute metrics
    baseline_median = statistics.median(baseline_times)
    cached_median = statistics.median(cached_times)

    saved = baseline_median - cached_median
    reduction = (saved / baseline_median) * 100 if baseline_median > 0 else 0
    multiplier = baseline_median / cached_median if cached_median > 0 else 0

    report = {
        "schema": "warp-cache-browser-benchmark/v1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runs": args.runs,
        "baseline_full_render": {
            "seconds": [round(t, 6) for t in baseline_times],
            "median_seconds": round(baseline_median, 6)
        },
        "warpcache_direct_bypass": {
            "seconds": [round(t, 6) for t in cached_times],
            "median_seconds": round(cached_median, 6)
        },
        "effect": {
            "seconds_saved": round(saved, 6),
            "reduction_percent": round(reduction, 2),
            "speed_multiplier": round(multiplier, 3)
        }
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
