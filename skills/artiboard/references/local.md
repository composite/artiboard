# Local backend

Python 3.10+ with SQLite is sufficient; no npm install or cloud account is needed to run the board. Locate an available interpreter (`python3`, `python`, or `py -3` on Windows) and check its version. Examples below use `python3`.

## Setup and lifetime

Use the installed skill's `scripts/local_board.py`. For team projects, install the skill project-locally with the project's skill manager and record its actual repository-relative path in the protocol; do not record your personal absolute skill path for teammates. Include the whole skill (assets and references), not just the script. Do not add a runtime copy inside the ignored data directory. A customized page can live at a tracked project path and be selected with `serve --page <path>`.

The commands below assume the source checkout layout. Substitute the installed script path when setting up another project. Resolve and record one database path for every participating session. By default it is `.artiboard/board.sqlite3` under the main Git checkout (shared across linked worktrees), or under the current directory outside Git. `--db` explicitly overrides this. For nonstandard/bare Git layouts, select `--db` explicitly. In a sandbox, use an authorized shared writable location; if access fails, stop and resolve it rather than creating a different board.

Add `.artiboard/` to the data owner's `.gitignore` before creating data (covers SQLite journal files too). If `--db` is elsewhere, ignore that data and its journal files there. Keep the database on a local filesystem with working SQLite locks, not network storage, cloud-sync folders or a Git-merged binary. All participating local processes must have permission to that same file.

```bash
# Replace these example people/title with the user's supplied choices.
python3 skills/artiboard/scripts/local_board.py --db .artiboard/board.sqlite3 init --title "Project Board" --person ana --person ben --lang en
python3 skills/artiboard/scripts/local_board.py --db .artiboard/board.sqlite3 serve --port 8765
```

`init` creates only `meta/config`, no invented tasks, and refuses to overwrite it. Successful writes return documents with their current versions. Do not assume the version is 1: dependency repair can increment it too.

The server prints its actual `http://127.0.0.1:<port>/` URL. Open that URL with the host's browser tool or share it as a local link. In Codex Desktop, use the available browser/open tool when present. If port 8765 is occupied, use `--port 0`, record the printed URL, and do not kill the other process. `localhost` aliases are intentionally rejected by Host validation; use the printed IP URL.

Keep a server handle/PID and report its lifetime. Ctrl-C stops the server without deleting the DB. Restart the same command and database to resume. If the agent's execution environment cannot keep a server alive or bind a socket, give the launch command for a user terminal and say the preview is not running. The CLI below continues to work without a server or browser. Do not claim a background service was installed.

## Agent data access

Pass JSON by stdin or `request --file <request.json>`; never compose shell code from board content. Run from the documented project root or use resolved paths. Every response is JSON; failures return JSON on stderr and a nonzero exit code. HTTP requests, when needed, use `POST /api`, `Content-Type: application/json`, `X-Artiboard: 1` and the same JSON envelope. Browser requests must be same-origin. The CLI is the simpler agent route.

```bash
python3 skills/artiboard/scripts/local_board.py --db .artiboard/board.sqlite3 request <<'JSON'
{"action":"query","collection":"tasks","where":[["status","==","todo"],["waitingOn","==",[]]],"limit":20}
JSON
```

Requests:

```json
{"action":"get","path":"tasks/M1-1"}
{"action":"query","collection":"notices","where":[["at",">","2026-01-01T00:00:00.000Z"]],"order_by":"at","direction":"asc","limit":20}
{"action":"query","collection":"tasks/M1-1/messages","order_by":"at","direction":"desc","limit":8}
{"action":"query","collection":"tasks","where":[["deps","array-contains","M1-1"]],"limit":20}
```

`get` returns `{path, id, exists, data, version}`; `query` returns `{docs: [...]}` in that same shape. Queries include direct children only. Supported filters: `==` (including arrays), `>`, `>=`, `<`, `<=`, `array-contains`. Range comparisons require matching scalar types; missing fields do not match ranges. Ordering is lexical, appropriate for normalized UTC ISO timestamps and task keys. Use a consistent millisecond UTC timestamp format. Default limit is 20; the UI alone uses `limit: null` to render the whole collection. Do not request an unbounded collection for routine agent work.

Seed only approved tasks. A batch has 1–50 unique paths; split larger seeds. `set` replaces a document, `update` merges top-level fields and requires an existing document, `delete` deletes its content. Every write requires `if_version`: use the value read; a never-created path has version 0. A deleted path retains a version, so reread it before deliberate recreation. No unconditional overwrite is available.

```json
{"action":"batch","writes":[
  {"op":"set","path":"tasks/M1-1","if_version":0,"data":{"key":"M1-1","title":"Approved task title","feature":"Core","status":"todo","owner":null,"deps":[],"claimedBy":null}},
  {"op":"set","path":"details/M1-1","if_version":0,"data":{"spec":"docs/plan.md","acceptance":"The agreed observable result.","summary":"","summaryAt":null}}
]}
```

A claim is one batch with a versioned task update, a create-only message and the cursor update, following `protocol.md`. Use a unique session ID and a random suffix on message/notice IDs. Preserve newer cursor values. On conflict the whole batch rolls back and the error includes `code: "conflict"`, zero-based `index`, and `path`. Re-read before a bounded retry; never overwrite another session's claim. UI claims also pin the version from their readiness check.

The store recalculates `waitingOn` in the same transaction as every batch, including browser changes and deletions, using task **keys**, raw `status == "done"` and dependency order. Missing keys remain blocked. It increments versions only where derived data changes. No open page or agent repair is required. Reads scan the small local board; this is not a large-scale issue database.

## Fill the project protocol

- `BACKEND_ACCESS`: record **local**, actual script/interpreter, data-owner root and explicit `--db` path, the `request` command, and server launch command/URL. Include the get/query/batch JSON shapes above so daily sessions need not reload the setup skill.
- `VERSION_RULES`: every write uses the version read; 0 means never-created; deleted documents retain versions; 1–50 unique writes are atomic; describe the conflict response and bounded retry.
- `READINESS_RULES`: local store computes readiness transactionally; reread versions after completion because dependent tasks may change.
- `LOCAL_LIMITS`: same-machine trusted collaboration only; identity labels are self-selected, not authenticated. No remote sharing or account permission enforcement.

Fill the other placeholders from the user's project. For an Artifact project, use its actual tools/schema instead, and remove the local-only line.

## Verify and maintain

Query config and ready work, then open the real URL and exercise document/kanban/graph, task detail and an authorized write. Confirm it persists via CLI and after a server restart. Check errors are surfaced and no task claim is overwritten on a stale version. The static `examples/demo.html` uses disposable in-memory data and is not persistence verification.

For upgrade, stop only the server you own, preserve customized pages/protocols, back up the DB with Python's `sqlite3.Connection.backup()` API or by copying it while **all writers** are stopped, update the installed skill through its manager, and restart with the same `--db` and optional `--page`. Backups contain project data and stay private and ignored. A database is not recreated during upgrade.

The server binds only `127.0.0.1`. Only the board and adapter are served; database/repository files are not exposed as static files. Host, Origin, JSON content type and a non-simple request header reject cross-site browser access. Other trusted processes/users on the same machine can access the service: it is not an authentication boundary. A local URL is not a team sharing link across machines. Remote service, tunnels and authentication require a separately authorized design.
