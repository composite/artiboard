# Claude Artifact backend

Read only when the actual `Artifact` and `ArtifactData` tools are available. Discover deferred tools through the host's tool discovery and inspect their current schemas; a Claude subscription or a tool with a similar name is not evidence of these capabilities. Do not use Spaces spreadsheets, Pages or unrelated canvas tools as an Artifact database.

## Publish and seed


Copy `assets/board.html` into your scratchpad. Set its `<title>` to the board name, two to four words, such as `Acme Board`. Edit the copy only for requested page customizations. Publish it with the Artifact tool: `capabilities: {"db": {}, "user": {}}`, `icon: "kanban"`, a one-sentence `description`. Keep the URL. `user` tells the page who is viewing: it links each person to the claude.ai account that first picks them in the "I am" picker (`people/<id>`), defaults to that person on later visits, warns when someone posts as a person linked to another account, and hides claim, post and edit controls from view-only viewers.

### Seed the database

Write everything with ArtifactData `batch`, at most 50 writes per call (split larger seeds). Use `file_path` for long documents.

```json
"meta/config":   {"title": "Acme Board", "subtitle": "What the board is for, one sentence.", "milestone": "M1",
                  "lang": "en", "people": [{"id": "ana", "name": "Ana", "role": "backend"}, {"id": "ben"}],
                  "strings": {}}
"meta/protocol": {"text": "<human copy of the rules>", "rev": 1, "updatedAt": "<ISO>"}
"tasks/M1-3":    {"key": "M1-3", "title": "...", "feature": "...", "milestone": "M1", "status": "todo",
                  "owner": null, "deps": ["M1-1"], "waitingOn": ["M1-1"], "claimedBy": null,
                  "branch": null, "pr": null, "updatedAt": "<ISO>"}
"details/M1-3":  {"spec": "docs/api.md §2", "acceptance": "...", "summary": "", "summaryAt": null}
"notices/n-<ISO with colons as hyphens>-<person>": {"at": "<ISO>", "author": "<person>", "kind": "agent", "type": "note", "text": "Board is up. ..."}
```

Set `waitingOn` to unfinished dependencies; it equals `deps` only when none are done. In `meta/protocol`, write numbered sections (`0. Collections`) with `- ` bullets. The page renders them as cards. Lines before the first number become an intro card.

## Fill the project protocol

- `BACKEND_ACCESS`: record **Artifact**, its URL/ID and the available ArtifactData get/query/batch tools with the actual argument names.
- `VERSION_RULES`: pin existing writes to the `version` read using `if_version`, and use the tool's documented create-only precondition for new paths. One logical action is an atomic batch; on conflict reread and retry only as specified in the common protocol.
- `READINESS_RULES`: when completing a task, query tasks where `deps array-contains "<key>"`; in the same versioned batch remove that key from each dependent's `waitingOn`. Respect the backend's write limit, query pagination and other sessions' newer versions. For a fan-out too large for one batch, finish all dependent updates before reporting readiness synchronized. The page also repairs drift while open.
- Remove the `LOCAL_LIMITS` bullet entirely. Account capabilities and sharing are governed by the Artifact platform.

Fill the remaining placeholders from the user's project. Do not copy local command envelopes or its version 0 convention here.


## Daily access and upgrades

Use ArtifactData for get/query/batch, with the tool's actual argument names and version/create preconditions. The local backend's JSON envelope and version 0 convention are **not** an ArtifactData API specification. Pin existing writes to the version read; consult the live tool schema for create-only writes. Never substitute unconditional overwrite for a missing atomic precondition.

Keep `people/<id>` and the `user` capability on this backend. The page links each person to the first claude.ai account that picks them; agents do not write these links. A wrong link can be removed at the user's request; an optional `meta/config.people[].uid` overrides the link. Do not guess account IDs.

For adapt/upgrade, read the live artifact first, preserve customizations, and publish to the same URL only for page changes. Config/data changes do not require republishing. Keep `capabilities: {"db": {}, "user": {}}`.

The page repairs `waitingOn` only while open. Agents completing tasks must update dependent tasks in versioned batches; do not rely on an open browser. Query readiness and config after seeding. Sharing is performed through the platform's controls, within the user's authorization; do not describe a local URL as a shared artifact.

Artifact quotas are provider-specific: check current tool errors/docs before archival. Propose counts and a backup before deleting old tasks, details, messages or notices. Moving documents into another collection does not reduce document count.
