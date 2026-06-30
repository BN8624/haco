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

## 라이브 검증 결과
- 실제 `.env` 키로 google provider 검증 완료. 모델 `gemma-4-31b-it` 실재 확인(계약서 예시 모델명 정확). 단일 task_router 호출이 스키마에 맞는 JSON 반환.
- 11개 키 슬롯 자동 탐지 확인. 429 재시도/키 회전/exponential backoff는 fake client 단위 테스트로 검증.
- **google 전체 preflight는 7개 워커 순차 호출로 31B 모델 지연이 누적돼 느림**(2분+). 정확성 문제 아님. mock은 즉시. 필요시 §17 asyncio 병렬화로 후속 최적화 가능(현재 core 워커는 계약서대로 순차).
- `latest`는 환경에 따라 symlink/junction/marker 3단계 폴백. C:\Users\USER\haco에선 symlink 동작. junction 폴백 시 mklink 출력은 DEVNULL로 버림(한국어 콘솔 인코딩 크래시 방지).

## 미해결 / 추후
- tree-sitter, tiktoken: optional, 미구현 (char/4 토큰 추정 사용).
- google 전체 파이프라인 latency 최적화(asyncio 병렬) — optional.
- `python -m haco bootstrap`의 라이브 11-key 실행은 quota 고려해 미실행(mock 경로/테스트만 검증).
