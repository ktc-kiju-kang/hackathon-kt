"""LLM 오류 분류 → 사용자용 메시지·재시도 여부. 공급자(SDK)와 무관하게 동작한다."""

from dataclasses import dataclass


@dataclass(frozen=True)
class LLMError:
    code: str  # rate_limit | unavailable | bad_request | auth | internal
    message: str  # 화면에 그대로 보여줄 한국어 문구
    retryable: bool
    retry_after: float | None = None  # 서버가 알려준 대기 시간(초)


def classify(e: Exception) -> LLMError:
    status = getattr(e, "status_code", None)
    name = type(e).__name__
    retry_after = _retry_after(e)
    if status == 429 or "RateLimit" in name:
        return LLMError(
            "rate_limit",
            "LLM 사용량 한도에 걸렸어요. 잠시 후 다시 시도해 주세요.",
            True,
            retry_after,
        )
    if (status and status >= 500) or name in (
        "InternalServerError",
        "APIConnectionError",
        "APITimeoutError",
        "OverloadedError",
        "TimeoutError",
    ):
        return LLMError(
            "unavailable",
            "LLM 서버가 잠시 응답하지 않아요. 다시 시도해 주세요.",
            True,
            retry_after,
        )
    if status in (401, 403):
        return LLMError("auth", "LLM API 키 설정에 문제가 있어요. 관리자에게 알려주세요.", False)
    if status == 400 or "BadRequest" in name:
        return LLMError(
            "bad_request", "LLM이 요청을 처리하지 못했어요. 새 대화로 시도해 주세요.", False
        )
    return LLMError("internal", "답변을 만드는 중 오류가 났어요. 다시 시도해 주세요.", False)


def _retry_after(e: Exception) -> float | None:
    response = getattr(e, "response", None)
    headers = getattr(response, "headers", None)
    if not headers:
        return None
    try:
        return float(headers.get("retry-after", ""))
    except ValueError:
        return None
