#!/usr/bin/env python3
"""Minimal local HTTP bridge for the AIBrain repo.

Pure Python 3 standard library only. Binds exclusively to 127.0.0.1.

Routes:
  GET  /                              -> web/index.html (or a simple hint page)
  GET  /api/list                      -> JSON list of relative .md paths
                                         under memory/ and knowledge/
  GET  /api/read?path=<rel>           -> JSON {path, content}
  POST /api/write  body {path,content} -> writes file, returns {ok:true}
  POST /api/sync                      -> runs `python tools/sync.py`,
                                         returns {ok, output}
  POST /api/detect                    -> runs `python tools/detect.py`,
                                         returns {ok, output}
  POST /api/ingest body {dry_run:bool}-> runs `python tools/ingest.py`,
                                         appends --dry-run when dry_run is
                                         true; returns {ok, output}

Security:
  - Every user-supplied path is normalized and resolved (realpath) and must
    stay inside REPO_ROOT; anything that escapes (e.g. "..", absolute paths
    pointing outside) is rejected with 403.
  - Writes are restricted to .md files whose relative path starts with
    memory/ or knowledge/.
"""

import sys
import os
import json
import subprocess
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PORT = 8420
HOST = "127.0.0.1"
WRITE_PREFIXES = ("memory", "knowledge")
ALLOWED_EXT = ".md"


def safe_resolve(rel_path):
    """Resolve a user-supplied relative path against REPO_ROOT.

    Returns (abs_path, rel_from_root) using real paths, or (None, None) if
    the path is absolute, empty, or escapes REPO_ROOT.
    """
    if not rel_path or not isinstance(rel_path, str):
        return None, None
    if os.path.isabs(rel_path):
        return None, None

    abs_root = os.path.realpath(REPO_ROOT)
    candidate = os.path.realpath(os.path.join(abs_root, rel_path))

    if candidate == abs_root or candidate.startswith(abs_root + os.sep):
        rel = os.path.relpath(candidate, abs_root)
        rel = rel.replace(os.sep, "/")
        return candidate, rel
    return None, None


def iter_md_files():
    """Yield relative (forward-slash) paths of all .md files under the
    allowed prefixes."""
    results = []
    for prefix in WRITE_PREFIXES:
        base = os.path.join(REPO_ROOT, prefix)
        if not os.path.isdir(base):
            continue
        for root, _dirs, files in os.walk(base):
            for name in files:
                if name.lower().endswith(ALLOWED_EXT):
                    rel = os.path.relpath(os.path.join(root, name), REPO_ROOT)
                    results.append(rel.replace(os.sep, "/"))
    results.sort()
    return results


