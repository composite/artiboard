#!/usr/bin/env python3
"""Persistent local artiboard: Python 3.10+, SQLite, no third-party packages."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"
MAX_BODY = 2 * 1024 * 1024


def default_db():
    """Parallel Git worktrees share their main checkout's data by default."""
    root = Path.cwd()
    try:
        result = subprocess.run(["git", "rev-parse", "--git-common-dir"],
                                capture_output=True, text=True, timeout=5)
        common = (root / result.stdout.strip()).resolve()
        if result.returncode == 0 and common.name == ".git":
            root = common.parent
    except (OSError, subprocess.TimeoutExpired):
        pass
    return root / ".artiboard" / "board.sqlite3"


class BoardError(Exception):
    def __init__(self, code, message, path=None):
        self.error = {"code": code, "message": message}
        if path is not None:
            self.error["path"] = path
        super().__init__(message)


def require(condition, message):
    if not condition:
        raise BoardError("invalid_request", message)


def valid_path(path, document=True):
    require(isinstance(path, str) and len(path) <= 512, "Invalid document/collection path")
    parts = path.split("/")
    require(all(re.fullmatch(r"[A-Za-z0-9_.:-]+", p) and p not in (".", "..") for p in parts),
            "Paths must use ASCII letters, numbers, underscore, dot, colon or hyphen")
    require(len(parts) % 2 == (0 if document else 1), "Wrong path depth")
    return path


class Store:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            # Deleted rows retain their version, preventing stale writers after recreation.
            db.execute("CREATE TABLE IF NOT EXISTS docs (path TEXT PRIMARY KEY, data TEXT, version INTEGER NOT NULL)")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def get(db, path):
        row = db.execute("SELECT data, version FROM docs WHERE path=?", (path,)).fetchone()
        return {"path": path, "id": path.rsplit("/", 1)[-1],
                "exists": bool(row and row[0] is not None),
                "data": json.loads(row[0]) if row and row[0] is not None else None,
                "version": row[1] if row else 0}

    @staticmethod
    def collection(db, collection):
        prefix = collection + "/"
        rows = db.execute("SELECT path, data, version FROM docs WHERE data IS NOT NULL ORDER BY path")
        return [{"path": p, "id": p[len(prefix):], "exists": True, "data": json.loads(d), "version": v}
                for p, d, v in rows if p.startswith(prefix) and "/" not in p[len(prefix):]]

    @staticmethod
    def repair_waiting(db):
        tasks = Store.collection(db, "tasks")
        done = {t["data"].get("key") for t in tasks if t["data"].get("status") == "done"}
        for task in tasks:
            data = task["data"]
            deps = data.get("deps", [])
            require(isinstance(deps, list) and all(isinstance(d, str) for d in deps),
                    "Task deps must be a list of keys")
            waiting = [key for key in deps if key not in done]
            if data.get("waitingOn") != waiting:
                data["waitingOn"] = waiting
                db.execute("UPDATE docs SET data=?, version=version+1 WHERE path=?",
                           (json.dumps(data, ensure_ascii=False), task["path"]))

    def request(self, req):
        require(isinstance(req, dict), "Request must be a JSON object")
        action = req.get("action")
        with self.connect() as db:
            if action == "get":
                return self.get(db, valid_path(req.get("path")))
            if action == "query":
                docs = self.collection(db, valid_path(req.get("collection"), False))
                where = req.get("where", [])
                require(isinstance(where, list), "where must be a list")
                for clause in where:
                    require(isinstance(clause, list) and len(clause) == 3, "Use [field, operator, value]")
                    field, op, value = clause
                    require(isinstance(field, str) and op in ("==", ">", ">=", "<", "<=", "array-contains"),
                            "Unsupported query operator or field")
                    def matches(doc):
                        actual = doc["data"].get(field)
                        if op == "==":
                            return actual == value
                        if op == "array-contains":
                            return isinstance(actual, list) and value in actual
                        if type(actual) is not type(value) or not isinstance(actual, (str, int, float)):
                            return False
                        return {">": actual > value, ">=": actual >= value,
                                "<": actual < value, "<=": actual <= value}[op]
                    docs = [d for d in docs if matches(d)]
                order = req.get("order_by")
                direction = req.get("direction", "asc")
                require(order is None or isinstance(order, str), "order_by must be a field name")
                require(direction in ("asc", "desc"), "direction must be asc or desc")
                if order:
                    # Board ordering fields (at, key, updatedAt) are strings.
                    docs.sort(key=lambda d: str(d["data"].get(order, "")), reverse=direction == "desc")
                limit = req.get("limit", 20)
                require(limit is None or type(limit) is int and 1 <= limit <= 10000, "Invalid query limit")
                return {"docs": docs if limit is None else docs[:limit]}
            if action == "batch":
                writes = req.get("writes")
                require(isinstance(writes, list) and 1 <= len(writes) <= 50, "Use 1–50 writes per batch")
                db.execute("BEGIN IMMEDIATE")
                paths = []
                for index, write in enumerate(writes):
                    try:
                        require(isinstance(write, dict), "Each write must be an object")
                        path = valid_path(write.get("path"))
                        require(path not in paths, "A batch may write each path only once")
                        paths.append(path)
                        old = self.get(db, path)
                        version = write.get("if_version")
                        require(type(version) is int and version >= 0, "Every write requires if_version")
                        if version != old["version"]:
                            raise BoardError("conflict", "Read the document again before retrying", path)
                        op = write.get("op")
                        require(op in ("set", "update", "delete"), "Use set, update or delete")
                        if op == "update" and not old["exists"]:
                            raise BoardError("not_found", "Cannot update a missing document", path)
                        data = None
                        if op != "delete":
                            patch = write.get("data")
                            require(isinstance(patch, dict), "Document data must be an object")
                            data = {**old["data"], **patch} if op == "update" else patch
                            if path.startswith("tasks/") and path.count("/") == 1:
                                require(isinstance(data.get("key"), str), "Tasks require a string key")
                                deps = data.get("deps", [])
                                require(isinstance(deps, list) and all(isinstance(d, str) for d in deps),
                                        "Task deps must be a list of keys")
                            data = json.dumps(data, ensure_ascii=False, allow_nan=False)
                            require(len(data.encode()) <= 256 * 1024, "Document exceeds 256 KiB")
                        db.execute("INSERT INTO docs VALUES (?, ?, ?) ON CONFLICT(path) DO UPDATE SET data=excluded.data, version=excluded.version",
                                   (path, data, version + 1))
                    except BoardError as error:
                        error.error["index"] = index
                        if isinstance(write, dict):
                            error.error["path"] = write.get("path")
                        raise
                self.repair_waiting(db)
                return {"docs": [self.get(db, p) for p in paths]}
        raise BoardError("invalid_request", "Use get, query or batch")


