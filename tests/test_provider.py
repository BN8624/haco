# google provider: 다중 키 탐지, 429 재시도/키 회전/백오프 (네트워크 없이).
import pytest

from haco.config import load_config
from haco.model_client import GoogleProvider, MockProvider, ProviderError, get_provider


def test_mock_is_default(config=None):
    cfg = load_config()
    assert isinstance(get_provider(cfg), MockProvider)


def test_key_discovery_both_naming(monkeypatch):
    for i in range(1, 12):
        monkeypatch.setenv(f"GOOGLE_API_KEY_{i}", f"k{i}")
    cfg = load_config()
    slots = GoogleProvider._discover_key_slots(cfg)
    # _1.._11 패턴을 숫자 순으로 인식
    assert "GOOGLE_API_KEY_1" in slots
    assert "GOOGLE_API_KEY_11" in slots
    assert slots.index("GOOGLE_API_KEY_2") < slots.index("GOOGLE_API_KEY_11")


def test_no_key_raises(monkeypatch):
    for k in list(__import__("os").environ):
        if "API_KEY" in k:
            monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("HACO_PROVIDER", "google")
    cfg = load_config()
    gp = GoogleProvider(cfg, sleep_func=lambda s: None)
    with pytest.raises(ProviderError):
        gp.generate_json("prompt", "task_router")


def test_429_retries_rotates_and_backoff(monkeypatch):
    for i in range(1, 4):
        monkeypatch.setenv(f"GOOGLE_API_KEY_{i}", f"k{i}")
    cfg = load_config()
    sleeps = []
    gp = GoogleProvider(cfg, sleep_func=lambda s: sleeps.append(s))

    attempts = {"n": 0}

    class FakeResp:
        text = '{"worker": "task_router", "task_type": "code_change"}'

    class FakeModels:
        def generate_content(self, **kw):
            attempts["n"] += 1
            if attempts["n"] < 3:
                raise RuntimeError("429 rate limit exceeded")
            return FakeResp()

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(gp, "_make_client", lambda slot: FakeClient())
    start_slot = gp.current_key_slot()
    out = gp.generate_json("p", "task_router")
    assert out["task_type"] == "code_change"
    assert attempts["n"] == 3          # 2번 실패 후 성공
    assert len(sleeps) == 2            # 재시도 사이 backoff 2회
    assert sleeps[1] >= sleeps[0]      # exponential (감소하지 않음)
    assert gp.current_key_slot() != start_slot  # 429에서 키 회전