class Handler(BaseHTTPRequestHandler):
    server_version = "AIBrainServe/1.0"

    # ---- low level helpers ------------------------------------------------
    def _send_json(self, obj, status=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_text(self, text, status=200,
                   content_type="text/html; charset=utf-8"):
        data = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_body(self):
        try:
            length = int(self.headers.get("Content-Length", "0") or "0")
        except ValueError:
            length = 0
        if length <= 0:
            return b""
        return self.rfile.read(length)

    # ---- routing ----------------------------------------------------------
    def do_GET(self):
        parsed = urlparse(self.path)
        route = parsed.path
        if route == "/":
            self._serve_index()
        elif route == "/api/list":
            self._api_list()
        elif route == "/api/read":
            self._api_read(parse_qs(parsed.query))
        else:
            self._send_text("<h1>404 Not Found</h1>", status=404)

    def do_POST(self):
        parsed = urlparse(self.path)
        route = parsed.path
        if route == "/api/write":
            self._api_write()
        elif route == "/api/sync":
            self._api_sync()
        elif route == "/api/detect":
            self._api_detect()
        elif route == "/api/ingest":
            self._api_ingest()
        else:
            self._send_text("<h1>404 Not Found</h1>", status=404)

    # ---- handlers ---------------------------------------------------------
    def _serve_index(self):
        index_path = os.path.join(REPO_ROOT, "web", "index.html")
        if os.path.isfile(index_path):
            try:
                with open(index_path, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            except OSError:
                pass
        self._send_text(
            "<!doctype html><html lang='zh'><head><meta charset='utf-8'>"
            "<title>AIBrain serve</title></head><body>"
            "<h1>AIBrain 本地服务</h1>"
            "<p>未找到 web/index.html。可用接口：</p>"
            "<ul><li>GET /api/list</li>"
            "<li>GET /api/read?path=&lt;相对路径&gt;</li>"
            "<li>POST /api/write</li>"
            "<li>POST /api/sync</li></ul>"
            "</body></html>"
        )

    def _api_list(self):
        self._send_json({"files": iter_md_files()})

    def _api_read(self, qs):
        rel = qs.get("path", [None])[0]
        abs_path, _ = safe_resolve(rel)
        if abs_path is None:
            self._send_json({"error": "forbidden path"}, status=403)
            return
        if not os.path.isfile(abs_path):
            self._send_json({"error": "not found"}, status=404)
            return
        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError as exc:
            self._send_json({"error": str(exc)}, status=500)
            return
        self._send_json({"path": rel, "content": content})

    def _api_write(self):
        body = self._read_body()
        try:
            payload = json.loads(body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self._send_json({"error": "invalid json"}, status=400)
            return
        if not isinstance(payload, dict):
            self._send_json({"error": "invalid json"}, status=400)
            return

        rel = payload.get("path")
        content = payload.get("content", "")
        if not rel or not isinstance(rel, str):
            self._send_json({"error": "missing path"}, status=400)
            return

        abs_path, rel_clean = safe_resolve(rel)
        if abs_path is None:
            self._send_json({"error": "forbidden path"}, status=403)
            return

        # Restrictions: only .md, only memory/ or knowledge/ prefixes.
        if not rel_clean.lower().endswith(ALLOWED_EXT):
            self._send_json({"error": "only .md allowed"}, status=403)
            return
        if not any(rel_clean == p or rel_clean.startswith(p + "/")
                   for p in WRITE_PREFIXES):
            self._send_json(
                {"error": "write restricted to memory/ and knowledge/"},
                status=403,
            )
            return

        try:
            parent = os.path.dirname(abs_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content if isinstance(content, str) else "")
        except OSError as exc:
            self._send_json({"error": str(exc)}, status=500)
            return
        self._send_json({"ok": True})

    def _api_sync(self):
        sync_script = os.path.join(REPO_ROOT, "tools", "sync.py")
        if not os.path.isfile(sync_script):
            self._send_json(
                {"ok": False, "output": "tools/sync.py not found"},
                status=404,
            )
            return
        try:
            proc = subprocess.run(
                [sys.executable, sync_script],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=120,
            )
            output = (proc.stdout or "") + (proc.stderr or "")
            self._send_json({
                "ok": proc.returncode == 0,
                "output": output,
                "returncode": proc.returncode,
            })
        except Exception as exc:  # pragma: no cover - defensive
            self._send_json({"ok": False, "output": str(exc)}, status=500)

    def _api_detect(self):
        script = os.path.join(REPO_ROOT, "tools", "detect.py")
        if not os.path.isfile(script):
            self._send_json(
                {"ok": False, "output": "tools/detect.py not found"},
                status=404,
            )
            return
        try:
            proc = subprocess.run(
                [sys.executable, script],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=180,
            )
            output = (proc.stdout or "") + (proc.stderr or "")
            self._send_json({
                "ok": proc.returncode == 0,
                "output": output,
                "returncode": proc.returncode,
            })
        except Exception as exc:  # pragma: no cover - defensive
            self._send_json({"ok": False, "output": str(exc)}, status=500)

    def _api_ingest(self):
        dry_run = False
        body = self._read_body()
        if body:
            try:
                payload = json.loads(body.decode("utf-8"))
                if isinstance(payload, dict):
                    dry_run = bool(payload.get("dry_run", False))
            except (ValueError, UnicodeDecodeError):
                pass
        script = os.path.join(REPO_ROOT, "tools", "ingest.py")
        if not os.path.isfile(script):
            self._send_json(
                {"ok": False, "output": "tools/ingest.py not found"},
                status=404,
            )
            return
        cmd = [sys.executable, script]
        if dry_run:
            cmd.append("--dry-run")
        try:
            proc = subprocess.run(
                cmd,
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=180,
            )
            output = (proc.stdout or "") + (proc.stderr or "")
            self._send_json({
                "ok": proc.returncode == 0,
                "output": output,
                "returncode": proc.returncode,
            })
        except Exception as exc:  # pragma: no cover - defensive
            self._send_json({"ok": False, "output": str(exc)}, status=500)

    def log_message(self, fmt, *args):
        sys.stderr.write("[serve] " + (fmt % args) + "\n")


def main():
    port = DEFAULT_PORT
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass

    httpd = ThreadingHTTPServer((HOST, port), Handler)
    url = f"http://{HOST}:{port}/"
    print(f"AIBrain serve running at {url}")
    print(f"  repo root : {REPO_ROOT}")
    print("  Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
