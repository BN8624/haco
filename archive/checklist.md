# HACO 구현 체크리스트

## 골격
- [x] pyproject.toml + console script
- [x] .env.example
- [x] config.example.yaml (계약서 §13)
- [x] haco/__init__.py, __main__.py

## 코어 모듈
- [x] schemas.py (pydantic worker/packet 스키마)
- [x] config.py
- [x] utils.py
- [x] run_store.py (runs dir + latest)
- [x] scanner.py (project snapshot)
- [x] repo_map.py (Python AST + best-effort regex)
- [x] budget.py (structural trimming)
- [x] metrics.py
- [x] candidate_store.py (candidate dirs + hard filtering)
- [x] model_client.py (Mock + Google + retry/backoff/key rotation)
- [x] workers.py (prompt loader + runner + sequencing + 2-pass rescan)
- [x] aggregate.py (task_packet)
- [x] brief_builder.py (execution_brief.md)
- [x] preflight.py (profile 처리 + 오케스트레이션)
- [x] postflight.py (validation parsing + report)
- [x] doctor.py
- [x] cli.py (init/doctor/preflight/run/show/postflight)
- [x] bootstrap.py

## 프롬프트
- [x] prompts/*.md (8개 워커)
- [x] bootstrap/prompts/*.md (11개)

## 문서
- [x] README.md
- [x] AGENTS.md

## 테스트
- [x] tests/* (schemas, scanner, repo_map, budget, preflight_mock, postflight_mock, aggregate, brief_builder, candidate_store, run_store, bootstrap, cli, locator_rescan)

## 검증
- [x] python -m haco doctor
- [x] python -m haco preflight (--task / --task-file / --profile)
- [x] python -m haco show / postflight / run
- [x] pytest 전체 통과
