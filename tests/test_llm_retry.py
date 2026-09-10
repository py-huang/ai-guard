from __future__ import annotations

from safety_gateway.playground.llm import (
    LlmBusyError,
    LlmFatalError,
    child_safe_llm_message,
    complete_with_failover,
)


class _Busy(RuntimeError):
    def __str__(self) -> str:
        return "503 UNAVAILABLE. This model is currently experiencing high demand."


class _Missing(RuntimeError):
    def __str__(self) -> str:
        return "404 NOT_FOUND. This model is no longer available to new users."


class _Auth(RuntimeError):
    def __str__(self) -> str:
        return "401 UNAUTHENTICATED. API key not valid."


def test_failover_retries_then_succeeds() -> None:
    calls: list[tuple[str, int]] = []
    sleeps: list[float] = []
    attempts = {"gemini-3.6-flash": 0}

    def generate(model: str) -> str:
        attempts[model] = attempts.get(model, 0) + 1
        calls.append((model, attempts[model]))
        if model == "gemini-3.6-flash" and attempts[model] < 3:
            raise _Busy()
        return "你好"

    text, model = complete_with_failover(
        generate,
        models=("gemini-3.6-flash", "gemini-3.5-flash"),
        max_attempts=3,
        backoff_seconds=0.5,
        sleeper=sleeps.append,
    )
    assert text == "你好"
    assert model == "gemini-3.6-flash"
    assert sleeps == [0.5, 1.0]


def test_failover_skips_missing_model_then_busy_raises_child_safe() -> None:
    def generate(model: str) -> str:
        if model == "gone":
            raise _Missing()
        raise _Busy()

    try:
        complete_with_failover(generate, models=("gone", "busy"), max_attempts=1, sleeper=lambda _: None)
    except LlmBusyError as exc:
        assert exc.retryable is True
        assert "忙" in str(exc)
        assert "503" not in child_safe_llm_message(exc)
        assert "UNAVAILABLE" not in child_safe_llm_message(exc)
    else:
        raise AssertionError("expected LlmBusyError")


def test_non_retryable_is_fatal_without_json_leak() -> None:
    def generate(_model: str) -> str:
        raise _Auth()

    try:
        complete_with_failover(generate, models=("gemini-3.6-flash",), max_attempts=2, sleeper=lambda _: None)
    except LlmFatalError as exc:
        assert exc.retryable is False
        assert "401" not in child_safe_llm_message(exc)
    else:
        raise AssertionError("expected LlmFatalError")


def test_policy_block_is_not_wrapped_as_busy_or_fatal() -> None:
    from safety_gateway.playground.llm import LlmPolicyBlockError

    def generate(_model: str) -> str:
        raise LlmPolicyBlockError()

    try:
        complete_with_failover(generate, models=("gemini-3.6-flash",), max_attempts=2, sleeper=lambda _: None)
    except LlmPolicyBlockError:
        return
    raise AssertionError("expected LlmPolicyBlockError")
