# HANDOFF

현재 상태만 기록한다. 역사·설계 논쟁은 넣지 않는다. 오래된 항목은 지우고 갱신한다.

---

## 현재 초점

문서 체계를 신 표준(`HACO_CANON.md` 정본 + `DOCS_INDEX.md` 라우터 + `CLAUDE.md`/`AGENTS.md` 규칙 + `HANDOFF.md` + `CHECKLIST.md`)으로 재구성 완료. 구 문서는 `archive/`로 이동.

- `CLAUDE.md`와 `AGENTS.md`는 byte-identical (확인 완료).
- 구 정본 `HACO.md`(74KB 구현 계약서)는 `archive/HACO.md`로 이동. 상세 계약 원문이 필요하면 여기 참조.
- 구 작업 노트 `context-notes.md`, 구 빌드 체크리스트 `checklist.md`도 `archive/`에 보존.

---

## 구현 상태

HACO 코어는 구현·검증 완료.

- 파이프라인: preflight(task_router → file_locator → scanner/repo_map → context_compressor → candidate → brief) / postflight / doctor / bootstrap.
- Provider: mock + google. 실제 `.env` 11키로 라이브 검증 완료, 모델 `gemma-4-31b-it` 실재 확인.
- 테스트: `pytest` 전체 통과, `python -m haco doctor` 정상.

### 직전 세션 반영 수정 (git log 참조)

- scanner가 gitignore된 root scratch를 file_paths에 넣던 노이즈 제거 (`git check-ignore`, Windows `\r`/quotePath 함정 해결).
- `prior_change_reference.md`: 반복 증분 작업에 마지막 관련 커밋 diff를 템플릿으로 제공.
- `task_type` planning 과탐(`plan` 부분일치) 수정 → marker 구현 작업이 candidate 정상 생성.
- `file_locator` archive/deprecated 경로 점수 감쇠(×0.2)로 live 파일 우선.
- postflight가 verifier `status PASS/FAIL` 라인 인식 + unknown을 `failed`로 오표기하던 문제 수정.

---

## 미해결 / 후속 후보

- tree-sitter, tiktoken: optional, 미구현 (현재 char/4 토큰 추정).
- google 전체 preflight latency: 7개 워커 순차 호출로 31B 모델 지연 누적(2분+). §17 asyncio 병렬화로 최적화 가능 (정확성 문제 아님).
- `python -m haco bootstrap` 라이브 11-key 실행: quota 고려해 미실행 (mock 경로/테스트만 검증).
- scanner gitignore 잔여: 해결됨. 재발 시 `-z` NUL 구분 경로 확인.

---

## 다음 세션 유의

- 저장소 정체성 먼저 확인 (`pwd` / `git remote -v` / `git status`).
- `HACO_CANON.md`는 정본이라 임의 수정 금지. 수정 시 사용자 승인.
- `CLAUDE.md` 수정 시 `AGENTS.md`도 동일 내용으로 갱신 후 `cmp -s`로 검증.
- `.haco/`는 커밋하지 않는다.
