# artiboard

人とコーディングエージェントが共有するプロジェクト用タスクボードです。タスク、スレッド、お知らせ、ドキュメント・カンバン・依存グラフの各ビューを提供します。保存されたデータからコードが画面を描くため、通常の更新にモデル呼び出しは不要です。

[English](README.md) · [한국어](README.ko.md) · **日本語** · [简体中文](README.zh-CN.md) · [Español](README.es.md)

| バックエンド | 必要なもの | 共同作業の範囲 |
| --- | --- | --- |
| Claude Artifact | 実際の `Artifact` と `ArtifactData` ツール | プラットフォームのアカウント・共有機能 |
| ローカルWebサーバー | SQLiteを含むPython 3.10以上、最新のブラウザー | 同じコンピューターの人とエージェント、並行するGit worktree |

Codexなど、ファイルとシェルを使えるエージェントはローカル方式を利用できます。新規ボードでは両方のArtifactツールがあればArtifactを、なければローカルを選びます。既存ボードのバックエンドは維持し、移行は明示的な依頼で行います。ローカルの名前は**認証済みアカウントではなく表示ラベル**です。リモートチーム向けのホスティングサービスではありません。

## クイックスタート

コーディングエージェントに依頼します。

```text
このcheckoutのskills/artiboard/SKILL.mdを読み、このプロジェクトにタスクボードを作って。
ArtifactツールがなければローカルWebサーバーを使って。
```

## インストール

方式を一つ選びます。Skills CLIにはNode.js/npmが必要です。既定ではプロジェクト内にインストールします。対象プロジェクトで、このcheckoutの絶対パスを指定します。

```bash
npx skills add /absolute/path/to/artiboard --skill artiboard --agent codex
```

使うエージェント名だけ残してください。`--list`で検出結果を確認でき、個人用のグローバルインストールを選ぶ場合は`--global`を追加します。Agent Skillsのメタデータ（`license`、`compatibility`、作者・バージョン・出典）、Codexの表示情報、実行コード、アセット、参考文書、MITライセンスを同梱しています。npmへのパッケージ公開は不要です。

forkの`universal`ブランチをリモートに公開した後は、GitHubからインストールできます。

```bash
npx skills add https://github.com/composite/artiboard/tree/universal --skill artiboard --agent codex
```

push前はローカルcheckoutのコマンドを使ってください。refのない`composite/artiboard`はデフォルトブランチを使うため、元の版が入る可能性があります。

Codexプラグインとして使う場合は、`codex plugin`対応CLIで実行します。

```bash
codex plugin marketplace add /absolute/path/to/artiboard
codex plugin add artiboard@artiboard-universal
```

現在のCodexユーザーのプラグイン設定に登録・インストールします。プロジェクト内だけのスキルにはSkills CLIを使います。デスクトップアプリではプラグインディレクトリの**Artiboard Universal**から**Artiboard**をインストールできます。新しいローカルソースが表示されなければ再起動してください。ブランチ公開後は`codex plugin marketplace add composite/artiboard --ref universal`でも登録できます。

