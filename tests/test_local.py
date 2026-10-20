"""Run: python3 -m unittest discover -s tests -p 'test_*.py' -v"""
import concurrent.futures
import http.client
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills/artiboard/scripts/local_board.py"
spec = importlib.util.spec_from_file_location("local_board", SCRIPT)
board = importlib.util.module_from_spec(spec)
spec.loader.exec_module(board)


def put(path, data, version=0, op="set"):
    return {"op": op, "path": path, "data": data, "if_version": version}


class LocalBoardTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dbpath = Path(self.temp.name) / "board.sqlite3"
        self.store = board.Store(self.dbpath)

    def get(self, path):
        return self.store.request({"action": "get", "path": path})

    def batch(self, *writes):
        return self.store.request({"action": "batch", "writes": list(writes)})

    def seed(self):
        self.batch(put("meta/config", {"title": "Test", "people": [{"id": "ana"}]}),
                   put("tasks/one", {"key": "M1-1", "status": "todo", "deps": []}),
                   put("tasks/two", {"key": "M1-2", "status": "todo", "deps": ["M1-1", "missing"]}))

    def test_persistence_atomic_conflict_and_merge(self):
        self.seed()
        old = self.get("tasks/one")
        self.batch(put("tasks/one", {"owner": "ana"}, old["version"], "update"))
        with self.assertRaises(board.BoardError) as caught:
            self.batch(put("notices/new", {"text": "must roll back"}),
                       put("tasks/one", {"owner": "ben"}, old["version"], "update"))
        self.assertEqual(caught.exception.error["index"], 1)
        self.assertEqual(caught.exception.error["path"], "tasks/one")
        self.assertFalse(self.get("notices/new")["exists"])
        fresh = board.Store(self.dbpath).request({"action": "get", "path": "tasks/one"})
        self.assertEqual(fresh["data"]["owner"], "ana")
        self.assertEqual(fresh["data"]["key"], "M1-1")
        with self.assertRaises(board.BoardError):
            self.batch(put("meta/config", {"title": "overwrite"}))

    def test_ready_query_matches_page_and_repairs_without_browser(self):
        self.seed()
        self.assertEqual(self.get("tasks/two")["data"]["waitingOn"], ["M1-1", "missing"])
        first = self.get("tasks/one")
        self.batch(put("tasks/one", {"status": "done"}, first["version"], "update"))
        self.assertEqual(self.get("tasks/two")["data"]["waitingOn"], ["missing"])
        second = self.get("tasks/two")
        self.batch(put("details/one", {"summary": "unrelated write"}))
        self.assertEqual(self.get("tasks/two")["version"], second["version"])
        ready = self.store.request({"action": "query", "collection": "tasks",
                                    "where": [["status", "==", "todo"], ["waitingOn", "==", []]]})
        self.assertEqual(ready["docs"], [])
        self.batch(put("tasks/missing", {"key": "missing", "status": "done"}))
        self.assertEqual(self.get("tasks/two")["data"]["waitingOn"], [])

    def test_queries_versions_paths_and_tombstones(self):
        self.seed()
        self.batch(put("tasks/one/messages/m-1", {"at": "2026-01-01", "text": "a"}),
                   put("tasks/one/messages/m-2", {"at": "2026-01-02", "text": "b"}))
        self.assertEqual(len(self.store.request({"action": "query", "collection": "tasks"})["docs"]), 2)
        found = self.store.request({"action": "query", "collection": "tasks/one/messages",
                                   "where": [["at", ">", "2026-01-01"]], "order_by": "at",
                                   "direction": "desc", "limit": 1})["docs"]
        self.assertEqual(found[0]["id"], "m-2")
        self.assertEqual(found[0]["version"], 1)
        found = self.store.request({"action": "query", "collection": "tasks",
                                   "where": [["deps", "array-contains", "M1-1"]]})["docs"]
        self.assertEqual(found[0]["id"], "two")
        for path in ("../secret", "tasks//x", "tasks/x/y", "/etc/passwd"):
            with self.assertRaises(board.BoardError):
                self.get(path)
        with self.assertRaises(board.BoardError):
            self.batch(put("details/missing", {}, 0, "update"))
        self.batch(put("details/gone", {}))
        self.batch(put("details/gone", {}, 1, "delete"))
        tombstone = self.get("details/gone")
        self.assertFalse(tombstone["exists"])
        self.assertEqual(tombstone["version"], 2)
        with self.assertRaises(board.BoardError):
            self.batch(put("details/gone", {}, 0))
        self.batch(put("details/gone", {}, tombstone["version"]))

    def test_two_cli_processes_cannot_claim_same_version(self):
        self.seed()
        version = self.get("tasks/one")["version"]
        def claim(who):
            request = {"action": "batch", "writes": [
                put("tasks/one", {"status": "doing", "claimedBy": {"who": who}}, version, "update"),
                put("tasks/one/messages/" + who, {"text": "claim"})
            ]}
            return subprocess.run([sys.executable, str(SCRIPT), "--db", str(self.dbpath), "request"],
                                  input=json.dumps(request), capture_output=True, text=True)
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results = list(pool.map(claim, ("ana", "ben")))
        self.assertEqual(sorted(r.returncode for r in results), [0, 1])
        loser = next(r for r in results if r.returncode)
        self.assertEqual(json.loads(loser.stderr)["code"], "conflict")
        messages = self.store.request({"action": "query", "collection": "tasks/one/messages"})["docs"]
        self.assertEqual(len(messages), 1)

    def test_http_boundaries_and_real_write(self):
        self.seed()
        server = board.make_server(self.store, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def cleanup():
            server.shutdown()
            server.server_close()
            thread.join()
        self.addCleanup(cleanup)
        port = server.server_port
        def call(method, path, data=None, headers=None):
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
            conn.request(method, path, json.dumps(data) if data is not None else None,
                         headers or {})
            response = conn.getresponse()
            result = response.status, response.read(), response.getheader("Access-Control-Allow-Origin")
            conn.close()
            return result
        headers = {"Content-Type": "application/json", "X-Artiboard": "1", "Origin": f"http://127.0.0.1:{port}"}
        data = {"action": "get", "path": "meta/config"}
        self.assertEqual(call("POST", "/api", data, headers)[0], 200)
        self.assertEqual(call("POST", "/api", data, {**headers, "Origin": "https://evil.test"})[0], 403)
        self.assertEqual(call("POST", "/api", data, {**headers, "Host": "evil.test"})[0], 403)
        self.assertEqual(call("POST", "/api", data, {**headers, "Content-Type": "text/plain"})[0], 415)
        self.assertEqual(call("POST", "/api", data, {"Content-Type": "application/json"})[0], 403)
        self.assertEqual(call("POST", "/api", data, {**headers, "Sec-Fetch-Site": "cross-site"})[0], 403)
        self.assertEqual(call("GET", "/../../board.sqlite3")[0], 404)
        self.assertEqual(call("GET", "/board.sqlite3")[0], 404)
        status, html, cors = call("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b'/local.js', html)
        self.assertIsNone(cors)
        self.assertIn(b'ARTIBOARD_STORAGE_KEY', call("GET", "/local.js")[1])
        data = {"action": "batch", "writes": [put("notices/browser", {"text": "persisted"})]}
        self.assertEqual(call("POST", "/api", data, headers)[0], 200)
        self.assertTrue(self.get("notices/browser")["exists"])
        self.assertEqual(call("POST", "/api", data, headers)[0], 409)
        self.assertEqual(call("POST", "/api", ["bad"], headers)[0], 400)

    def test_git_worktrees_share_default_database(self):
        repo = Path(self.temp.name) / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "-c", "user.name=Test", "-c", "user.email=test@example.test",
                        "commit", "--allow-empty", "-qm", "init"], check=True)
        linked = Path(self.temp.name) / "linked"
        subprocess.run(["git", "-C", str(repo), "worktree", "add", "-qb", "test", str(linked)],
                       capture_output=True, check=True)
        for cwd in (repo, linked):
            code = f"import runpy; m=runpy.run_path({str(SCRIPT)!r}); print(m['default_db']())"
            result = subprocess.check_output([sys.executable, "-c", code], cwd=cwd, text=True).strip()
            self.assertEqual(Path(result).resolve(), (repo / ".artiboard/board.sqlite3").resolve())

    def test_utf8_requests_with_ascii_terminal(self):
        req = {"action": "batch", "writes": [put("notices/korean", {"text": "한글 공지"})]}
        env = {**os.environ, "PYTHONIOENCODING": "ascii", "PYTHONUTF8": "0"}
        command = [sys.executable, str(SCRIPT), "--db", str(self.dbpath), "request"]
        result = subprocess.run(command, input=json.dumps(req, ensure_ascii=False).encode("utf-8"),
                                capture_output=True, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["docs"][0]["data"]["text"], "한글 공지")
        req["writes"][0]["path"] = "notices/from-file"
        request_file = Path(self.temp.name) / "request.json"
        request_file.write_text(json.dumps(req, ensure_ascii=False), encoding="utf-8")
        result = subprocess.run(command + ["--file", str(request_file)], capture_output=True, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.get("notices/from-file")["data"]["text"], "한글 공지")


if __name__ == "__main__":
    unittest.main()
