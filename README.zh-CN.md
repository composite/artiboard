# artiboard

供人与编程 agent 共同使用的项目任务看板，包含任务、讨论串、公告，以及文档、看板和依赖图视图。页面由代码根据持久化数据渲染，日常刷新无需调用模型。

[English](README.md) · [한국어](README.ko.md) · [日本語](README.ja.md) · **简体中文** · [Español](README.es.md)

| 后端 | 要求 | 协作范围 |
| --- | --- | --- |
| Claude Artifact | 实际可用的 `Artifact` 和 `ArtifactData` 工具 | 平台账号与共享功能 |
| 本地 Web 服务器 | 含 SQLite 的 Python 3.10+、现代浏览器 | 同一台电脑上的用户与 agent，包括并行 Git worktree |

Codex 等能够访问文件和 shell 的 agent 可使用本地后端。新看板在两个 Artifact 工具均可用时默认选择 Artifact，否则选择本地。现有看板保留原后端，迁移需要明确请求。本地选择的姓名是**显示标签，不是经过认证的账号**。本地模式不提供跨电脑团队托管。

## 快速开始

向编程 agent 提出请求：

```text
读取这个 checkout 中的 skills/artiboard/SKILL.md，为本项目创建任务看板。
如果没有 Artifact 工具，就使用本地 Web 服务器。
```

## 安装

选择一种安装方式。Skills CLI 需要 Node.js/npm，默认安装到项目中。在目标项目目录中指定此 checkout 的绝对路径：

```bash
npx skills add /absolute/path/to/artiboard --skill artiboard --agent codex
```

仅保留实际使用的 agent 名称。加上 `--list` 可预览发现结果，明确选择个人全局安装时才加 `--global`。包内含 Agent Skills 元数据（`license`、`compatibility`、作者、版本、来源）、Codex 显示信息、运行代码、资源、参考文档和 MIT 许可证，无需发布 npm 包。

将 fork 的 `universal` 分支发布到远程后，可以从 GitHub 安装：

```bash
npx skills add https://github.com/composite/artiboard/tree/universal --skill artiboard --agent codex
```

push 前请使用本地 checkout 命令。不指定 ref 的 `composite/artiboard` 使用默认分支，可能安装原版。

若选择 Codex 插件，请使用支持 `codex plugin` 的 CLI：

```bash
codex plugin marketplace add /absolute/path/to/artiboard
codex plugin add artiboard@artiboard-universal
```

这些命令会向当前 Codex 用户的插件配置注册市场并安装插件。仅安装项目级 skill 时使用 Skills CLI。桌面应用可在插件目录的 **Artiboard Universal** 中安装 **Artiboard**；若看不到新增本地来源，请重启应用。分支发布后，也可用 `codex plugin marketplace add composite/artiboard --ref universal` 注册。