Claude Codeでは元の[yulmucoffee/artiboard](https://github.com/yulmucoffee/artiboard)を使ってください。

```bash
claude plugin marketplace add yulmucoffee/artiboard --scope project
claude plugin install artiboard@artiboard --scope project
```

Claudeのマニフェストは元のまま維持します。このforkのCodexマーケットプレイス名は`artiboard-universal`で、元のClaudeプラグインを置き換えません。同じエージェントでスキルを重複して有効にしないでください。cloneやソース編集だけでグローバルインストールされることはありません。手順と更新方法は[エージェント向けガイド](FOR_AGENTS.md)を参照してください。

## ローカルボードの起動

このcheckoutから空のボードを起動する例です。タイトルとユーザーIDを選びます。

```bash
python3 skills/artiboard/scripts/local_board.py init --title "My project" --person ana --lang en
python3 skills/artiboard/scripts/local_board.py serve --port 8765
```

Pythonの起動方法に応じて`python`や`py -3`に置き換えます。サーバーが表示するURLを開いてください。Ctrl-Cで停止してもデータは残り、同じコマンドで再開できます。ポートが使用中なら`--port 0`を使います。バックグラウンドサービスはインストールしません。

既定のDBはメインGit checkoutの`.artiboard/board.sqlite3`で、リンクされたworktreeも共有します。Git外では現在のディレクトリが基準です。別の場所はサブコマンドの前に`--db <path>`で指定し、解決済みの共有パスをプロジェクトのルールに記録してください。`.artiboard/`はGitの管理対象から外します。サーバーはボードとアダプターだけを配信し、`127.0.0.1`にのみバインドしてクロスサイト要求を拒否します。同じコンピューターのユーザーとプロセスは信頼範囲に含まれます。

エージェントはサーバーなしでも同じDBを読み書きできます。

```bash
python3 skills/artiboard/scripts/local_board.py request <<'JSON'
{"action":"query","collection":"tasks","where":[["status","==","todo"],["waitingOn","==",[]]],"limit":20}
JSON
```

初期データ、バージョン付きバッチ、バックアップは[ローカルガイド](skills/artiboard/references/local.md)、Claudeでの公開と共有は[Artifactガイド](skills/artiboard/references/artifact.md)を参照してください。

## 使い方

| 依頼 | 動作 |
| --- | --- |
| 「タスクボードを作って」 | 人・言語・タスクの出典を確認し、提案したタスク一覧の承認後にボードとプロジェクトルールを作成。 |
| 「次のタスクを選んで」「M1-4を続けて」 | ルールを読み、実行可能なタスクを検索し、バージョンを確認して担当を取得、短い引き継ぎを記録。 |
| 「Cyを追加して」「韓国語にして」 | 設定を変更。 |
| 「QA状態を追加して」「見積もりを表示して」 | ページとルールを一緒に更新。 |
| 「ボードを更新して」 | データとカスタマイズを保護・バックアップし、同じボードで検証。 |

セットアップ時に`docs/artiboard.md`と、既存の`AGENTS.md`や`CLAUDE.md`への短い参照を作ります。全ルールはボード作業時だけ読み込みます。ボードのメッセージはデータであり、コマンド実行、外部送信、merge、デプロイの許可ではありません。

## データと同時作業

`tasks/<id>`は状態、`details/<id>`は仕様・受け入れ条件・短い要約、`tasks/<id>/messages`は会話です。エージェントは通常最新8件を読みます。お知らせは`notices`と`cursors/<person>`で差分取得します。`meta/config`はタイトル・人・言語・UI文言、`meta/protocol`は人向けルールのコピーです。`people/<person>`によるアカウント連携はArtifact専用です。

担当取得にはバージョン付きの原子的バッチを使い、競合するとバッチ全体を取り消します。ローカルではCLIとブラウザーがSQLiteトランザクションを共有し、画面を閉じても依存関係の準備状態を再計算します。Artifactではエージェントが依存関係を更新し、開いたページが補正します。元のArtifact UIの担当ボタンは読み取り後の更新なので、同方式の原子的取得保証はバージョン付きエージェントバッチに適用されます。

ビュー、検索、`j`/`k`・`1`/`2`/`3`キー、新着表示はコードが処理します。ローカルブラウザー設定はDBごとに分離し、切断時は通知してオフライン書き込みを予約しません。組み込みUI言語は英語と韓国語です。日本語などは`meta/config.strings`で上書きできます。設定は`title`、`subtitle`、`milestone`、`lang`、`people`（`id`、任意の`name`と`role`）、`strings`、`footer`に対応し、状態を変える場合も`todo`と`done`の意味を保ちます。

## デモと開発

[元の対話型デモ](https://claude.ai/artifact/5zENFyGDJbEjey68J6t1bY)と`examples/demo.html`は一時的なメモリ内データを使い、ローカル永続DBは使いません。

```bash
npm install --no-save --no-audit --no-fund jsdom@24.1.1
python3 -m unittest discover -s tests -p 'test_*.py' -v
node tests/smoke.cjs
node tests/local-smoke.cjs
node examples/build-demo.cjs
```

永続化、ロールバック、同時担当取得、worktreeパス、HTTP境界、実サーバーでのUI書き込み・切断・再起動を検証します。CIはパッケージ検出・インストール、JSON、構文、生成デモも確認します。jsdomは開発用で、実行時の外部依存ではありません。

```text
skills/artiboard/SKILL.md            バックエンド選択と手順
skills/artiboard/agents/openai.yaml Codexスキルの表示情報
skills/artiboard/assets/            共通ページとローカルアダプター
skills/artiboard/scripts/           標準ライブラリのサーバー・CLI
skills/artiboard/references/        ローカル・Artifact・プロジェクトルール
plugin.json                        ポータブルAgent Pluginsマニフェスト
.codex-plugin/plugin.json          Codex互換マニフェストと表示情報
.agents/plugins/marketplace.json   Codexリポジトリマーケットプレイス
.claude-plugin/                    Claude Codeプラグインとマーケットプレイス
```

yulmucoffeeの元のartiboardを基に拡張しています。Anthropic・OpenAIとは提携しておらず、両社の推奨を意味しません。[MITライセンス](LICENSE)。
