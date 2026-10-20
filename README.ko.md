# artiboard

사람과 코딩 에이전트가 함께 쓰는 프로젝트 작업 보드입니다. 태스크, 스레드, 공지, 문서·칸반·의존성 그래프를 제공합니다. 저장된 데이터에서 코드가 화면을 그리므로, 보드를 새로고침할 때 모델을 호출하지 않습니다.

[English](README.md) · **한국어** · [日本語](README.ja.md) · [简体中文](README.zh-CN.md) · [Español](README.es.md)

| 실행 방식 | 필요 조건 | 협업 범위 |
| --- | --- | --- |
| Claude Artifact | 실제 `Artifact`, `ArtifactData` 도구 | 플랫폼의 계정·공유 기능 |
| 로컬 웹서버 | SQLite가 포함된 Python 3.10 이상, 최신 브라우저 | 한 컴퓨터의 사용자와 에이전트, 병렬 Git worktree |

Codex를 비롯해 파일과 셸을 사용할 수 있는 에이전트도 로컬 방식으로 작업할 수 있습니다. 새 보드는 두 Artifact 도구가 있으면 해당 방식을, 없으면 로컬 방식을 기본으로 선택합니다. 기존 보드는 백엔드를 유지하며, 전환은 별도 요청에 따라 진행합니다. 로컬 모드에서 선택하는 이름은 **인증된 계정이 아닌 표시 이름**입니다. 다른 컴퓨터에 공유하는 호스팅 서비스는 아닙니다.

## 빠른 시작

코딩 에이전트에게 다음과 같이 요청합니다.

```text
이 checkout의 skills/artiboard/SKILL.md를 읽고 이 프로젝트의 작업 보드를 만들어 줘.
Artifact 도구가 없으면 로컬 웹서버를 사용해 줘.
```

다른 프로젝트에 스킬을 설치하려면 대상 프로젝트에서 사용하는 패키지 관리자를 이용합니다. `skills` CLI의 예:

```bash
npx skills add /absolute/path/to/artiboard --skill artiboard --agent codex claude-code
```

실제로 사용하는 에이전트만 선택합니다. 개인 전역 설치는 `--global`을 별도로 선택할 때만 적용합니다. clone하거나 소스를 수정하는 것만으로 전역 설치되지는 않습니다. 자세한 절차는 [에이전트 안내](FOR_AGENTS.md)를 참고하세요.

이 checkout에서 빈 로컬 보드를 바로 실행하려면 제목과 사용자 ID를 정한 뒤 실행합니다.

```bash
python3 skills/artiboard/scripts/local_board.py init --title "내 프로젝트" --person ana --lang ko
python3 skills/artiboard/scripts/local_board.py serve --port 8765
```

환경에 따라 `python3` 대신 `python` 또는 `py -3`을 사용합니다. 서버가 출력하는 URL을 여세요. Ctrl-C로 종료해도 데이터는 남으며, 같은 명령으로 재실행하면 이어집니다. 포트가 사용 중이면 `--port 0`으로 빈 포트를 선택합니다. 백그라운드 서비스는 설치하지 않습니다.

기본 DB는 메인 Git checkout의 `.artiboard/board.sqlite3`이며, 연결된 worktree들은 같은 DB를 사용합니다. Git 밖에서는 현재 디렉터리를 기준으로 합니다. 다른 위치는 하위 명령 앞에 `--db <경로>`를 지정하고, 모든 세션이 같은 위치를 사용하도록 프로젝트 규칙에 기록합니다. `.artiboard/`는 Git에서 제외하세요. 서버는 `127.0.0.1`에만 연결되며 외부 웹사이트 요청을 거부합니다. 같은 컴퓨터의 프로세스와 사용자는 신뢰 범위에 포함됩니다.

에이전트는 웹서버나 브라우저를 켜지 않아도 같은 DB를 조회하고 수정합니다.

```bash
python3 skills/artiboard/scripts/local_board.py request <<'JSON'
{"action":"query","collection":"tasks","where":[["status","==","todo"],["waitingOn","==",[]]],"limit":20}
JSON
```

