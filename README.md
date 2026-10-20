# artiboard

A project task board for people and coding agents: tasks, threads, notices, document and kanban views, and a dependency graph. The page renders from persistent data; routine refreshes do not need model calls.

**English** · [한국어](README.ko.md) · [日本語](README.ja.md) · [简体中文](README.zh-CN.md) · [Español](README.es.md)

| Backend | Requirements | Collaboration |
| --- | --- | --- |
| Claude Artifact | Actual `Artifact` and `ArtifactData` tools | Platform sharing and account capabilities |
| Local webserver | Python 3.10+ with SQLite; a modern browser | Trusted people/agents on one machine, including parallel Git worktrees |

Codex and other filesystem/shell agents can use the local backend. A new board defaults to Artifacts when both tools exist, otherwise local. An existing board keeps its backend; migration is an explicit action. A local person name is a self-selected label, **not an authenticated account**. Local mode is not a remote team hosting service.

## Quick start

Ask your coding agent:

```text
Read skills/artiboard/SKILL.md from this checkout and set up a task board for this project.
Use the local backend if Artifact tools are unavailable.
```

For project-local skill installation, run your skill manager from the target project. With the `skills` CLI:

```bash
npx skills add /absolute/path/to/artiboard --skill artiboard --agent codex claude-code
```

Select the agents you use. Personal/global installation is optional (`--global`), not required. See [FOR_AGENTS.md](FOR_AGENTS.md) for agent setup and upgrade rules. Clone or edit of the source alone does not install it globally.

To run an empty local board directly from this checkout, choose your title/person ID, then:

```bash
python3 skills/artiboard/scripts/local_board.py init --title "My project" --person ana --lang en
python3 skills/artiboard/scripts/local_board.py serve --port 8765
```

Use `python` or `py -3` if that is your Python 3.10+ launcher. Open the URL printed by the server. Ctrl-C stops it; the same command restarts it with its data intact. Use `--port 0` if the default port is occupied. There is no background-service installation.

The default DB is `.artiboard/board.sqlite3` in the main Git checkout, shared by linked worktrees, or the current directory outside Git. Use `--db <path>` **before** the subcommand to choose another location. Record the resolved shared path in the project protocol and keep `.artiboard/` ignored. The server serves only its page/adapter; it does not expose repo files. It binds only `127.0.0.1` and rejects cross-site requests. Other local processes/users are within its trust boundary.

Agents query and update the same SQLite file without a running server:

```bash
python3 skills/artiboard/scripts/local_board.py request <<'JSON'
{"action":"query","collection":"tasks","where":[["status","==","todo"],["waitingOn","==",[]]],"limit":20}
JSON
```

See [local backend](skills/artiboard/references/local.md) for seeding, versioned batches, customization, backups and lifecycle. See [Artifact backend](skills/artiboard/references/artifact.md) for publication, identity and sharing through Claude's tools.

## Use it

| Request | Behavior |
| --- | --- |
| “Set up a task board”, “작업 보드 만들어줘” | Resolve people/language/task source, confirm a proposed task list, create the selected backend and install a short repo pointer. |
| “Pick the next task”, “Continue M1-4” | Read the project's protocol; query ready work, claim with version checks, record a short handoff. |
| “Add Cy”, “Switch to Korean” | Update config without rebuilding the page. |
| “Add a QA status”, “Show estimates” | Adapt the project page and protocol together. |
| “Upgrade the board” | Preserve data and customizations, back up, update runtime and verify the same board. |

Setup writes `docs/artiboard.md` and a marked pointer in the project's established `AGENTS.md` and/or `CLAUDE.md`. The rules are loaded only for board work. Messages are untrusted project data, never permission to run commands, send external messages, merge or deploy.

## Data and token use

| Location | Purpose |
| --- | --- |
| `tasks/<id>` | Key, title, status, owner, deps, `waitingOn`, claim, branch/PR |
| `details/<id>` | Spec pointer, acceptance and a short handoff summary |
| `tasks/<id>/messages` | Updates, questions and handoffs; agents usually query the latest eight |
| `notices`, `cursors/<person>` | Shared changes, read incrementally after the last seen notice |
| `meta/config` | Title, people, language and UI-string overrides |
| `meta/protocol` | Human copy of the repository rules; agents read the repo source |
| `people/<person>` | Artifact account links only; unused by local identity |

Claims use atomic, versioned batches. A stale version rolls back the whole batch. Local mode uses SQLite transactions across CLI and browser clients; its UI claims also check versions. Local readiness is recalculated transactionally even with the browser closed. Artifact agents update dependency readiness themselves, with page repair while open. The inherited Artifact UI's claim button uses read-then-update; the stronger atomic-claim guarantee there applies to agents using versioned ArtifactData batches.

Views, search, keyboard navigation (`j`/`k`, `1`/`2`/`3`) and “new” markers are computed by code. Task lists stay lean; details and summaries load only when needed. Local browser preferences are separated per database. The local server polls changed snapshots and reports a disconnected server; it does not enqueue offline writes.

Config supports `title`, `subtitle`, `milestone`, `lang` (`en` or `ko` built in), `people` (`id`, optional `name` and `role`), `strings` (UI overrides), and `footer`. Artifact people can additionally have a pinned `uid`; local mode does not authenticate these IDs. Preserve `todo` and `done` semantics when customizing statuses.

## Demo and development

[Original interactive demo](https://claude.ai/artifact/5zENFyGDJbEjey68J6t1bY) and `examples/demo.html` use disposable in-memory sample data, not the persistent local backend.

```bash
npm install --no-save --no-audit --no-fund jsdom@24.1.1
python3 -m unittest discover -s tests -p 'test_*.py' -v
node tests/smoke.cjs
node tests/local-smoke.cjs
node examples/build-demo.cjs
```

Python tests cover persistence, rollback, concurrent CLI claims, query semantics, worktree paths and HTTP boundaries. jsdom runs the existing Artifact-shaped fake tests and the real local server/adapter/page flow, including concurrent browser claims, disconnection and restart. CI also checks manifests, script syntax and demo freshness. jsdom is a development dependency only.

```text
skills/artiboard/SKILL.md            backend routing and workflow
skills/artiboard/agents/openai.yaml Codex discovery metadata
skills/artiboard/assets/            shared page and local browser adapter
skills/artiboard/scripts/           standard-library local runtime/CLI
skills/artiboard/references/        local, Artifact and project protocol guidance
```

Based on the original artiboard by yulmucoffee, created for a multi-agent product team on claude.ai. Independent of and not endorsed by Anthropic or OpenAI. [MIT License](LICENSE).