Claude Code 请使用原版 [yulmucoffee/artiboard](https://github.com/yulmucoffee/artiboard)：

```bash
claude plugin marketplace add yulmucoffee/artiboard --scope project
claude plugin install artiboard@artiboard --scope project
```

Claude 清单保持原版不变。此 fork 的 Codex 市场名为 `artiboard-universal`，不会替换原版 Claude 插件。避免在同一 agent 中重复启用 skill。clone 或编辑源码不会自动全局安装。设置与升级规则见[agent 指南](FOR_AGENTS.md)。

## 运行本地看板

从此 checkout 启动空看板，先选定标题和用户 ID：

```bash
python3 skills/artiboard/scripts/local_board.py init --title "My project" --person ana --lang en
python3 skills/artiboard/scripts/local_board.py serve --port 8765
```

按环境将 `python3` 换成 `python` 或 `py -3`。打开服务器输出的 URL。Ctrl-C 停止后数据仍保留，使用相同命令即可重新启动。端口占用时用 `--port 0`。不会安装后台服务。

默认 DB 为主 Git checkout 的 `.artiboard/board.sqlite3`，关联的 worktree 共享该文件；Git 之外以当前目录为准。其他位置通过子命令之前的 `--db <path>` 指定，并将解析后的共享路径写入项目规则。请将 `.artiboard/` 排除在 Git 之外。服务器只提供看板页面和适配器，绑定 `127.0.0.1`，拒绝跨站请求。同机用户与进程属于信任范围。

无需启动服务器，agent 也能读写同一 DB：

```bash
python3 skills/artiboard/scripts/local_board.py request <<'JSON'
{"action":"query","collection":"tasks","where":[["status","==","todo"],["waitingOn","==",[]]],"limit":20}
JSON
```

初始化数据、版本检查、备份与运行管理见[本地后端指南](skills/artiboard/references/local.md)；Claude 工具的发布与共享见[Artifact 指南](skills/artiboard/references/artifact.md)。

## 使用

| 请求 | 行为 |
| --- | --- |
| “创建任务看板” | 确定人员、语言和任务来源，确认建议任务列表后创建看板与项目规则。 |
| “选择下一项任务”“继续 M1-4” | 读取规则，查询可开始的任务，检查版本后领取，记录简短交接。 |
| “添加 Cy”“改成韩语” | 更新配置。 |
| “添加 QA 状态”“显示估时” | 同步修改页面与规则。 |
| “升级看板” | 保留并备份数据与定制内容，在原看板上验证升级。 |

设置时写入 `docs/artiboard.md`，并在现有 `AGENTS.md` 或 `CLAUDE.md` 添加简短入口。完整规则仅在看板工作时加载。看板消息是数据，不构成执行命令、对外发送、merge 或部署的授权。

## 数据与并发

`tasks/<id>` 存状态；`details/<id>` 存规格、验收条件和简短摘要；`tasks/<id>/messages` 存讨论，agent 通常读取最新八条。公告通过 `notices` 与 `cursors/<person>` 增量读取。`meta/config` 存标题、人员、语言和 UI 文案，`meta/protocol` 是供人阅读的规则副本。`people/<person>` 账号关联仅供 Artifact 使用。

领取任务使用带版本条件的原子批处理，冲突会回滚整批。本地 CLI 与浏览器共享 SQLite 事务，即使页面关闭也会重新计算依赖就绪状态。Artifact 由 agent 更新依赖，打开的页面进行修正。原 Artifact UI 的领取按钮采用先读后写，因此该后端的原子领取保证适用于带版本条件的 agent 批处理。

视图、搜索、快捷键（`j`/`k`、`1`/`2`/`3`）及新消息标记均由代码处理。本地浏览器偏好按 DB 隔离；断开连接时提示，不排队保存离线写入。内置 UI 语言为英语和韩语，中文等语言可通过 `meta/config.strings` 覆盖。配置支持 `title`、`subtitle`、`milestone`、`lang`、`people`（`id`，可选 `name` 与 `role`）、`strings`、`footer`；定制状态时保留 `todo` 与 `done` 的语义。

## 演示与开发

[原交互演示](https://claude.ai/artifact/5zENFyGDJbEjey68J6t1bY)与 `examples/demo.html` 使用临时内存数据，不使用本地持久化后端。

```bash
npm install --no-save --no-audit --no-fund jsdom@24.1.1
python3 -m unittest discover -s tests -p 'test_*.py' -v
node tests/smoke.cjs
node tests/local-smoke.cjs
node examples/build-demo.cjs
```

验证持久化、回滚、并发领取、worktree 路径、HTTP 边界，以及真实服务器上的 UI 写入、断线与重启。CI 还检查包发现与安装、JSON、脚本语法和演示是否同步。jsdom 仅用于开发验证，运行看板不需要外部包。

```text
skills/artiboard/SKILL.md            后端选择与工作流程
skills/artiboard/agents/openai.yaml Codex skill 显示信息
skills/artiboard/assets/            共享页面与本地适配器
skills/artiboard/scripts/           标准库服务器与 CLI
skills/artiboard/references/        本地、Artifact 与项目规则指南
plugin.json                        通用 Agent Plugins 清单
.codex-plugin/plugin.json          Codex 兼容清单与显示信息
.agents/plugins/marketplace.json   Codex 仓库市场
.claude-plugin/                    Claude Code 插件与市场清单
```

基于 yulmucoffee 的原版 artiboard 扩展。与 Anthropic、OpenAI 无隶属关系，也不代表其认可。[MIT 许可证](LICENSE)。