def make_server(store, port, page_path=None):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, status, body, content_type="application/json"):
            if isinstance(body, (dict, list)):
                body = json.dumps(body, ensure_ascii=False).encode()
            elif isinstance(body, str):
                body = body.encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type + "; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def valid_host(self):
            return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

        def do_GET(self):
            if not self.valid_host():
                return self.reply(403, {"code": "forbidden"})
            if self.path == "/":
                page = (Path(page_path) if page_path else ASSETS / "board.html").read_text(encoding="utf-8")
                page = page.replace("<script>", '<script src="/local.js"></script>\n<script>', 1)
                return self.reply(200, "<!doctype html><meta charset=\"utf-8\">" + page, "text/html")
            if self.path == "/local.js":
                namespace = hashlib.sha256(str(store.path).encode()).hexdigest()[:16]
                script = 'window.ARTIBOARD_STORAGE_KEY="ab-' + namespace + '-";\n'
                return self.reply(200, script + (ASSETS / "local.js").read_text(encoding="utf-8"), "text/javascript")
            return self.reply(404, {"code": "not_found"})

        def do_POST(self):
            origin = self.headers.get("Origin")
            expected = f"http://127.0.0.1:{self.server.server_port}"
            # No CORS, no arbitrary Host, and a non-simple header/content type: other
            # websites cannot read or mutate this unauthenticated loopback service.
            if (not self.valid_host() or origin not in (None, expected)
                    or self.headers.get("Sec-Fetch-Site") == "cross-site"
                    or self.headers.get("X-Artiboard") != "1"):
                return self.reply(403, {"code": "forbidden"})
            if self.path != "/api":
                return self.reply(404, {"code": "not_found"})
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                return self.reply(415, {"code": "json_required"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                require(0 < length <= MAX_BODY, "Request must be 1 byte–2 MiB")
                req = json.loads(self.rfile.read(length), parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
                self.reply(200, store.request(req))
            except BoardError as error:
                self.reply(409 if error.error["code"] == "conflict" else 400, error.error)
            except (ValueError, TypeError, UnicodeError):
                self.reply(400, {"code": "invalid_request", "message": "Invalid JSON request"})
            except sqlite3.Error:
                self.reply(503, {"code": "storage_unavailable", "message": "Check the server's database access"})

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(default_db()), help="Database path (default: main Git checkout's .artiboard/board.sqlite3, otherwise cwd)")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Create an empty board without overwriting an existing config")
    init.add_argument("--title", required=True)
    init.add_argument("--person", action="append", required=True, help="User-supplied lowercase ASCII ID; repeat for more people")
    init.add_argument("--lang", default="en")
    request = commands.add_parser("request", help="Run a get/query/batch JSON request without an HTTP server")
    request.add_argument("--file", default="-", help="JSON request file, or - for stdin")
    serve = commands.add_parser("serve", help="Serve the board on loopback only; Ctrl-C stops it")
    serve.add_argument("--port", type=int, default=8765, help="Use 0 to select an available port")
    serve.add_argument("--page", help="Optional project-customized board.html")
    args = parser.parse_args()
    try:
        if args.command == "init":
            require(all(re.fullmatch(r"[a-z][a-z0-9_-]*", p) for p in args.person), "Invalid person ID")
            require(len(set(args.person)) == len(args.person), "Person IDs must be unique")
        elif not Path(args.db).is_file():
            raise BoardError("not_found", "Database missing. Run init or check --db.")
        store = Store(args.db)
        if args.command == "init":
            result = store.request({"action": "batch", "writes": [
                {"op": "set", "path": "meta/config", "if_version": 0,
                 "data": {"title": args.title, "lang": args.lang, "people": [{"id": p} for p in args.person]}}
            ]})
        elif args.command == "request":
            raw = (sys.stdin.buffer.read(MAX_BODY + 1).decode("utf-8") if args.file == "-"
                   else Path(args.file).read_text(encoding="utf-8"))
            require(len(raw.encode()) <= MAX_BODY, "Request exceeds 2 MiB")
            result = store.request(json.loads(raw, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x))))
        else:
            require(0 <= args.port <= 65535, "Port must be 0–65535")
            if args.page:
                require(Path(args.page).is_file(), "Custom board page is missing")
            server = make_server(store, args.port, args.page)
            print(f"http://127.0.0.1:{server.server_port}/", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
            return 0
        # ASCII-safe JSON remains lossless and cannot fail after a committed
        # write merely because the terminal uses a legacy encoding.
        print(json.dumps(result))
        return 0
    except BoardError as error:
        print(json.dumps(error.error), file=sys.stderr)
    except (OSError, sqlite3.Error, ValueError) as error:
        print(json.dumps({"code": "local_error", "message": str(error)}), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
