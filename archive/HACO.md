# HACO 정본 구현 계약서

## 0. 작업 명령

너는 지금부터 `haco`를 완성한다.

이 문서는 토론용 제안서가 아니라 구현 계약서다.
계획만 세우고 멈추지 말고, 실제 파일을 만들고, 테스트를 작성하고, 실행해서 통과시킨 뒤 완료 보고하라.

사용자에게 중간 질문하지 마라.
합리적으로 결정 가능한 구현 세부사항은 직접 결정하고 진행하라.

사용자가 최종적으로 원하는 사용 방식은 이것이다.

```text
사용자:
“하코 사용해서 이 작업 해. 완성되면 불러.”

Claude Code 또는 Codex:
1. haco preflight 실행
2. haco 산출물 확인
3. 후보 package를 참고해서 실제 작업
4. 테스트 실행
5. haco postflight 실행
6. 사용자에게 짧게 완료 보고
```

즉 `haco`는 사용자가 직접 만지는 앱이 아니다.
`haco`는 Claude Code / Codex 같은 메인 코딩 에이전트가 자기 작업 전에 호출하는 사용량 절감용 CLI 하네스다.

---

# 1. 프로젝트 이름

프로젝트 이름은 `haco`다.

중간에 하이픈이 들어간 이름은 사용하지 않는다.

```text
프로젝트명: haco
폴더명: haco
Python package: haco
기본 실행: python -m haco
선택 실행: haco
```

`cost-harness`, `cost_harness`, `haco-cli` 같은 이름은 사용하지 않는다.

`HACO`의 의미는 다음으로 둔다.

```text
HACO = Harness for Agent Cost Optimization
```

---

# 2. 목적

`haco`는 Codex Desktop, Claude Code, 기타 코딩 에이전트의 사용량을 줄이기 위한 범용 CLI 하네스다.

핵심 목표는 다음이다.

```text
비싼 메인 코딩 에이전트가 본작업에 들어가기 전에
저렴한 worker 모델이 작업을 분석하고, 컨텍스트를 압축하고, 코드 후보를 생성해서
메인 에이전트가 적은 컨텍스트와 짧은 판단으로 실제 수정과 실행만 하게 만든다.
```

`haco`는 단순 요약기가 아니다.
`haco`는 Gemma 31B급 worker를 junior coder pool로 사용한다.

`haco`는 다음 산출물을 만든다.

```text
1. task_packet.json
   메인 에이전트가 읽을 압축 작업 계약서

2. execution_brief.md
   Claude Code 또는 Codex가 읽고 바로 작업할 실행 브리프

3. candidates/
   Gemma worker가 만든 수정 후보 패키지

4. postflight report
   작업 후 결과를 짧게 정리한 보고서

5. metrics.json / postflight_packet.json
   HACO가 실제로 비용 절감에 도움이 되었는지 판단할 근거
```

---

# 3. 핵심 사용 전제

`haco`의 직접 사용자는 사람이 아니라 Claude Code / Codex다.

잘못된 흐름:

```text
사용자가 haco 실행
사용자가 산출물 확인
사용자가 prompt 복사
사용자가 다시 Claude Code에 전달
```

올바른 흐름:

```text
사용자가 “하코 사용해서 작업해”라고 말함
Claude Code/Codex가 haco preflight 실행
Claude Code/Codex가 task_packet, execution_brief, candidates 확인
Claude Code/Codex가 실제 수정과 테스트 수행
Claude Code/Codex가 haco postflight 실행
Claude Code/Codex가 사용자에게 완료 보고
```

따라서 `haco`는 사람에게 친절한 대시보드가 아니라, 코딩 에이전트가 읽고 실행하기 좋은 구조화 산출물을 만들어야 한다.

---

# 4. 역할 분담

```text
Gemma 31B worker pool:
- 작업 분류
- 컨텍스트 압축
- 관련 파일 후보 추정
- 수정 후보 패키지 생성
- 테스트 후보 생성
- 실패 로그 기반 fix 후보 생성
- 문서/보고 초안 생성
- 후보 자기검토

Claude Code / Codex:
- haco 실행
- 실제 파일 확인
- 후보 검토
- 후보 적용 또는 수정 적용
- 테스트 실행
- 실패 시 최소 수정
- 최종 통합
- postflight 실행
- 최종 보고

haco:
- worker 호출
- 로컬 프로젝트 스캔
- repository map 생성
- JSON 출력 검증
- 후보 산출물 저장
- execution_brief 생성
- 실행 결과 정리
- 사용량 절감 지표 기록
```

Gemma 31B는 단순 평가원이 아니다.
Gemma 31B는 코드 후보를 만드는 junior coder pool이다.

단, Gemma가 만든 후보를 `haco`가 기본 모드에서 대상 프로젝트에 직접 적용하지 않는다.
최종 적용권은 Claude Code 또는 Codex가 가진다.

---

# 5. 만들지 말 것

이번 구현에서 아래 항목은 금지한다.

```text
- MCP 서버
- 웹 UI
- 대시보드
- DB 서버
- 자동 git push
- 대상 프로젝트 파일 자동 수정
- 복잡한 agent 토론 시스템
- 여러 라운드의 agent debate
- 특정 프로젝트 전용 규칙
- 과한 프레임워크
- 불필요한 문서 대량 생성
- unified diff만을 기본 적용 포맷으로 삼는 구조
- 본격적인 벡터 DB / 임베딩 RAG 시스템
```

`haco`는 다음 성격을 유지한다.

```text
CLI first
JSON first
mock first
candidate first
agent-facing first
bounded exploration first
실사용 first
```

---

# 6. 최종 사용 흐름

사용자는 Claude Code 또는 Codex에게 이렇게 말한다.

```text
하코 사용해서 이 작업 해. 완성되면 불러.
```

Claude Code 또는 Codex는 내부적으로 다음을 실행한다.

```bash
python -m haco preflight --project . --task "사용자 작업 내용"
```

사용자의 작업 지시가 길거나 여러 줄이거나 shell argument 길이 제한에 걸릴 가능성이 있으면, Claude Code 또는 Codex는 작업 내용을 파일로 저장한 뒤 `--task-file`을 사용한다.

```bash
python -m haco preflight --project . --task-file .haco/task_input.md
```

그러면 대상 프로젝트 내부에 다음 산출물이 생성된다.

```text
.haco/runs/latest/input.md
.haco/runs/latest/project_snapshot.json
.haco/runs/latest/worker_outputs/*.json
.haco/runs/latest/task_packet.json
.haco/runs/latest/execution_brief.md
.haco/runs/latest/candidates/*
.haco/runs/latest/metrics.json
```

Claude Code 또는 Codex는 다음 파일을 읽고 작업한다.

```text
.haco/runs/latest/task_packet.json
.haco/runs/latest/execution_brief.md
.haco/runs/latest/candidates/
```

작업이 끝나면 Claude Code 또는 Codex는 같은 run 디렉터리에 다음 파일을 남긴다.

```text
.haco/runs/latest/execution_result.md
.haco/runs/latest/diff_summary.md
.haco/runs/latest/test_log.txt
```

테스트를 실행하지 않았다면 다음 파일을 남긴다.

```text
.haco/runs/latest/tests_skipped.md
```

그 후 Claude Code 또는 Codex는 다음을 실행한다.

```bash
python -m haco postflight --run .haco/runs/latest --project .
```

그러면 다음 파일이 생성된다.

```text
.haco/runs/latest/report.md
.haco/runs/latest/postflight_packet.json
```

마지막으로 Claude Code 또는 Codex는 사용자에게 짧게 보고한다.

---

# 7. 필수 CLI 명령

다음 명령은 반드시 구현한다.

```bash
python -m haco init
python -m haco doctor

python -m haco preflight --task "작업 내용"
python -m haco preflight --task-file task.md
python -m haco preflight --project /path/to/project --task "작업 내용"
python -m haco preflight --project /path/to/project --task-file task.md
python -m haco preflight --project /path/to/project --task "작업 내용" --profile quick
python -m haco preflight --project /path/to/project --task "작업 내용" --profile standard
python -m haco preflight --project /path/to/project --task "작업 내용" --profile deep

python -m haco run --task "작업 내용"
python -m haco run --task-file task.md
python -m haco run --project /path/to/project --task "작업 내용"
python -m haco run --project /path/to/project --task-file task.md

python -m haco show .haco/runs/latest
python -m haco postflight --run .haco/runs/latest
python -m haco postflight --run .haco/runs/latest --project /path/to/project
```

가능하면 `pyproject.toml`에 console script도 등록한다.

```bash
haco preflight --project . --task "작업 내용"
```

하지만 필수 성공 기준은 `python -m haco ...`다.

`preflight`와 `run`의 입력 우선순위는 다음으로 한다.

```text
1. --task-file이 있으면 파일 입력을 사용한다.
2. --task가 있으면 문자열 입력을 사용한다.
3. 둘 다 있으면 --task-file을 우선하거나 명확한 에러를 낸다.
   구현자는 한 가지 방식을 정하고 README에 명시한다.
4. 둘 다 없으면 명확한 CLI 에러를 낸다.
```

---

# 8. preflight profile

HACO는 모든 작업에 모든 worker를 무조건 실행하지 않는다.
작업 크기와 위험도에 따라 profile을 사용한다.

기본값은 `standard`다.

```text
quick:
- task_router
- context_compressor
- file_locator
- doc_reporter
- patch/test 후보 생성 안 함

standard:
- task_router
- context_compressor
- file_locator
- patch_candidate
- test_candidate
- doc_reporter
- candidate_judge

deep:
- standard 전체
- patch 후보 복수 생성
- test 후보 복수 생성
- candidate_judge 강화
```

