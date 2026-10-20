# Set up artiboard with a coding agent

artiboard is a project task-board skill for Codex, Claude Code and other agents with filesystem/shell access. It retains the Claude Artifact backend and provides a persistent loopback webserver when those tools are absent. Speak to the user in their language.

1. Inspect the project instructions and any existing artiboard pointer. Preserve its backend and data location. Read `skills/artiboard/SKILL.md` from this checkout; missing Artifact tools no longer stop a **new** local setup.
2. If asked to install, use the user's chosen scope and skill package manager. Project-local installation keeps runtime paths portable for teammates. A current `skills` CLI accepts the following, run in the target project:

   ```bash
   npx skills add /absolute/path/to/artiboard --skill artiboard --agent codex claude-code
   ```

   Select only agents actually used. Omit unwanted agent names. Add `--global` only for an explicitly requested personal installation. Inspect the installed paths and retain the package manager's lock metadata; upgrade with that manager from the same source. Do not overwrite a package-managed installation with manual copies. Users without this manager can use their host's supported skill installer or read `SKILL.md` directly without installing.
3. Validate that the installed skill contains `SKILL.md`, `assets/board.html`, `assets/local.js`, `scripts/local_board.py` and the linked references. In this session read it directly; a later session may be needed for automatic discovery. No global installation is implied by cloning or editing this repository.
4. If the user requested a board, follow setup in `SKILL.md`. Reuse provided people, language and approved tasks; ask only for missing choices. Use the actual `Artifact`/`ArtifactData` tools when available and appropriate, otherwise the local backend. Do not substitute unrelated canvas or document tools.
5. Report the installed/source location, selected backend, verification result and actual URL if running. For local mode include the DB path and stop/restart command; it is same-machine only and names are labels, not accounts. For Artifacts explain the platform's sharing controls. Do not commit, push, publish externally or install a background service unless authorized.

For source development in this repository, keep changes in `skills/artiboard/`, update the relevant docs, run the checks documented in `README.md`, and rebuild the generated demo after changing the page. Do not seed real project tasks merely to test an enhancement.

## Existing Claude plugin users

The `.claude-plugin` manifests remain supported. To install this checkout through Claude's plugin manager, use the selected scope explicitly:

```bash
claude plugin marketplace add /absolute/path/to/artiboard --scope project
claude plugin install artiboard@artiboard --scope project
```

Inspect an existing marketplace named `artiboard` before replacing it; it may point to the upstream release. A local plugin-source path is machine-specific. For a team's reproducible setup, prefer the project-local skill-manager route above and record the runtime's installed path. Do not install both routes unnecessarily.
