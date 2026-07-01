# CHECKLIST

반복 실수를 막는 능동 점검 목록이다. 일반 문서가 아니다. 매 작업에서 해당 항목을 확인한다.

---

## 저장소 안전

- [ ] 편집 전 저장소 정체성 확인 (`pwd`, `git remote -v`, `git status`).
- [ ] `git add -A` 금지. 명시적 파일만 스테이징.
- [ ] `.haco/`, scratch, cache, 복사된 잡파일이 스테이징되지 않았는지 `git status`로 확인.
- [ ] 커밋은 한 저장소·한 목적으로 스코프 유지. HACO와 외부 프로젝트(GODSEED 등) 커밋 분리.
- [ ] 사용자가 명시 승인하지 않으면 push 금지.

## 문서 규칙

- [ ] `CLAUDE.md` 수정 시 `AGENTS.md`도 동일 내용으로 갱신하고 `cmp -s CLAUDE.md AGENTS.md`로 byte-identity 검증.
- [ ] `HACO_CANON.md`(정본)는 사용자 승인 없이 수정하지 않는다.
- [ ] 문서 sprawl 금지. 규칙은 `CLAUDE.md`, 정본은 canon, 라우팅은 `DOCS_INDEX.md`, 현재 상태는 `HANDOFF.md`에만.
- [ ] 구 문서는 삭제하지 말고 `archive/`로 이동.

## HACO 워크플로

- [ ] 비자명 저장소 작업은 preflight 먼저. skip 시 사유 기록.
- [ ] 편집 전 `context_pack.md` → `task_packet.json` → `execution_brief.md` → `candidates/` 순으로 확인.
- [ ] `haco_status=skip_to_main_agent`면 bounded exploration으로 진행하고 skip 사유 기록.
- [ ] 저신뢰면 후보를 짧게. 억지 후보 생성 금지 (fail closed).
- [ ] 작업 후 `execution_result.md`에 HACO Validation 블록 작성.

## 검증

- [ ] 코드를 건드렸으면 완료 보고 전 `pytest` 실행. 실패면 고치고 재실행.
- [ ] 실패·스킵·미커밋·불확실성을 정직하게 보고.

## Windows 함정

- [ ] `git check-ignore` 등 native exe 호출 시 `\r`/quotePath로 경로 매칭 깨짐 주의 (`-z` NUL 구분 + bytes).
- [ ] 파일시스템 대소문자 무시 — `CHECKLIST.md`와 `checklist.md`는 동일 파일.
- [ ] 콘솔 한국어 인코딩 크래시 방지 — 불필요한 native 출력은 DEVNULL 처리.