사용 기준:

```text
간단한 문서/상태 작업 → quick
일반 코드 작업 → standard
큰 기능/복잡한 실패 수정 → deep
```

`task_router`가 `docs_only` 또는 `planning`으로 판단하고 risk가 low이면, `standard` profile에서도 patch/test 후보 생성을 생략할 수 있다.

기본 정책:

```text
docs_only + low risk:
- patch_candidate skip
- test_candidate skip 또는 test_scope=skip

planning:
- patch_candidate skip
- test_candidate skip

code_change:
- patch_candidate run
- test_candidate run

test_failure:
- failure_fixer run
- test_candidate run

high risk:
- candidate_judge run
```

---

# 9. run 저장 위치

기본 run 저장 위치는 다음으로 한다.

```text
<target_project>/.haco/runs/
```

예:

```text
myproject/
  .haco/
    runs/
      2026-06-30_200000/
      latest
```

`--project`가 없으면 현재 작업 디렉터리를 대상 프로젝트로 본다.

`latest`는 심볼릭 링크가 가능하면 심볼릭 링크로 만들고, Windows 등에서 어려우면 latest marker 파일로 대체한다.

어느 방식이든 아래 명령이 동작해야 한다.

```bash
python -m haco show .haco/runs/latest
```

---

# 10. 폴더 구조

`haco` 프로젝트 자체는 다음 구조로 구현한다.

```text
haco/
  README.md
  AGENTS.md
  pyproject.toml
  .env.example
  config.example.yaml

  haco/
    __init__.py
    __main__.py
    cli.py
    config.py
    schemas.py
    run_store.py
    scanner.py
    repo_map.py
    model_client.py
    workers.py
    aggregate.py
    preflight.py
    postflight.py
    doctor.py
    brief_builder.py
    candidate_store.py
    metrics.py
    budget.py
    bootstrap.py
    utils.py

  prompts/
    task_router.md
    context_compressor.md
    file_locator.md
    patch_candidate.md
    test_candidate.md
    failure_fixer.md
    doc_reporter.md
    candidate_judge.md

  bootstrap/
    prompts/
      worker_01_contract_review.md
      worker_02_cli_review.md
      worker_03_schema_review.md
      worker_04_scanner_repo_map_review.md
      worker_05_budget_review.md
      worker_06_provider_review.md
      worker_07_candidate_format_review.md
      worker_08_test_plan_review.md
      worker_09_docs_review.md
      worker_10_security_review.md
      worker_11_adversarial_review.md

  tests/
    test_cli.py
    test_schemas.py
    test_scanner.py
    test_repo_map.py
    test_preflight_mock.py
    test_postflight_mock.py
    test_aggregate.py
    test_brief_builder.py
    test_candidate_store.py
    test_run_store.py
    test_budget.py
    test_bootstrap.py
```

---

# 11. 기술 스택

Python으로 구현한다.

필수:

```text
- argparse 또는 typer
- pydantic
- python-dotenv
- pathlib
- json
- datetime
- subprocess
- asyncio
- pytest
- Python 내장 ast
```

선택:

```text
- pyyaml
- google-genai
- aiohttp
- tree-sitter
- tiktoken
```

권장:

```text
- CLI는 typer를 써도 되고 argparse를 써도 된다.
- 외부 API 연동이 불안정하면 mock provider를 먼저 완성한다.
- google provider는 실사용 가능한 골격까지 구현하되, mock mode가 반드시 통과해야 한다.
- Python AST 기반 repo_map은 필수 구현한다.
- tree-sitter 기반 다중 언어 repo_map은 선택 구현이다.
- token counter는 기본 char budget으로 구현하고, tiktoken은 선택 사항으로 둔다.
```

---

# 12. Provider 구조

모델 호출은 provider로 분리한다.

필수 provider:

```text
mock
google
```

`mock`은 API 키 없이 항상 동작해야 한다.
`google`은 Gemini/Gemma 계열 모델을 호출할 수 있게 만든다.

기본 provider는 `mock`이다.

Provider interface:

```python
class ModelProvider:
    def generate_json(self, prompt: str, schema_name: str) -> dict:
        ...
```

비동기 실행을 위해 가능하면 다음 인터페이스도 둔다.

```python
class ModelProvider:
    async def generate_json_async(self, prompt: str, schema_name: str) -> dict:
        ...
```

동기 provider만 있어도 전체 CLI는 동작해야 한다.
비동기 경로는 동기 provider를 wrapper로 감싸도 된다.

MockProvider는 deterministic해야 한다.
같은 입력이면 같은 출력을 내야 한다.

GoogleProvider는 다음을 지원한다.

```text
- GOOGLE_API_KEY
- HACO_GOOGLE_API_KEY
- HACO_PROVIDER=google
- config.yaml의 google.model
```

JSON 응답이 깨졌을 때 전체 실행이 죽으면 안 된다.

처리 순서:

```text
1. JSON parse 시도
2. 실패 시 간단한 JSON repair 시도
3. 그래도 실패 시 worker fallback output 생성
4. 에러 정보를 worker_outputs/<worker>.error.json에 저장
5. preflight 전체는 계속 진행
```

GoogleProvider는 API 호출 실패에 대해 견고해야 한다.

특히 다음 에러는 전체 preflight를 중단시키지 않는다.

```text
- 429 rate limit
- 500/502/503 server error
- timeout
- invalid JSON response
```

처리 규칙:

```text
1. 429 또는 일시적 서버 오류가 발생하면 exponential backoff로 재시도한다.
2. 기본 재시도 횟수는 3회로 한다.
3. backoff는 짧게 시작하고 상한을 둔다.
4. 11개 API key가 설정되어 있으면 다음 key로 회전할 수 있게 구조를 둔다.
5. 모든 재시도가 실패하면 해당 worker만 fallback output을 생성한다.
6. worker 실패 때문에 preflight 전체가 실패하면 안 된다.
7. 실패 정보는 worker_outputs/<worker>.error.json에 기록한다.
```

GoogleProvider 구현 시 실제 sleep/backoff는 테스트가 느려지지 않도록 분리한다.
테스트에서는 backoff sleep을 mock 처리하거나 0초로 설정할 수 있어야 한다.

API key는 절대 repo, logs, reports, worker outputs, error trace에 쓰지 않는다.

허용:

```text
.env
GOOGLE_API_KEY_01=...
GOOGLE_API_KEY_02=...
...
GOOGLE_API_KEY_11=...
```

로그에는 key 값이 아니라 slot 이름만 남긴다.

```json
{
  "provider": "google",
  "key_slot": "GOOGLE_API_KEY_03",
  "key_value_logged": false
}
```

---

# 13. config.example.yaml

```yaml
provider: mock

google:
  model: gemma-4-31b-it
  api_key_env: GOOGLE_API_KEY
  api_key_envs:
    - GOOGLE_API_KEY_01
    - GOOGLE_API_KEY_02
    - GOOGLE_API_KEY_03
    - GOOGLE_API_KEY_04
    - GOOGLE_API_KEY_05
    - GOOGLE_API_KEY_06
    - GOOGLE_API_KEY_07
    - GOOGLE_API_KEY_08
    - GOOGLE_API_KEY_09
    - GOOGLE_API_KEY_10
    - GOOGLE_API_KEY_11

provider_retry:
  max_retries: 3
  initial_backoff_seconds: 1
  max_backoff_seconds: 20
  rotate_keys_on_429: true
  fail_worker_on_exhausted_retries: false

concurrency:
  recommended_concurrency: 4
  max_concurrency: 11
  bootstrap_concurrency: 4

runs_dir: .haco/runs

workers:
  enabled:
    - task_router
    - context_compressor
    - file_locator
    - patch_candidate
    - test_candidate
    - doc_reporter
    - candidate_judge
  conditional:
    - failure_fixer

profiles:
  default: standard
  quick:
    - task_router
    - context_compressor
    - file_locator
    - doc_reporter
  standard:
    - task_router
    - context_compressor
    - file_locator
    - patch_candidate
    - test_candidate
    - doc_reporter
    - candidate_judge
  deep:
    - task_router
    - context_compressor
    - file_locator
    - patch_candidate
    - test_candidate
    - doc_reporter
    - candidate_judge

limits:
  max_worker_output_chars: 6000
  max_reason_chars: 800
  max_candidate_chars: 20000
  max_files_in_snapshot: 300
  max_file_preview_chars: 6000
  fail_on_invalid_json: false

budgets:
  max_project_snapshot_chars: 30000
  max_repo_map_chars: 12000
  max_execution_brief_chars: 16000
  max_task_packet_chars: 12000
  max_candidate_total_chars: 40000
  token_estimation: "char_div_4"

scanner:
  include_tree_depth: 3
  include_git_status: true
  include_recent_files: true
  include_readme_preview: true
  include_repo_map: true
  respect_gitignore: true   # git check-ignore로 무시 파일을 스캔에서 제외(git 없으면 무필터)
  ignore_dirs:
    - .git
    - .haco
    - .venv
    - venv
    - node_modules
    - __pycache__
    - dist
    - build
```

---

# 14. 로컬 프로젝트 스캐너

`file_locator`가 허공에서 파일명을 추정하면 안 된다.

따라서 `preflight`는 worker 호출 전에 대상 프로젝트를 가볍게 스캔한다.

스캔 대상:

```text
- project path
- 파일 트리 상위 N단계
- 전체 파일 경로 목록 일부
- git status
- 최근 수정 파일
- README/AGENTS/CLAUDE/pyproject/package.json 등 주요 파일 존재 여부
- 주요 설정 파일 목록
- 사용자가 준 task에서 추출한 키워드 기반 파일명 후보
- primary language 추정
- project type 추정
- test framework 추정
- repository map
```

