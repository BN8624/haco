# HACO 구현 컨텍스트 노트

작업 중 내린 결정과 근거를 계속 추가한다. 정본은 `HACO.md` (수정하려면 사용자 승인 필요).

## 결정 로그

- **정본**: `HACO.md`가 구현 계약서. 임의 수정 금지.
- **Python**: 3.14.5. 설치된 패키지 — pydantic 2.13, python-dotenv 1.2, PyYAML 6, google-genai 2.8, aiohttp 3.13, pytest 9.
- **API 키 네이밍 불일치**: 계약서 §13 config 예시는 `GOOGLE_API_KEY_01`..`_11` (zero-pad), 실제 `.env`는 `GOOGLE_API_KEY_1`..`_11`. → GoogleProvider 키 탐지를 robust하게: (1) config의 `api_key_envs` 목록, (2) `api_key_env` 단일, (3) `GOOGLE_API_KEY` / `HACO_GOOGLE_API_KEY`, (4) 정규식 `GOOGLE_API_KEY_?\d+` 스캔. 두 패턴 모두 동작. config.example.yaml은 계약서대로 유지.
- **--task vs --task-file 우선순위**: `--task-file` 우선 (둘 다 주어지면 파일 사용 + stderr 경고). 계약서 §7 허용 범위. README 명시.
- **MockProvider 결정성**: 워커 프롬프트에 `<<<HACO_CONTEXT_JSON>>> ... <<<END>>>` 머신리더블 블록을 넣고 MockProvider가 이를 파싱해 입력 인지형(deterministic) 출력 생성. GoogleProvider는 이를 추가 컨텍스트로만 취급.
- **latest 해석**: Windows symlink 권한 문제 가능 → symlink 시도, 실패 시 `latest`를 marker 파일(디렉터리명 기록)로 대체. `show .haco/runs/latest`가 두 방식 모두에서 동작.
- **bootstrap**: 계약서 §32.4/§41.8에 따라 본체보다 키우지 않음. prompt 파일 + bootstrap.py 골격 + mock 테스트까지만. 실제 11-key 라이브 리뷰는 quota 소모 → 자동 실행하지 않음(옵션 경로만 제공).
- **diff**: optional artifact. 기본 적용 포맷 아님 (§20.5).
- **run 인자 해석 확장**: preflight는 `--project`만으로 run을 만드는데 postflight/show는 같은 run을 run ID나 `latest`로 못 찾고 전체 절대경로를 강제했다. `resolve_run`에 `project_path`/`runs_dir` 옵션을 더해, 인자가 직접 가리키는 경로가 아니면 `<project>/.haco/runs/<arg>`에서 재해석한다(기존 절대경로 직접 해석은 `_resolve_existing`으로 보존). `cmd_postflight`는 project_path를 resolve 앞으로 옮겨 넘기고, `cmd_show`엔 `--project`를 추가. 정본 HACO.md의 CLI 예시(절대경로)는 상위호환이라 그대로 유효 → 정본 미수정.
- **postflight 실패 판정**: `_detect_test_outcome`이 부분문자열(`failed`·`passed` 동시 존재)로 판정해 실제 pytest 실패 요약(`1 failed, 71 passed`)을 unknown으로 떨궜고 failure_fixer가 안 돌았다(1개라도 통과하면 실패 놓침). `N failed`/`N error(s)` 카운트를 정규식으로 우선 신뢰(합 0이면 통과, >0이면 실패)하고, 카운트가 없을 때만 강한 마커로 폴백한다. 오탐 잦은 단독 `error`/`fail` 토큰은 폴백에서 제외.
- **verifier status 라인 인식 + unknown 렌더링**: pytest를 안 쓰는 자체 verifier(예: GODSEED `verify_phase*.py`)는 `status PASS/FAIL`만 찍어 카운트도 `passed` 부분문자열도 없어 unknown으로 떨어졌다. 게다가 report 렌더링이 `("passed" if tests_passed else "failed")`라 unknown(None)을 `failed`로 **오표기**했다. (1) `_detect_test_outcome`에 pytest 카운트 다음 우선순위로 `status\s*:?\s+(pass|fail)` 정규식을 추가(다중 라인이면 전부 pass라야 통과). (2) report의 Tests 표기를 not run/unknown/passed/failed 4분기로 분리해 None을 `unknown`으로 표기.
- **task_type planning 과탐(`plan` 부분일치)**: `_detect_task_type`이 `plan`/`research`를 code_signal 계산 *전에* 부분일치로 판정해, `PHASE_5_IMPLEMENTATION_PLAN.md`를 언급한 marker 구현 작업을 `planning`으로 오분류 → `_patch_test_suppressed`로 candidate 생성이 통째로 억제됐다(GODSEED Phase 5 5개 run 전부 candidate 0/0, recommended_mode preflight_only). "doc" 부분일치 버그와 동형. 수정: code_signal에 marker/event/engine/이벤트/엔진 추가, plan/research/design 영어 키워드는 단어경계(`\bplan\b` → `implementation_plan` 식별자 부분일치 차단)로 매칭, planning/research/docs_only는 전부 `not code_signal` 게이트. 결과 godseed marker 작업이 code_change→candidate 2/2로 정상화.
- **file_locator archive 노이즈**: `_keyword_matches`가 `docs/archive/...` 닫힌 문서를 live 파일과 동일 점수로 올려 files_to_read 상위 4를 잠식했다(매 run observer/archive 문서 2건 혼입). archive/deprecated/vendor/third_party 경로는 점수 ×0.2로 낮춰 목록엔 남기되 live 파일에 밀리게 함. (잔여: gitignore된 root scratch `*_summary.json`/`*_failures.jsonl`은 archive 경로가 아니라 여전히 혼입 가능 — scanner가 gitignore를 무시하는 별개 이슈, 후속 후보.)
- **mock 한계는 결함 아님(보고)**: test_scope/new_doc_needed/candidate 품질은 mock 휴리스틱·profile·provider 의존이며 google provider에서 달라진다. test_scope는 위 task_type 수정으로 planning 억제가 풀려 code_change→test_candidate 실행→smoke로 개선. new_doc_needed=False는 mock의 의도적 보수 stance(설계). candidate 다건/재사용은 google provider 또는 deep profile 필요.
- **scanner gitignore 제외**: scanner가 fs를 직접 walk해 gitignore된 root scratch(`*_summary.json`/`*_failures.jsonl` 등)까지 file_paths에 넣어 keyword_matches/files_to_read 노이즈가 됐다. `_git_ignored_paths`가 `git check-ignore`로 일괄 판정해 제외(config `scanner.respect_gitignore` 기본 True, git 없으면 무필터). **Windows 함정**: `text=True` stdin이 `\n`→`\r\n` 변환 → git이 경로에 `\r` 포함 + core.quotePath 따옴표 → 매칭 깨짐. `-z`(양방향 NUL 구분) + bytes 입출력으로 해결.
- **prior_change_reference(반복 증분 템플릿)**: 반복 패턴 작업(marker chain 등)에서 candidate가 빈약할 때, files_to_edit[0]을 **마지막으로 바꾼 커밋 diff**를 `prior_change_reference.md`로 써서 "직전 비슷한 변경" 템플릿을 제공. git 기반·결정론·provider 비의존. code_change/refactor/test_failure에서만, 편집 대상/이력 없으면 빈 문자열. task_packet.prior_change_reference + brief 한 줄로 노출. 크기는 max_candidate_total_chars로 절단.

