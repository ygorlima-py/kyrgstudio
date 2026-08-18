from __future__ import annotations

import pytest

from app.settings import load_settings


def test_load_settings_reads_llm_temperature(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_LLM_TEMPERATURE", "0.35")

    settings = load_settings()

    assert settings.llm_temperature == 0.35


@pytest.mark.parametrize("value", ["not-a-number", "-0.1", "2.1"])
def test_load_settings_rejects_invalid_llm_temperature(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    monkeypatch.setenv("APP_LLM_TEMPERATURE", value)

    with pytest.raises(ValueError, match="APP_LLM_TEMPERATURE"):
        load_settings()


def test_load_settings_defaults_llm_temperature_to_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("APP_LLM_TEMPERATURE", raising=False)

    settings = load_settings()

    assert settings.llm_temperature == 0.0