출력 파일:

```text
.haco/runs/latest/project_snapshot.json
```

스냅샷은 너무 길면 안 된다.
큰 파일 내용을 통째로 넣지 않는다.

`project_snapshot.json` 예시:

```json
{
  "project_path": "/path/to/project",
  "primary_language": "python | javascript | typescript | rust | go | unknown",
  "project_type": "python_package | node_package | rust_crate | go_module | generic | unknown",
  "test_frameworks": ["pytest"],
  "package_files": ["pyproject.toml", "package.json"],
  "tree_preview": [],
  "file_paths_sample": [],
  "git_status": "",
  "recent_files": [],
  "important_files": [],
  "keyword_file_matches": [],
  "search_hints": [],
  "repo_map": [],
  "repo_map_status": "ok | partial | skipped",
  "repo_map_notes": [],
  "truncation_applied": false,
  "truncation_notes": [],
  "notes": []
}
```

언어 감지 규칙은 단순하고 결정적으로 구현한다.

```text
pyproject.toml / setup.py / requirements.txt / *.py 다수 → python
package.json / *.js 다수 → javascript
package.json / tsconfig.json / *.ts 다수 → typescript
Cargo.toml / *.rs 다수 → rust
go.mod / *.go 다수 → go
```

테스트 프레임워크 감지 예시:

```text
pytest.ini / pyproject.toml에 pytest 설정 / tests/test_*.py → pytest
package.json scripts.test → npm test
vitest.config.* → vitest
jest.config.* → jest
Cargo.toml → cargo test
go test 패턴 → go test
```

`test_candidate` worker는 테스트 후보 파일 확장자와 테스트 명령을 추측하지 말고, 가능한 경우 `project_snapshot.primary_language`와 `project_snapshot.test_frameworks`를 기준으로 생성한다.

언어를 확신할 수 없으면 `unknown`으로 기록하고, 테스트 코드를 억지로 만들지 말고 `candidates/candidate_xx/test_candidate.md`에 테스트 전략을 쓴다.

---

# 15. Repository Map

`scanner.py`는 단순 파일 트리만 만들지 않는다.
가능한 경우 repository map을 생성한다.

목표는 전체 파일 내용을 읽는 것이 아니라, 프로젝트의 구조적 뼈대를 작게 요약하는 것이다.

필수 구현:

```text
- Python 파일은 내장 ast 모듈로 class/function/import/docstring/signature 후보를 추출한다.
- 추출 결과는 project_snapshot.json의 repo_map 필드에 저장한다.
- repo_map은 너무 길면 구조 보존 trimming으로 줄인다.
- Python 외 언어는 처음에는 best-effort 파일명/path 기반 symbol hint만 제공해도 된다.
```

Python 외 언어 best-effort symbol hint:

```text
JavaScript/TypeScript:
- package.json, tsconfig.json 탐지
- export function / export class / function / class 정규식 hint

Rust:
- Cargo.toml 탐지
- pub fn / fn / pub struct / struct / enum / mod 정규식 hint

Go:
- go.mod 탐지
- func / type / struct 정규식 hint
```

선택 구현:

```text
- tree-sitter가 설치되어 있으면 JavaScript/TypeScript/Rust/Go 등도 symbol map을 만든다.
- tree-sitter가 없으면 실패하지 말고 fallback한다.
```

`repo_map` 항목 예시:

```json
{
  "file": "src/example.py",
  "symbols": [
    {
      "kind": "function",
      "name": "run_task",
      "signature": "run_task(task: str) -> dict",
      "docstring_preview": "Runs one task..."
    }
  ]
}
```

규칙:

```text
- repo_map은 코드 전문을 담지 않는다.
- 함수/클래스 이름, signature, import, 짧은 docstring preview만 담는다.
- repo_map 생성 실패는 preflight 전체 실패가 아니다.
- repo_map이 없으면 file_locator confidence를 보수적으로 낮출 수 있다.
- 임베딩이나 본격 RAG는 이번 구현 범위에 넣지 않는다.
- 추후 확장을 위해 scanner 출력에 search_hints 필드를 둔다.
```

---

# 16. Token / Size Circuit Breaker

HACO는 사용량 절감 도구이므로, 자기 자신이 거대한 context를 만들면 안 된다.

기본 token 추정은 다음으로 한다.

```text
estimated_tokens = chars / 4
```

`tiktoken` 등 외부 token counter는 선택 사항이다.

`budget.py`를 구현해서 다음을 담당하게 한다.

```text
- char budget 계산
- token estimate 계산
- snapshot 크기 제한
- repo_map 크기 제한
- execution_brief 크기 제한
- task_packet 크기 제한
- candidate 전체 크기 제한
```

## 16.1 Structural Budget Trimming

budget trimming은 문자열을 임의 위치에서 자르지 않는다.

금지:

```text
- JSON 문자열을 단순 substring으로 자르기
- AST/repo_map JSON을 중간에서 잘라 파서 불가능한 파일 만들기
- markdown code fence를 중간에서 잘라 깨진 문서 만들기
```

허용:

```text
- list 항목 개수 줄이기
- repo_map 파일 항목 줄이기
- symbols 배열의 뒤쪽 항목 제거
- docstring_preview 길이 줄이기
- tree_preview depth 줄이기
- file_paths_sample 개수 줄이기
- keyword_file_matches 상위 N개만 유지
```

trimming 규칙:

```text
1. 객체를 먼저 정렬한다.
2. 중요도 낮은 list item부터 제거한다.
3. 문자열 필드는 필드 내부에서만 안전하게 축약한다.
4. JSON serialization이 성공하는지 확인한다.
5. 실패하면 더 작은 fallback snapshot을 만든다.
```

fallback snapshot 예시:

```json
{
  "project_path": "/path/to/project",
  "primary_language": "unknown",
  "project_type": "unknown",
  "test_frameworks": [],
  "important_files": [],
  "keyword_file_matches": [],
  "repo_map": [],
  "repo_map_status": "skipped",
  "truncation_applied": true,
  "truncation_notes": [
    "Fallback minimal snapshot used because budget trimming failed."
  ]
}
```

모든 budget trimming 결과는 다음 검증을 통과해야 한다.

```text
- valid JSON
- required fields 존재
- task_packet 생성 가능
- execution_brief 생성 가능
```

---

# 17. Worker Sequencing / Concurrency

HACO는 모든 worker를 무조건 순차 실행하지 않는다.

하지만 patch와 test 후보는 무조건 병렬 실행하지 않는다.
테스트 후보는 패치 후보의 내용을 알아야 더 유용할 수 있으므로 작업 목적에 따라 순서를 조절한다.

실행 순서:

```text
Stage 0:
- scanner
- repo_map
- budget trimming

Stage 1, sequential:
- task_router
- context_compressor
- file_locator

Stage 1.5, conditional:
- file_locator low confidence이면 focused rescan

Stage 2, conditional:
- docs_only/planning: patch/test skip
- code_change/refactor: patch_candidate 먼저, 그 후 test_candidate
- test_failure: failure_fixer 또는 재현 테스트 우선, 그 후 test_candidate
- deep: patch 후보 복수 병렬 생성 가능, judge 후 test_candidate 생성

Stage 3, sequential:
- candidate_judge
- hard filtering
- aggregate
- brief_builder
```

구현 규칙:

```text
- Python asyncio를 사용할 수 있다.
- 동기 provider만 있어도 동작해야 한다.
- mock provider에서도 concurrency 경로가 테스트 가능해야 한다.
- worker별 실행 시간은 metrics.json에 기록한다.
- worker 병렬화 때문에 출력 순서가 불안정해져도 결과 파일명은 결정적이어야 한다.
- Stage 1 core worker가 실패하면 Stage 2 후보 생성은 억제한다.
```

`metrics.json`에는 다음 필드를 포함한다.

```json
{
  "worker_timings": {
    "task_router": 0.4,
    "context_compressor": 0.6,
    "file_locator": 0.5,
    "patch_candidate": 2.4,
    "test_candidate": 1.8
  },
  "preflight_wall_time_seconds": 3.2
}
```

---

# 18. File Locator 2-pass Focused Rescan

`file_locator`는 HACO 파이프라인의 단일 장애점이 될 수 있다.

첫 번째 locator 결과가 낮은 신뢰도일 때 바로 포기하지 말고, 한 번 더 focused rescan을 수행한다.

조건:

```text
file_locator confidence=low
또는 files_to_read가 비어 있음
또는 files_to_edit가 비어 있으나 task_type이 code_change/test_failure/refactor임
```

이 경우 HACO는 다음을 수행한다.

```text
1. file_locator가 반환한 search_keywords를 사용한다.
2. scanner가 수집한 file_paths_sample, repo_map, keyword_file_matches를 다시 검색한다.
3. 파일명, path, symbol name, docstring preview를 대상으로 focused match를 수행한다.
4. top N 후보만 다시 file_locator에게 전달한다.
5. 2-pass 결과도 low confidence이면 haco_status=skip_to_main_agent로 전환한다.
```

`task_packet.json`에는 다음 필드를 포함한다.

```json
{
  "locator_passes": 2,
  "locator_rescan_applied": true,
  "locator_rescan_notes": [
    "First pass had low confidence; retried with search_keywords against repo_map and file_paths_sample."
  ]
}
```

2-pass rescan은 full repository scan이 아니다.
검색 범위는 HACO가 이미 수집한 snapshot, repo_map, file path sample, keyword matches 안에서 제한한다.

---

# 19. Worker 구성

필수 worker는 다음 8개다.

```text
1. task_router
2. context_compressor
3. file_locator
4. patch_candidate
5. test_candidate
6. failure_fixer
7. doc_reporter
8. candidate_judge
```

