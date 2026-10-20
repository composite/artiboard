# Set up artiboard with a coding agent

artiboard is a project task-board skill for Codex and other agents with filesystem/shell access. It retains the Claude Artifact backend and provides a persistent loopback webserver when those tools are absent. Speak to the user in their language.

1. Inspect the project instructions and any existing artiboard pointer. Preserve its backend and data location. Read `skills/artiboard/SKILL.md` from this checkout; missing Artifact tools no longer stop a **new** local setup.
2. If asked to install, use the user's chosen scope and skill package manager. Project-local installation keeps runtime paths portable for teammates. A current `skills` CLI accepts the following, run in the target project:

   ```bash
   npx skills add /absolute/path/to/artiboard --skill artiboard --agent codex
   ```

   Select only agents actually used. Omit unwanted agent names. Add `--list` to preview discovery and `--global` only for an explicitly requested personal installation. Once the fork's `universal` branch has been published, the source can be `https://github.com/composite/artiboard/tree/universal`; do not use the unqualified default branch for this release. Inspect the installed paths and retain the package manager's lock metadata; upgrade with that manager from the same source. Do not overwrite a package-managed installation with manual copies. Users without this manager can use their host's supported skill installer or read `SKILL.md` directly without installing.
3. Validate that the installed skill contains `SKILL.md`, `assets/board.html`, `assets/local.js`, `scripts/local_board.py` and the linked references. In this session read it directly; a later session may be needed for automatic discovery. No global installation is implied by cloning or editing this repository.
4. If the user requested a board, follow setup in `SKILL.md`. Reuse provided people, language and approved tasks; ask only for missing choices. Use the actual `Artifact`/`ArtifactData` tools when available and appropriate, otherwise the local backend. Do not substitute unrelated canvas or document tools.
5. Report the installed/source location, selected backend, verification result and actual URL if running. For local mode include the DB path and stop/restart command; it is same-machine only and names are labels, not accounts. For Artifacts explain the platform's sharing controls. Do not commit, push, publish externally or install a background service unless authorized.

For source development in this repository, keep skill and runtime changes in `skills/artiboard/`, update the relevant package manifests and docs, run the checks documented in `README.md`, and rebuild the generated demo after changing the page. Do not seed real project tasks merely to test an enhancement.

## Codex plugin installation

The repository provides portable `plugin.json`, a `.codex-plugin/plugin.json` compatibility overlay and `.agents/plugins/marketplace.json`. All use the same `skills/artiboard/` source; there is no extra MCP service or install hook. For an explicitly requested Codex plugin installation:

```bash
codex plugin marketplace add /absolute/path/to/artiboard
codex plugin add artiboard@artiboard-universal
```

These commands modify the current Codex user's plugin configuration. Prefer the Skills CLI route for project-local skill installation. In the desktop app the source is **Artiboard Universal**; restart if it is not visible. After the remote branch is published, `codex plugin marketplace add composite/artiboard --ref universal` can register the Git source. Inspect existing marketplace settings before changing their source.

## Claude Code uses upstream

For Claude Code, use the original [yulmucoffee/artiboard](https://github.com/yulmucoffee/artiboard), not this fork's local runtime package:

```bash
claude plugin marketplace add yulmucoffee/artiboard --scope project
claude plugin install artiboard@artiboard --scope project
```

The `.claude-plugin` manifests retain the upstream identity and contents. Do not register this fork as a replacement Claude marketplace or silently replace an existing upstream install. The Codex marketplace `artiboard-universal` is separate. Avoid duplicate skill installations within one agent.

## Package maintenance

Keep the version and publisher/source metadata aligned in `plugin.json`, `.codex-plugin/plugin.json` and `skills/artiboard/SKILL.md`. Leave the upstream `.claude-plugin` manifests unchanged. Preserve upstream credit and keep the bundled `skills/artiboard/LICENSE` identical to the root license: Skills CLI installs the skill folder on its own. Validate discovery and installation using the real package manager; metadata alone is not proof that runtime assets are included.