## 라이브 검증 결과
- 실제 `.env` 키로 google provider 검증 완료. 모델 `gemma-4-31b-it` 실재 확인(계약서 예시 모델명 정확). 단일 task_router 호출이 스키마에 맞는 JSON 반환.
- 11개 키 슬롯 자동 탐지 확인. 429 재시도/키 회전/exponential backoff는 fake client 단위 테스트로 검증.
- **google 전체 preflight는 7개 워커 순차 호출로 31B 모델 지연이 누적돼 느림**(2분+). 정확성 문제 아님. mock은 즉시. 필요시 §17 asyncio 병렬화로 후속 최적화 가능(현재 core 워커는 계약서대로 순차).
- `latest`는 환경에 따라 symlink/junction/marker 3단계 폴백. C:\Users\USER\haco에선 symlink 동작. junction 폴백 시 mklink 출력은 DEVNULL로 버림(한국어 콘솔 인코딩 크래시 방지).

## 미해결 / 추후
- tree-sitter, tiktoken: optional, 미구현 (char/4 토큰 추정 사용).
- google 전체 파이프라인 latency 최적화(asyncio 병렬) — optional.
- `python -m haco bootstrap`의 라이브 11-key 실행은 quota 고려해 미실행(mock 경로/테스트만 검증).