단, `failure_fixer`는 실패 로그가 있을 때만 실행한다.

## 19.1 task_router

작업 종류, 위험도, 사용자 결정 필요 여부를 판단한다.

출력:

```json
{
  "worker": "task_router",
  "task_type": "docs_only | code_change | test_failure | refactor | planning | research | unknown",
  "user_decision_needed": false,
  "risk": "low | medium | high",
  "recommended_mode": "preflight_only | candidate_generation | failure_fix | postflight_only | test_first",
  "reason": ""
}
```

사용자 결정이 필요한 경우는 제한한다.

사용자에게 물어야 하는 경우:

```text
- 목표 자체 변경
- 대규모 범위 변경
- 파괴적 롤백
- 큰 비용/시간 증가
- 제공 정보가 완전히 부족해서 합리적 가정 불가
```

사소한 파일명, 테스트 선택, 문서 생성 여부는 사용자에게 묻지 않는다.

## 19.2 context_compressor

사용자 요청과 project snapshot을 실행 가능한 짧은 컨텍스트로 압축한다.

출력:

```json
{
  "worker": "context_compressor",
  "compressed_context": "",
  "known_constraints": [],
  "assumptions": [],
  "open_questions": []
}
```

주의:

```text
- open_questions가 있다고 무조건 user_decision_needed=true로 만들지 않는다.
- 사소한 질문은 assumptions로 바꾼다.
- compressed_context는 execution_brief에 들어갈 수 있게 짧게 쓴다.
```

## 19.3 file_locator

관련 파일 후보를 추정한다.

입력에는 반드시 `project_snapshot.json`을 포함한다.

출력:

```json
{
  "worker": "file_locator",
  "files_to_read": [],
  "files_to_edit": [],
  "search_keywords": [],
  "confidence": "low | medium | high",
  "reason": ""
}
```

주의:

```text
- project_snapshot에 없는 파일을 확정적으로 말하지 않는다.
- 모르면 search_keywords를 제안한다.
- files_to_edit는 보수적으로 제안한다.
- repo_map과 keyword_file_matches를 우선 참고한다.
```

## 19.4 patch_candidate

Gemma를 단순 평가자가 아니라 junior coder로 사용한다.

`patch_candidate`는 실제 수정 후보 패키지를 만든다.

중요: `.diff`를 기본 적용 포맷으로 삼지 않는다.
LLM이 생성한 unified diff는 줄 번호, 주변 문맥, 들여쓰기, 파일 상태 차이 때문에 깨질 수 있다.
따라서 `.diff`는 optional artifact로만 사용한다.

기본 후보 단위는 candidate directory다.

```text
.haco/runs/latest/candidates/
  candidate_01/
    candidate.json
    edit_plan.md
    search_replace.json
    replacement_blocks.md
    optional.diff
```

출력 JSON:

```json
{
  "worker": "patch_candidate",
  "candidate_id": "candidate_01",
  "candidate_dir": "candidates/candidate_01",
  "preferred_apply_method": "full_block | search_replace | insert_after_anchor | strategy_only | diff_optional",
  "summary": "",
  "risk": "low | medium | high",
  "assumptions": [],
  "reason": ""
}
```

주의:

```text
- 대상 프로젝트 파일에 직접 적용하지 않는다.
- 파일 내용이 부족하면 적용 불가능한 후보를 억지로 만들지 않는다.
- 파일 경로와 수정 위치가 불확실하면 strategy_only 후보를 만든다.
- .diff는 선택 산출물이며 기본 산출물이 아니다.
```

## 19.5 test_candidate

테스트 후보를 만든다.

출력 JSON:

```json
{
  "worker": "test_candidate",
  "test_scope": "skip | smoke | focused | full | long_run | unknown",
  "tests_to_run": [],
  "test_candidate_paths": [],
  "reason": ""
}
```

테스트 코드 후보가 있으면 candidate directory 안에 저장한다.

예:

```text
.haco/runs/latest/candidates/candidate_02/test_candidate_01.py
.haco/runs/latest/candidates/candidate_02/test_candidate_01.js
.haco/runs/latest/candidates/candidate_02/test_candidate.md
```

언어가 `unknown`이면 테스트 코드를 억지로 만들지 않고 `test_candidate.md`에 테스트 전략을 쓴다.

## 19.6 failure_fixer

실패 로그가 있을 때만 실행한다.

입력 후보:

```text
test_log.txt
execution_result.md
diff_summary.md
```

출력:

```json
{
  "worker": "failure_fixer",
  "fix_candidate_id": "candidate_fix_01",
  "likely_cause": "",
  "candidate_dir": "candidates/candidate_fix_01",
  "tests_to_rerun": [],
  "reason": ""
}
```

fix 후보도 candidate directory 구조를 사용한다.

## 19.7 doc_reporter

문서 생성/수정 필요 여부와 보고 초안을 만든다.

출력:

```json
{
  "worker": "doc_reporter",
  "new_doc_needed": false,
  "docs_to_update": [],
  "docs_to_avoid": [],
  "report_draft": "",
  "reason": ""
}
```

기본값은 `new_doc_needed=false`다.
문서 생성은 기본적으로 억제한다.

## 19.8 candidate_judge

생성된 후보들을 평가하고 hard filtering을 수행한다.

출력:

```json
{
  "worker": "candidate_judge",
  "accepted_candidates": [],
  "masked_candidates": [],
  "rejected_candidates": [],
  "best_candidate": "",
  "warnings": [],
  "reason": ""
}
```

평가 기준:

```text
- 적용 가능성
- 범위 과대 여부
- 파일 경로 신뢰도
- 테스트 가능성
- 사용자 요청과의 정합성
- 불필요한 문서 생성 여부
- 메인 에이전트에게 읽힐 가치가 있는지
```

`candidate_judge`는 후보를 “정답”으로 판정하지 않는다.
역할은 위험 후보를 걸러내고, 메인 코딩 에이전트가 먼저 볼 후보의 우선순위를 정하는 것이다.

---

# 20. candidate directory 포맷

각 후보는 directory 단위로 저장한다.

```text
.haco/runs/latest/candidates/candidate_01/
  candidate.json
  edit_plan.md
  search_replace.json
  replacement_blocks.md
  optional.diff
```

## 20.1 candidate.json

```json
{
  "candidate_id": "candidate_01",
  "kind": "patch | test | fix | doc | strategy",
  "target_files": [],
  "language": "python | javascript | typescript | rust | go | unknown",
  "confidence": "low | medium | high",
  "requires_human_or_agent_review": true,
  "direct_apply_recommended": false,
  "preferred_apply_method": "full_block | search_replace | insert_after_anchor | strategy_only | diff_optional",
  "judge_status": "accepted | masked | rejected",
  "judge_reason": "",
  "expose_in_execution_brief": true,
  "summary": "",
  "risk": "low | medium | high",
  "reason": ""
}
```

기본값:

```text
requires_human_or_agent_review = true
direct_apply_recommended = false
expose_in_execution_brief = false until candidate_judge accepts it
```

HACO는 후보를 직접 적용하지 않는다.
Claude Code/Codex가 후보를 검토한 뒤 적용하거나 수정해서 적용한다.

## 20.2 edit_plan.md

`edit_plan.md`는 메인 코딩 에이전트가 읽는 짧은 수정 계획이다.

포함할 내용:

```text
- 목표
- 수정 대상 파일
- 수정 대상 함수/클래스/섹션
- 변경 이유
- 적용 순서
- 주의할 점
- 추천 테스트
```

`edit_plan.md`는 장황하면 안 된다.
메인 에이전트가 바로 실행할 수 있는 수준으로 짧고 구체적으로 쓴다.

## 20.3 search_replace.json

`search_replace.json`은 정확한 search/replace 후보를 담는다.

```json
{
  "edits": [
    {
      "file": "path/to/file.py",
      "operation": "replace | insert_after_anchor | insert_before_anchor",
      "search": "exact old block or anchor",
      "replace": "new block",
      "notes": "why this change is needed"
    }
  ]
}
```

규칙:

```text
- search는 실제 파일에서 찾을 수 있을 가능성이 높은 짧은 블록이어야 한다.
- 너무 긴 search 블록을 만들지 않는다.
- 줄 번호에 의존하지 않는다.
- 파일 내용이 충분하지 않으면 search_replace를 억지로 만들지 않는다.
```

## 20.4 replacement_blocks.md

`replacement_blocks.md`는 전체 함수, 전체 클래스, 또는 독립 블록 교체 후보를 담는다.

형식:

````md
## Replacement 1

File: path/to/file.py  
Target: function_name or class_name  
Apply method: replace entire function

```python
def function_name(...):
    ...
```
````

규칙:

```text
- 가능하면 전체 함수 단위로 제안한다.
- 부분 줄 수정보다 함수/클래스 단위 교체를 우선한다.
- target function/class를 모르면 strategy_only로 낮춘다.
- 실제 파일 경로가 불확실하면 적용 후보가 아니라 전략 후보로 저장한다.
```

## 20.5 optional.diff

`.diff`는 optional이다.

Gemma worker가 unified diff를 만들 수 있으면 `optional.diff`로 저장할 수 있다.
단, HACO는 `.diff`를 기본 적용 포맷으로 간주하지 않는다.

규칙:

```text
- diff는 있으면 참고 자료로만 사용한다.
- diff가 파싱 불가능해도 candidate 전체를 실패로 보지 않는다.
- candidate_judge는 diff보다 edit_plan/search_replace/replacement_blocks를 우선 평가한다.
- execution_brief는 메인 에이전트에게 diff를 맹목적으로 적용하지 말라고 지시한다.
```

