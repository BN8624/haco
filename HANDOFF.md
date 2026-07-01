# HANDOFF

현재 상태만 기록한다. 역사·설계 논쟁은 넣지 않는다. 오래된 항목은 지우고 갱신한다.

---

## 현재 초점

정본(`HACO_CANON.md`)이 약속한 핵심 산출물과 Fail Closed 원칙을 코드·테스트에 반영 완료. 최근 dogfood(GODSEED)에서 드러난 Locator context miss까지 교정. 문서 체계(정본 + `DOCS_INDEX` 라우터 + `CLAUDE`/`AGENTS` 규칙 + `HANDOFF` + `CHECKLIST`)는 신 표준으로 정착, 구 문서는 `archive/`.

- `CLAUDE.md` ≡ `AGENTS.md` byte-identical (확인 완료). README는 규칙상 금지(개인용).

---

## 구현 상태

HACO 코어 + context offloading + fail-closed + locator ranking(2차 보강) + locator eval harness 구현·검증 완료. `pytest` 133 passed, `doctor` 통과.

- 파이프라인: preflight(scan/repo_map → task_router → context_compressor → file_locator → **context_pack** → candidate → aggregate → brief) / postflight / doctor / bootstrap.
- Provider: mock + google(gemma-4-31b-it, .env 11키 라이브 검증).

### 이번 세션 반영 (정본 정합 + 리뷰 반영)

- **context_pack.md/json** 생성(§7.1/§9): repo_map 심볼 범위·markdown 섹션·키워드 윈도우로 결정론적 focused excerpt. budget(8k tok)·fail-closed. repo_map 심볼에 line 범위 추가.
- **postflight auto_diff_summary.md**(§7.3): git 작업트리 결정론 요약.
- **Fail Closed / Confidence Calibration**(§17.1): `haco/confidence.py` — Hard Gate → Evidence Score → Tier. preflight가 후보 생성 前 평가, fail-closed면 skip. tier<high면 accepted→masked. candidate anchor 검증(placeholder/0회·다회 매칭/full_block symbol 미존재 → accepted 불가). 스키마/브리프/postflight에 confidence 필드.
- **Locator Ranking (Intent Expansion)**: 식별자 키워드 상위화(절단 생존), 파일명 stem 정확매칭 boost, context_pack이 snapshot.search_hints 사용 + 심볼 매칭 tier(이름>시그니처), content-aware 랭킹(파일명 아닌 심볼 내용으로 타깃 파일 상위화). GODSEED miss(dataclass+phase3 → 실제 함수+phase5) 교정 확인.
- **Locator Ranking 2차 보강**: `haco/ranking.py` `post_locator_rerank` — LLM locator는 제안자, 결정론 랭커가 최종 파일 순서 확정(preflight Stage 1.6, rescan 이후·context_pack 전). worker top과 다르면 `locator_adjusted`/`locator_adjust_reason`(packet/metrics). repo_map이 top-level 상수/설정(UPPER_CASE, `*_RELIEF/_THRESHOLD/_YEARS/_DAYS`, ast.Assign/AnnAssign, line 범위) 추출. context_pack symbol entry에 `match_tier`(exact_name/partial_name/signature) + 정확매칭 다수면 MAX_SYMBOLS 3→6 adaptive. confidence는 exact=strong_symbol_evidence(+25)/signature=weak(+10)로 세분화. 근거 없으면(score 0) locator 원본 유지(fail-closed).
- **Locator eval harness**: `tests/test_eval_locator.py` — 라벨 fixture로 rerank on/off top-1 hit-rate 측정(LLM API 미사용, 결정론). 회귀 테스트 겸 수동 스크립트(`python tests/test_eval_locator.py`). 현재 baseline 2/4(50%) → rerank 4/4(100%). 실 miss 사례는 `CASES`에 추가해 eval 셋을 키운다.

---

## 미해결 / 후속 후보

- tree-sitter, tiktoken: optional, 미구현 (char/4 토큰 추정).
- google 전체 preflight latency: 7워커 순차 + 31B 지연(2분+). asyncio 병렬화 여지.
- `haco bootstrap` 라이브 11-key: quota 고려 미실행(mock/테스트만).
- fail-closed 임계값(§17.1 권장치)·rerank 가중치는 정답 보장 아님 — 튜닝은 eval 셋(`test_eval_locator.py` `CASES`)이 커진 뒤가 의미 있음(현재 4케이스).

---

## 다음 세션 유의

- 저장소 정체성 먼저 확인 (`pwd` / `git remote -v` / `git status`). GODSEED 작업은 `C:\Users\USER\godseed`에서, HACO는 도구.
- `HACO_CANON.md`는 정본이라 임의 수정 금지(수정 시 사용자 승인).
- `CLAUDE.md` 수정 시 `AGENTS.md`도 동일 내용으로 갱신 후 `cmp -s` 검증. README 생성 금지.
- 커밋하면 곧바로 push(사용자 규칙). 단 명시 파일만 스테이징, `.haco/` 커밋 금지.