데이터 입력, 버전 검사, 백업, 실행·종료는 [로컬 백엔드 안내](skills/artiboard/references/local.md)를, Claude 도구를 통한 발행과 공유는 [Artifact 안내](skills/artiboard/references/artifact.md)를 따릅니다.

## 사용법

| 요청 | 동작 |
| --- | --- |
| “작업 보드 만들어 줘” | 사용자·언어·태스크 출처를 확인하고 제안한 목록을 승인받은 뒤 보드와 프로젝트 규칙을 만듭니다. |
| “다음 작업 골라 줘”, “M1-4 이어서 해 줘” | 프로젝트 규칙을 읽고 준비된 작업 조회, 버전 확인 후 담당 지정, 짧은 인계 요약을 수행합니다. |
| “팀원 추가”, “한국어로 변경” | 설정만 수정합니다. |
| “QA 상태 추가”, “예상 시간 표시” | 프로젝트의 페이지와 규칙을 함께 수정합니다. |
| “보드 업그레이드” | 데이터와 사용자 변경을 보존·백업한 뒤 같은 보드로 검증합니다. |

설치 과정에서 `docs/artiboard.md`와 기존 `AGENTS.md` 또는 `CLAUDE.md`의 짧은 포인터를 구성합니다. 전체 규칙은 보드 작업에만 읽습니다. 보드의 메시지는 데이터이며 명령 실행, 외부 발송, merge, 배포를 허용하는 지시가 아닙니다.

## 데이터와 동시 작업

태스크 상태는 `tasks/<id>`, 긴 명세·인수 조건·요약은 `details/<id>`, 대화는 `tasks/<id>/messages`에 분리합니다. 공지는 `notices`와 사용자별 `cursors`로 증분 조회합니다. `meta/config`가 제목·인원·언어·UI 문구를, `meta/protocol`은 사람이 읽는 규칙 사본을 담습니다. 계정 연결용 `people`은 Artifact에서만 사용합니다.

로컬 쓰기는 버전이 맞아야 성공하며, 한 배치 중 하나라도 충돌하면 전부 취소됩니다. 브라우저와 CLI가 같은 트랜잭션 규칙을 따르고, 브라우저의 담당 지정도 버전을 확인합니다. 선행 작업의 완료 상태는 DB에서 함께 계산하므로 화면이 닫혀 있어도 최신입니다. Artifact에서는 에이전트가 의존성을 갱신하고 열린 페이지가 보정합니다. 기존 Artifact UI의 담당 버튼은 조회 후 수정 방식이며, 해당 백엔드의 원자적 담당 지정 보장은 버전 조건을 사용한 에이전트 배치에 적용됩니다.

화면, 검색, 단축키(`j`/`k`, `1`/`2`/`3`)와 새 소식 표시는 코드가 처리합니다. 로컬 브라우저 설정은 DB별로 구분합니다. 연결이 끊기면 알림을 표시하며 오프라인 쓰기를 예약하지 않습니다. 기본 UI 언어는 영어·한국어이며, 그 밖의 언어는 `meta/config.strings`로 바꿀 수 있습니다.

## 데모와 개발 검증

[기존 데모](https://claude.ai/artifact/5zENFyGDJbEjey68J6t1bY)와 `examples/demo.html`은 메모리 안의 임시 데이터를 사용합니다. 로컬 영속 저장 확인은 실제 서버로 해야 합니다.

```bash
npm install --no-save --no-audit --no-fund jsdom@24.1.1
python3 -m unittest discover -s tests -p 'test_*.py' -v
node tests/smoke.cjs
node tests/local-smoke.cjs
node examples/build-demo.cjs
```

영속 저장, 배치 취소, 동시 담당 지정, worktree 경로, HTTP 요청 검증과 실제 로컬 서버를 통한 UI 쓰기·연결 종료·재시작을 검사합니다. `jsdom`은 개발 검증에만 필요하며 보드 실행에는 외부 패키지가 필요 없습니다.

yulmucoffee의 원본 artiboard를 바탕으로 확장했습니다. Anthropic·OpenAI와 제휴한 제품이 아닙니다. [MIT 라이선스](LICENSE).