---

# 21. Candidate Hard Filtering

HACO는 무의미한 후보를 모두 메인 에이전트에게 넘기지 않는다.
candidate_judge는 단순 평가자가 아니라 hard filter 역할도 한다.

후보 상태:

```text
accepted:
- 메인 에이전트가 우선 검토할 후보

masked:
- 디스크에는 보관하지만 execution_brief에는 노출하지 않는 후보
- 참고용으로만 남김

rejected:
- 품질이 너무 낮아 메인 에이전트에게 보여주지 않을 후보
- rejected/ 폴더로 이동하거나 execution_brief에서 완전히 제외
```

hard filtering 기준:

```text
- target_files가 비어 있고 strategy_only도 아닌 후보
- 파일 경로가 snapshot/repo_map에 전혀 없는 후보
- search_replace의 search block이 너무 길거나 모호한 후보
- replacement_blocks가 target function/class를 전혀 지정하지 못한 후보
- optional.diff만 있고 edit_plan/search_replace/replacement_blocks가 없는 후보
- candidate confidence=low 이고 risk=high인 후보
- 사용자 요청과 직접 관련이 낮은 후보
```

execution_brief에는 기본적으로 `accepted` 후보만 노출한다.
`masked` 후보는 “additional candidates exist but were masked by HACO” 정도로만 표시한다.
`rejected` 후보는 execution_brief에 표시하지 않는다.

목표:

```text
Gemma 후보가 많아져서 Claude/Codex가 오답 검토에 토큰을 낭비하는 상황을 막는다.
```

---

# 22. core worker 실패 시 중단 규칙

Fallback은 모든 worker에 동일하게 적용하지 않는다.

핵심 worker가 실패하면 무의미한 후보 생성을 계속하지 않는다.

핵심 worker:

```text
- task_router
- context_compressor
- file_locator
```

중단 조건:

```text
- task_router 실패
- context_compressor 실패
- file_locator 실패
- 2-pass 후에도 file_locator confidence=low 이면서 files_to_read가 비어 있음
- project_snapshot 생성 실패
```

이 경우 HACO는 patch/test 후보 생성을 억지로 진행하지 않고 다음 상태를 만든다.

```json
{
  "haco_status": "skip_to_main_agent",
  "reason": "Core preflight context was insufficient.",
  "recommended_action": "Main coding agent should proceed directly with normal bounded exploration."
}
```

그리고 `execution_brief.md`에는 다음을 명시한다.

```text
HACO could not prepare reliable candidates.
Do not rely on candidates.
Proceed with normal bounded exploration.
```

목표는 garbage-in garbage-out을 막는 것이다.

---

# 23. skip_to_main_agent 원인 기록

`haco_status=skip_to_main_agent`는 실패가 아니라 안전한 후퇴다.
다만 원인을 반드시 기록해야 한다.

`task_packet.json`과 `postflight_packet.json`에 다음 필드를 포함한다.

```json
{
  "skip_reason": "locator_failed | context_too_small | repo_map_missing | task_too_ambiguous | candidate_quality_low | provider_failure | unknown",
  "suggested_haco_improvement": ""
}
```

예시:

```json
{
  "skip_reason": "locator_failed",
  "suggested_haco_improvement": "Improve repo_map or search_hints for this project type."
}
```

목표:

```text
- HACO가 왜 후퇴했는지 추적한다.
- 반복 skip 원인을 통해 HACO 자체를 개선할 수 있게 한다.
```

---

# 24. task_packet.json 스키마

`preflight`는 최종적으로 다음 스키마의 `task_packet.json`을 생성한다.

```json
{
  "run_id": "",
  "project_path": "",
  "haco_status": "ready | skip_to_main_agent",
  "skip_reason": "",
  "suggested_haco_improvement": "",
  "locator_passes": 1,
  "locator_rescan_applied": false,
  "locator_rescan_notes": [],
  "task_type": "code_change",
  "user_decision_needed": false,
  "risk": "medium",
  "recommended_mode": "candidate_generation",
  "compressed_context": "",
  "files_to_read": [],
  "files_to_edit": [],
  "search_keywords": [],
  "tests_to_run": [],
  "test_scope": "focused",
  "long_run_needed": false,
  "docs_to_update": [],
  "new_doc_needed": false,
  "candidate_summary": {
    "generated": 0,
    "accepted": 0,
    "masked": 0,
    "rejected": 0,
    "patch_candidates": [],
    "test_candidates": [],
    "fix_candidates": [],
    "best_candidate": "",
    "warnings": []
  },
  "prior_change_reference": "",
  "constraints": [],
  "assumptions": [],
  "recommended_action": "",
  "reason": "",
  "worker_outputs": {
    "task_router": "worker_outputs/task_router.json",
    "context_compressor": "worker_outputs/context_compressor.json",
    "file_locator": "worker_outputs/file_locator.json",
    "patch_candidate": "worker_outputs/patch_candidate.json",
    "test_candidate": "worker_outputs/test_candidate.json",
    "doc_reporter": "worker_outputs/doc_reporter.json",
    "candidate_judge": "worker_outputs/candidate_judge.json"
  }
}
```

---

# 25. aggregate 규칙

`aggregate.py`는 worker 결과를 합쳐 `task_packet.json`을 만든다.

규칙:

```text
- risk는 가장 높은 값을 선택한다.
- user_decision_needed는 task_router 판단을 우선한다.
- open_questions만 있다고 user_decision_needed=true로 만들지 않는다.
- new_doc_needed는 doc_reporter 결과를 따른다.
- test_scope와 tests_to_run은 test_candidate 결과를 따른다.
- files_to_read/files_to_edit는 file_locator 결과를 따른다.
- candidate_summary는 candidates/와 candidate_judge 결과를 반영한다.
- prior_change_reference는 code_change/refactor/test_failure 작업에서 files_to_edit[0]을 마지막으로
  바꾼 커밋 diff를 `prior_change_reference.md`로 쓰고 그 rel 경로를 담는다(반복 증분 템플릿). git/이력이
  없거나 편집 대상이 없으면 빈 문자열. git 기반·결정론·provider 비의존.
- recommended_action은 짧게 쓴다.
- reason은 최대 5문장으로 압축한다.
- core worker가 실패하면 haco_status=skip_to_main_agent로 설정한다.
- core worker 실패 시 patch/test 후보 생성을 억지로 진행하지 않는다.
- non-core worker 하나가 실패해도 전체 preflight는 실패하지 않는다.
- 실패한 non-core worker는 fallback output을 넣고 계속 진행한다.
```

---

# 26. execution_brief.md 생성

`preflight`는 Claude Code 또는 Codex가 직접 읽을 `execution_brief.md`를 생성한다.

이 파일은 사용자용 안내가 아니다.
이 파일은 메인 코딩 에이전트가 실제 작업 전에 읽는 실행 브리프다.

형식:

````md
# HACO Execution Brief

You are the main coding agent.

HACO has prepared a task packet and candidate files to reduce your exploration cost.

## Mandatory first step

Before editing files, validate HACO outputs.

Record the result in `execution_result.md` under a section named `HACO Validation`.

You must check:

- Did you read `task_packet.json`?
- Did you inspect accepted candidates?
- Are the suggested files plausible?
- Are the candidates usable, partially usable, or unusable?
- If you perform broader exploration, why was it necessary?

Use this format:

```text
## HACO Validation

task_packet_read: yes/no
accepted_candidates_checked: yes/no
candidate_usefulness: usable | partially_usable | unusable | none
bounded_exploration_needed: yes/no
reason:
```

## Required behavior

- Read `task_packet.json` first.
- Read the suggested files first.
- Check accepted candidates before writing a patch from scratch.
- If a candidate is usable, apply or adapt it.
- If a candidate is wrong, do not blindly follow it.
- Do not treat `optional.diff` as the primary source of truth.
- Prefer `edit_plan.md`, `search_replace.json`, and `replacement_blocks.md` over raw diff.
- Do not create new documents unless `new_doc_needed=true`.
- Use the recommended test scope.
- Do not ask the user if `user_decision_needed=false`.
- Keep edits minimal.
- Avoid broad refactors unless the task requires them.
- After execution, write `execution_result.md`.
- Write `diff_summary.md`.
- If tests ran, write `test_log.txt`.
- If tests were skipped, write `tests_skipped.md`.
- Then run `python -m haco postflight --run <this_run_dir> --project <project_path>`.
- Keep final report short.

## Bounded exploration rule

Use HACO outputs first.
Do not perform broad exploration before checking task_packet and accepted candidates.

If HACO candidates are missing, low confidence, or clearly wrong, perform bounded exploration:
- start from files_to_read and search_keywords
- use focused search
- avoid full repository scans unless necessary
- explain briefly why broader exploration was needed

## Task packet

<task_packet 요약 또는 JSON>

## Accepted candidate files

<accepted 후보 파일 목록>

## Masked candidates

<masked 후보 수만 표시>

## Output files required after execution

- execution_result.md
- diff_summary.md
- test_log.txt or tests_skipped.md
````

이 파일이 매우 중요하다.

Claude Code/Codex가 `haco` 결과를 무시하고 전체 repo를 넓게 탐색하면 사용량 절감 효과가 사라진다.
하지만 “탐색 금지”처럼 시스템 프롬프트와 충돌하는 지시를 쓰지 말고, mandatory first-step validation과 bounded exploration을 요구한다.

---

# 27. metrics.json

`metrics.json`을 생성한다.

```json
{
  "input_chars": 0,
  "project_snapshot_chars": 0,
  "repo_map_chars": 0,
  "worker_output_chars": 0,
  "task_packet_chars": 0,
  "execution_brief_chars": 0,
  "candidate_chars": 0,
  "worker_count": 0,
  "provider": "mock",
  "haco_status": "ready | skip_to_main_agent",
  "skip_reason": "",
  "locator_passes": 1,
  "locator_rescan_applied": false,
  "candidate_counts": {
    "generated": 0,
    "accepted": 0,
    "masked": 0,
    "rejected": 0
  },
  "candidate_usefulness": "unknown",
  "bounded_exploration_needed": false,
  "execution_validation_expected": true,
  "worker_timings": {
    "task_router": 0.0,
    "context_compressor": 0.0
  },
  "preflight_wall_time_seconds": 0.0,
  "compression_notes": []
}
```

목적:

```text
- worker 출력이 너무 길어지는지 확인
- execution_brief가 비대해지는지 확인
- repo_map이 너무 커지는지 확인
- 후보가 너무 많이 생성되는지 확인
- HACO 자체가 문서 생성 병목이 되는지 확인
- worker별 latency를 확인
- HACO가 실제로 유용했는지 누적 판단할 근거를 남김
```

---

# 28. postflight 동작

명령:

```bash
python -m haco postflight --run .haco/runs/latest --project .
```

입력으로 다음 파일이 있으면 읽는다.

```text
task_packet.json
execution_result.md
test_log.txt
tests_skipped.md
diff_summary.md
```

출력:

```text
report.md
postflight_packet.json
```

`report.md` 형식:

```md
# HACO Report

- Task type:
- Changed:
- Tests:
- Result:
- Risk:
- Candidate usefulness:
- Bounded exploration:
- HACO validation recorded:
- Next action:
```

`postflight`는 `execution_result.md`의 `HACO Validation` 섹션을 읽어 다음을 `postflight_packet.json`에 기록한다.

```json
{
  "haco_validation": {
    "task_packet_read": true,
    "accepted_candidates_checked": true,
    "candidate_usefulness": "usable | partially_usable | unusable | none",
    "bounded_exploration_needed": true,
    "reason": ""
  },
  "haco_effectiveness": {
    "main_agent_used_haco": true,
    "skip_to_main_agent": false,
    "notes": ""
  },
  "main_agent_did_not_record_haco_validation": false
}
```

`execution_result.md`에 `HACO Validation` 섹션이 없으면 postflight는 실패하지 않되 warning을 남긴다.

```json
{
  "main_agent_did_not_record_haco_validation": true
}
```

`postflight`는 실패 로그가 있으면 `failure_fixer`를 실행해 fix 후보를 생성할 수 있어야 한다.

단, fix 후보도 직접 적용하지 않는다.

테스트 결과 판정(`_detect_test_outcome`)은 다음 우선순위를 따른다. (1) pytest `N failed`/`N error(s)`
카운트(합 0이면 통과), (2) pytest를 안 쓰는 자체 verifier의 `status PASS/FAIL` 라인(여러 줄이면 전부
pass라야 통과), (3) 강한 실패 마커(`failed`/`traceback`/`assertionerror`) 또는 통과 마커(`passed`/`ok`).
판정 불가면 `tests_passed=null`(미상)이며, report의 Tests 표기는 not run/unknown/passed/failed로 구분한다
(미상을 failed로 적지 않는다).

---

# 29. run 명령

명령:

```bash
python -m haco run --project . --task "작업 내용"
python -m haco run --project . --task-file task.md
```

동작:

```text
1. preflight 실행
2. task_packet 경로 출력
3. execution_brief 경로 출력
4. candidates 경로 출력
5. “메인 코딩 에이전트는 execution_brief.md를 읽고 작업하라”고 출력
```

`run`은 대상 프로젝트를 직접 수정하지 않는다.

---

# 30. doctor 명령

명령:

```bash
python -m haco doctor
```

확인할 것:

```text
- Python version
- package import 가능 여부
- config 로드 가능 여부
- .haco/runs directory 쓰기 가능 여부
- mock provider 동작 여부
- google provider 설정 여부
- prompts 존재 여부
- pydantic schema validation 동작 여부
- repo_map 생성 경로 동작 여부
- budget trimming 동작 여부
- bootstrap prompt 존재 여부
```

---

# 31. show 명령

명령:

```bash
python -m haco show .haco/runs/latest
```

출력:

```text
- input 요약
- task_packet 요약
- worker 결과 목록
- candidates 목록
- accepted/masked/rejected 후보 수
- repo_map 상태
- metrics 요약
- HACO effectiveness 요약
- report 존재 여부
```

---

# 32. HACO 제작용 Gemma 11-key bootstrap

HACO가 완성되기 전에는 HACO를 사용할 수 없다.
따라서 HACO 제작 자체에는 임시 bootstrap worker pool을 사용할 수 있다.

이 bootstrap은 HACO 본체의 핵심 기능이 아니라, HACO를 만들기 위한 임시 발판이다.

목적:

```text
- Claude Code의 설계 검토 토큰을 줄인다.
- Gemma 11개 독립 key를 병렬 검토자/후보 생성자로 활용한다.
- Claude Code는 구현자/통합자/테스트 실행자로 남는다.
```

금지:

```text
- bootstrap worker가 직접 repo 파일 수정
- bootstrap worker가 git commit/push 수행
- bootstrap 결과를 무조건 반영
- API key를 파일, 로그, 리포트에 기록
```

허용:

```text
- 설계 검토
- 모순 지적
- 테스트 후보 생성
- 위험 분석
- README/AGENTS.md 초안 검토
- 구현 순서 검토
- 보안/API key/logging 검토
```

## 32.1 Bootstrap worker 역할

```text
Gemma worker 01: 전체 계약서 모순 검토
Gemma worker 02: CLI 명령/UX 검토
Gemma worker 03: schema/config 설계 검토
Gemma worker 04: scanner/repo_map 설계 검토
Gemma worker 05: budget/structural trimming 검토
Gemma worker 06: provider/retry/JSON fallback 검토
Gemma worker 07: candidate package 포맷 검토
Gemma worker 08: test plan 생성
Gemma worker 09: README/AGENTS.md 초안 검토
Gemma worker 10: 보안/API key/logging 검토
Gemma worker 11: 반대자 역할, 과설계/낭비 지적
```

## 32.2 Bootstrap 산출물

```text
.haco_bootstrap/
  input_contract.md
  worker_outputs/
    worker_01.json
    worker_02.json
    ...
    worker_11.json
  aggregate.md
```

또는 HACO 프로젝트 내부에서는:

```text
bootstrap/outputs/
  worker_01.json
  worker_02.json
  ...
  aggregate.md
```

## 32.3 Bootstrap 실행 규칙

```text
1. 정본 계약서를 각 worker prompt에 넣는다.
2. 각 Gemma key로 독립 검토를 돌린다.
3. 각 worker는 JSON 또는 markdown으로 결과를 저장한다.
4. aggregate.md에 중복 제거해서 요약한다.
5. Claude Code는 aggregate.md만 보고 구현한다.
```

초기 동시성은 3~4로 제한한다.

```text
recommended_concurrency: 3~4
max_concurrency: 11
429 발생 시 key rotation + backoff
```

## 32.4 Bootstrap을 본체 기능으로 과도하게 확장하지 말 것

bootstrap은 HACO를 만들기 위한 임시 도구다.

이번 구현에서 bootstrap은 다음 정도면 충분하다.

```text
- bootstrap prompt 파일 제공
- bootstrap.py 골격 제공
- mock bootstrap 테스트
- google provider가 설정되어 있으면 11-key review를 실행할 수 있는 구조
```

bootstrap이 HACO 본체보다 커지면 안 된다.

---

# 33. AGENTS.md 내용

`AGENTS.md`는 이 프로젝트를 수정하는 Claude Code 또는 Codex가 지켜야 할 규칙이다.

```md
# AGENTS.md

This project is HACO.

HACO means Harness for Agent Cost Optimization.

Goal:
Build and maintain a Python CLI that reduces expensive coding-agent usage by creating compact task packets and coding candidates before Codex/Claude Code performs real work.

Core rules:
- Keep the project CLI-first.
- HACO is used by coding agents, not primarily by the human user.
- Do not add MCP, web UI, dashboard, database, vector DB, or auto-editing unless explicitly requested.
- Mock mode must always work.
- Worker outputs must be JSON and schema-validated.
- HACO must not modify target project files in its default mode.
- Gemma workers are allowed to generate candidate packages, test candidates, and fix candidates.
- Do not rely on raw unified diff as the primary candidate format.
- Candidate directories must include candidate.json and, when possible, edit_plan.md/search_replace.json/replacement_blocks.md.
- candidate_judge must hard-filter low-quality candidates before they appear in execution_brief.md.
- Codex/Claude Code remains the final integrator and executor.
- Prefer small, deterministic, testable functions.
- Use Python AST repo_map as the required baseline; tree-sitter is optional.
- Apply token/size budgets so HACO does not become a context bloat source.
- Budget trimming must preserve JSON/Markdown structural integrity.
- Postflight must record HACO effectiveness signals.
- Bootstrap workers may review and propose, but must not edit files directly.
- Never log API key values.
- Keep reports short.
- Do not create unnecessary planning documents.
- Update README when CLI behavior changes.
- Do not ask the user about minor implementation choices.
```

---

# 34. README.md 필수 내용

README에는 다음을 넣는다.

```text
1. HACO가 무엇인지
2. HACO는 사람이 직접 쓰는 앱이 아니라 코딩 에이전트가 호출하는 하네스라는 점
3. 왜 사용하는지
4. Gemma worker와 Codex/Claude Code의 역할 분담
5. 설치 방법
6. mock mode 사용법
7. google provider 설정법
8. 다중 API key 설정법
9. preflight 사용법
10. preflight profile quick/standard/deep 설명
11. postflight 사용법
12. run 사용법
13. Claude Code / Codex와 함께 쓰는 법
14. “하코 사용해서 작업해”라고 했을 때 코딩 에이전트가 해야 할 내부 절차
15. 출력 파일 설명
16. candidates 디렉터리 설명
17. candidate hard filtering 설명
18. 왜 .diff를 기본 포맷으로 삼지 않는지
19. repository map 설명
20. token/size budget 설명
21. structural trimming 설명
22. bounded exploration 설명
23. mandatory first-step validation 설명
24. HACO effectiveness tracking 설명
25. skip_to_main_agent와 skip_reason 설명
26. bootstrap 11-key Gemma review 설명
27. 안전 원칙
28. 제한사항
29. 긴 작업 지시는 --task-file 사용 권장
30. candidates는 적용 가능한 정답이 아니라 메인 코딩 에이전트가 검토할 후보군이라는 점
31. primary_language/test_frameworks 감지는 best-effort이며 틀릴 수 있다는 점
32. provider rate limit 발생 시 worker 단위 fallback으로 전체 흐름을 계속 진행한다는 점
33. core worker 실패 시 skip_to_main_agent로 전환한다는 점
34. 참고 레퍼런스: Aider, SWE-agent, AlphaCodium
```

README는 철학 문서처럼 길게 쓰지 말고 실제 사용법 중심으로 작성한다.

레퍼런스는 짧게만 적는다.

```text
- Aider: repository map, search/replace style edit format
- SWE-agent: agent-computer interface and bounded tool use
- AlphaCodium: code generation as multi-stage flow engineering
```

---

# 35. 다른 프로젝트에서 HACO를 쓰는 규칙

HACO를 사용하는 대상 프로젝트의 `AGENTS.md` 또는 `CLAUDE.md`에 넣을 수 있도록 README에 아래 템플릿을 제공한다.

```md
## HACO Usage Rule

When the user says “use haco”, “하코 사용”, or asks to reduce expensive model usage:

1. If the user task is long, multiline, or likely to exceed shell argument limits, write it to `.haco/task_input.md` or another temporary task file first.
2. Run one of:
   - `python -m haco preflight --project . --task "<user task>"`
   - `python -m haco preflight --project . --task-file .haco/task_input.md`
3. Read `.haco/runs/latest/task_packet.json`.
4. Read `.haco/runs/latest/execution_brief.md`.
5. Inspect accepted candidates in `.haco/runs/latest/candidates/`.
6. Prefer adapting HACO candidates before writing a patch from scratch.
7. Do not blindly apply `optional.diff`; prefer edit_plan/search_replace/replacement_blocks.
8. Apply changes yourself.
9. Run the recommended tests unless clearly impossible.
10. Write execution results into the HACO run directory:
   - execution_result.md
   - diff_summary.md
   - test_log.txt or tests_skipped.md
11. In execution_result.md, include a `HACO Validation` section.
12. Run `python -m haco postflight --run .haco/runs/latest --project .`.
13. Report to the user only after completion.

Do not ask the user for minor decisions if HACO says `user_decision_needed=false`.
If HACO says `haco_status=skip_to_main_agent`, proceed with normal bounded exploration.
```

---

# 36. 테스트

pytest 테스트를 만든다.

필수 테스트:

```text
test_schemas.py
- worker output schema validation
- task_packet schema validation
- postflight packet schema validation
- candidate metadata schema validation

test_scanner.py
- project snapshot 생성
- ignore_dirs 적용
- important files 탐지
- primary_language 필드 존재 확인
- project_type 필드 존재 확인
- test_frameworks 필드 존재 확인

test_repo_map.py
- Python ast 기반 function/class 추출 확인
- import 추출 확인
- docstring preview 추출 확인
- repo_map_status 확인
- Python 파싱 실패 시 fallback 확인

test_budget.py
- char budget 계산 확인
- project_snapshot structural trimming 확인
- repo_map structural trimming 확인
- truncation_notes 기록 확인
- trimming 후 valid JSON 확인

test_preflight_mock.py
- mock provider로 preflight 실행
- input.md 생성 확인
- project_snapshot.json 생성 확인
- repo_map 필드 생성 확인
- worker_outputs 생성 확인
- task_packet.json 생성 확인
- execution_brief.md 생성 확인
- candidates 디렉터리 생성 확인
- candidate directory 생성 확인
- candidate hard filtering 결과 확인
- metrics.json 생성 확인
- worker_timings 기록 확인
- .haco/runs/latest 확인
- --task-file 입력 확인
- --profile quick 실행 확인
- --profile standard 실행 확인

test_locator_rescan.py
- file_locator low confidence 시 2-pass focused rescan 시도 확인
- 2-pass 실패 시 skip_to_main_agent 확인

test_postflight_mock.py
- report.md 생성 확인
- postflight_packet.json 생성 확인
- HACO Validation parsing 확인
- missing HACO Validation warning 확인
- test_log 없이도 동작 확인

test_aggregate.py
- risk high 우선순위 확인
- new_doc_needed 기본 false 확인
- user_decision_needed aggregation 확인
- non-core worker 실패 fallback 확인
- core worker 실패 시 haco_status=skip_to_main_agent 확인
- skip_reason 기록 확인

test_brief_builder.py
- execution_brief.md에 mandatory first step 포함 확인
- HACO Validation 기록 요구 포함 확인
- accepted candidates 목록 포함 확인
- masked/rejected 후보 미노출 확인
- postflight 실행 지시 포함 확인
- bounded exploration 규칙 포함 확인
- optional.diff 맹목 적용 금지 문구 포함 확인

test_candidate_store.py
- candidate directory 저장 확인
- candidate.json 저장 확인
- edit_plan.md 저장 확인
- search_replace.json 저장 확인
- replacement_blocks.md 저장 확인
- optional.diff가 없어도 정상 동작 확인
- rejected 후보가 execution_brief에 노출되지 않는지 확인

test_run_store.py
- .haco/runs 아래 run 생성 확인
- latest resolve 확인

test_bootstrap.py
- bootstrap prompt 존재 확인
- mock bootstrap worker outputs 생성 확인
- aggregate.md 생성 확인
- API key value가 output에 기록되지 않는지 확인

test_cli.py
- doctor 실행
- show 실행
- run 실행
- run --task-file 실행
```

---

# 37. 성공 기준

다음 명령이 성공해야 한다.

```bash
python -m haco doctor
```

다음 명령도 성공해야 한다.

```bash
python -m haco preflight --project . --task "Add a small feature and update status only."
```

다음 명령도 성공해야 한다.

```bash
python -m haco preflight --project . --task-file task.md
python -m haco run --project . --task-file task.md
```

다음 명령도 성공해야 한다.

```bash
python -m haco preflight --project . --task "Add a small feature" --profile quick
python -m haco preflight --project . --task "Add a small feature" --profile standard
```

실행 시 다음이 생성되어야 한다.

```text
.haco/runs/latest/input.md
.haco/runs/latest/project_snapshot.json
.haco/runs/latest/worker_outputs/*.json
.haco/runs/latest/task_packet.json
.haco/runs/latest/execution_brief.md
.haco/runs/latest/candidates/
.haco/runs/latest/metrics.json
```

`project_snapshot.json`에는 최소한 다음 필드가 있어야 한다.

```json
{
  "primary_language": "unknown",
  "project_type": "unknown",
  "test_frameworks": [],
  "repo_map": [],
  "repo_map_status": "ok | partial | skipped"
}
```

candidate가 생성되는 경우 다음 구조가 있어야 한다.

```text
.haco/runs/latest/candidates/candidate_01/candidate.json
.haco/runs/latest/candidates/candidate_01/edit_plan.md
```

그리고:

```bash
python -m haco show .haco/runs/latest
```

정상 출력되어야 한다.

그리고:

```bash
python -m haco postflight --run .haco/runs/latest --project .
```

실행 시 다음이 생성되어야 한다.

```text
.haco/runs/latest/report.md
.haco/runs/latest/postflight_packet.json
```

마지막으로:

```bash
pytest
```

통과해야 한다.

mock mode에서 `primary_language`가 unknown이어도 전체 실행은 성공해야 한다.
Rate limit/backoff 설정이 없어도 mock provider는 정상 동작해야 한다.
tree-sitter가 설치되어 있지 않아도 전체 실행은 성공해야 한다.
실제 Google API key가 없어도 mock 기반 테스트는 모두 통과해야 한다.

---

# 38. 구현 순서

Claude Code는 다음 순서로 구현한다.

```text
1. 프로젝트 구조 생성
2. pyproject.toml 작성
3. pydantic schemas 작성
4. run_store 작성
5. scanner 작성
6. repo_map 작성
7. budget 작성
8. candidate_store 작성
9. metrics 작성
10. MockProvider 작성
11. GoogleProvider 골격 작성
12. provider retry/backoff 구조 작성
13. prompt loader 작성
14. worker runner 작성
15. worker sequencing/concurrency 처리 작성
16. file_locator 2-pass rescan 작성
17. candidate hard filtering 작성
18. aggregate 작성
19. brief_builder 작성
20. preflight profile 처리 작성
21. preflight command 작성
22. postflight command 작성
23. doctor command 작성
24. show command 작성
25. run command 작성
26. bootstrap prompt / bootstrap.py mock 경로 작성
27. README 작성
28. AGENTS.md 작성
29. pytest 작성
30. 전체 테스트 실행
31. 실패 수정
32. 최종 보고
```

중간에 사용자에게 묻지 말고 합리적으로 결정한다.

구현 우선순위:

```text
1. mock end-to-end
2. scanner + Python AST repo_map
3. budget structural trimming
4. candidate directory
5. candidate hard filtering
6. execution_brief + mandatory validation
7. postflight validation parsing
8. skip_reason/effectiveness metrics
9. google provider 골격
10. bootstrap mock 경로
```

선택 기능은 필수 성공 기준 이후에만 구현한다.

---

# 39. 최종 보고 형식

작업 완료 후 Claude Code는 아래 형식으로만 보고한다.

```text
Changed:
Tests:
Result:
Remaining risk:
Next:
```

보고는 짧게 한다.

---

# 40. 가장 중요한 판단 기준

이 프로젝트의 성공 기준은 “멋진 멀티에이전트 시스템”이 아니다.

성공 기준은 다음이다.

```text
Claude Code/Codex가 처음부터 넓게 읽고 길게 생각하지 않도록,
Gemma worker가 task_packet, candidate packages, execution_brief를 먼저 만들어주는가?
```

구현 중 선택이 필요하면 항상 다음 기준으로 결정한다.

```text
사용량을 줄이는가?
메인 에이전트가 읽을 양을 줄이는가?
사소한 사용자 판단을 줄이는가?
Gemma 31B의 코딩 능력을 후보 생성에 활용하는가?
.diff 깨짐으로 메인 에이전트를 낭비시키지 않는가?
core worker 실패 시 garbage-in garbage-out을 막는가?
file_locator SPOF를 2-pass rescan으로 완화하는가?
후보가 많아져서 메인 에이전트 토큰을 낭비하지 않도록 hard filtering하는가?
repo_map으로 대형 저장소 탐색 비용을 줄이는가?
budget/circuit breaker로 HACO 자체의 context bloat를 막는가?
structural trimming으로 JSON/Markdown을 깨뜨리지 않는가?
worker sequencing/concurrency로 preflight latency와 후보 품질을 균형 있게 다루는가?
HACO effectiveness를 postflight에서 측정하는가?
skip_to_main_agent 원인을 기록하는가?
API key가 절대 로그/리포트/출력에 새지 않는가?
대상 프로젝트를 안전하게 보호하는가?
mock mode로 항상 테스트 가능한가?
Claude Code/Codex가 직접 haco를 호출하는 흐름에 맞는가?
```

이 기준에 맞으면 구현하고, 맞지 않으면 넣지 않는다.

---

# 41. 비판적 자가검증

아래는 이 구현 계약서 자체에 대한 비판적 자가검증이다.
Claude Code는 구현 중 아래 리스크를 염두에 두고, 과도한 확장보다 동작하는 최소 안정 구현을 우선하라.

## 41.1 리스크: 문서가 너무 커져 구현 부담이 커질 수 있음

문제:

```text
HACO는 사용량을 줄이기 위한 도구인데, 구현 계약서가 너무 길면 Claude Code가 문서를 이해하는 데 많은 토큰을 쓸 수 있다.
```

방어:

```text
- 모든 기능을 “대형 프레임워크”로 만들지 않는다.
- mock provider 기준으로 먼저 끝까지 동작하게 만든다.
- tree-sitter, tiktoken, aiohttp는 선택 사항으로 둔다.
- Python AST repo_map, structural trimming, candidate hard filtering은 작고 결정적으로 구현한다.
```

판정:

```text
허용 가능한 리스크다.
단, 구현자는 “화려함”보다 “CLI end-to-end 성공”을 우선해야 한다.
```

## 41.2 리스크: HACO 자체가 토큰 이중 지출을 만들 수 있음

문제:

```text
Gemma 후보가 틀리면 Claude/Codex가 오답을 검토하고 다시 탐색해야 한다.
이 경우 worker 비용 + 메인 검증 비용 + 재탐색 비용이 발생한다.
```

방어:

```text
- candidate hard filtering
- accepted 후보만 execution_brief 노출
- masked/rejected 후보 미노출
- core worker 실패 시 skip_to_main_agent
- postflight의 HACO Validation 기록
- candidate usefulness 기록
```

판정:

```text
방어 장치가 명세에 포함되어 있다.
구현 시 candidate_judge를 형식적 worker로 만들지 말고 실제 filtering 로직을 넣어야 한다.
```

## 41.3 리스크: file_locator가 SPOF가 될 수 있음

문제:

```text
file_locator가 틀리면 후속 candidate들이 전부 잘못될 수 있다.
```

방어:

```text
- project_snapshot
- repo_map
- keyword_file_matches
- file_locator 2-pass focused rescan
- 2-pass 실패 시 skip_to_main_agent
```

판정:

```text
완전히 해결되지는 않지만 충분히 완화된다.
본격 RAG/vector DB는 이번 범위에서 제외하는 판단이 맞다.
```

## 41.4 리스크: patch_candidate와 test_candidate의 실행 순서 충돌

문제:

```text
patch와 test를 무조건 병렬 실행하면 test_candidate가 patch 내용을 모른 채 테스트를 만들 수 있다.
```

방어:

```text
- code_change/refactor는 patch_candidate → test_candidate 순서
- test_failure는 failure_fixer/test reproduction 우선 가능
- deep profile에서만 patch 후보 복수 병렬 생성 가능
```

판정:

```text
명세상 해결되어 있다.
구현 시 단순 asyncio.gather로 모든 worker를 무조건 병렬 실행하면 안 된다.
```

## 41.5 리스크: budget trimming이 JSON/Markdown을 깨뜨릴 수 있음

문제:

```text
문자열 substring 방식으로 자르면 JSON, code fence, repo_map 구조가 깨질 수 있다.
```

방어:

```text
- structural trimming 필수
- list item 제거
- symbol 배열 축소
- docstring_preview 필드 내부 축약
- serialization 검증
- fallback minimal snapshot
```

판정:

```text
해결 방향이 명확하다.
budget.py는 반드시 테스트로 보호해야 한다.
```

## 41.6 리스크: execution_brief를 메인 에이전트가 무시할 수 있음

문제:

```text
Claude Code/Codex는 자체 시스템 프롬프트가 있어서 HACO의 지시를 참고 문서로만 볼 수 있다.
```

방어:

```text
- “탐색 금지”가 아니라 mandatory first-step validation 요구
- execution_result.md에 HACO Validation 기록 의무
- postflight가 validation 기록을 확인하고 warning 생성
- bounded exploration 허용
```

판정:

```text
완전 강제는 불가능하지만 현실적인 통제 방식이다.
postflight가 validation 기록을 읽으므로 실제 사용성 측정도 가능하다.
```

## 41.7 리스크: 기능 범위가 커져 첫 구현이 실패할 수 있음

문제:

```text
repo_map, budget, worker, provider, candidate filtering, postflight, bootstrap까지 한 번에 만들면 복잡하다.
```

방어:

```text
- mock provider first
- google provider는 골격 우선
- tree-sitter/tiktoken/aiohttp는 optional
- bootstrap은 mock 경로와 prompt 제공 수준으로 제한
- 기본 end-to-end 명령 통과가 최우선
```

판정:

```text
구현 가능하다.
다만 Claude Code는 모든 선택 기능을 완성하려고 하지 말고 필수 성공 기준을 먼저 통과시켜야 한다.
```

## 41.8 리스크: Gemma 11-key bootstrap이 본체보다 커질 수 있음

문제:

```text
HACO 제작용 bootstrap을 과하게 만들면 본래 목표인 HACO 구현보다 bootstrap 관리가 더 커질 수 있다.
```

방어:

```text
- bootstrap은 임시 발판으로 제한한다.
- bootstrap worker는 파일을 직접 수정하지 않는다.
- bootstrap.py는 mock + google provider 연결 골격 정도만 둔다.
- 핵심은 worker output과 aggregate.md 생성이다.
```

판정:

```text
허용 가능한 리스크다.
HACO 본체 구현을 방해할 정도로 bootstrap을 키우면 안 된다.
```

## 41.9 남는 약점

```text
- HACO가 실제 비용을 줄이는지는 postflight 누적 데이터가 쌓여야 판단 가능하다.
- Gemma 후보 품질이 낮은 작업에서는 skip_to_main_agent가 자주 발생할 수 있다.
- repo_map은 Python 중심으로 시작하므로 JS/TS/Rust/Go 대형 프로젝트에서는 초기에 제한적이다.
- Claude Code/Codex가 execution_brief를 완전히 따르도록 강제할 수는 없다.
- bootstrap 11-key 활용은 API quota와 rate limit 영향을 받는다.
```

## 41.10 최종 자가판정

이 계약서는 다음 장점을 가진다.

```text
- HACO의 직접 사용자를 사람에서 Claude Code/Codex로 정확히 설정했다.
- Gemma 31B를 단순 평가원이 아니라 junior coder pool로 사용한다.
- unified diff 취약성을 피하고 candidate package 방식을 채택했다.
- repo_map으로 대형 저장소 탐색 비용을 줄인다.
- structural trimming으로 HACO 자체의 context bloat를 방지한다.
- file_locator SPOF를 2-pass rescan으로 완화한다.
- candidate hard filtering으로 토큰 이중 지출을 줄인다.
- execution_brief에 mandatory first-step validation을 넣어 무시 가능성을 낮춘다.
- postflight에 HACO effectiveness tracking을 넣어 실제 효율을 측정한다.
- skip_to_main_agent 원인을 기록해 HACO 개선 루프를 만든다.
- HACO 제작 자체에도 Gemma 11-key bootstrap 검토를 활용할 수 있다.
- mock-first로 테스트 가능성을 확보했다.
```

최종 판단:

```text
이 정본은 구현에 투입해도 된다.
더 이상 설계 문서를 확장하지 말고, mock 기반 end-to-end 구현으로 들어간다.
```
