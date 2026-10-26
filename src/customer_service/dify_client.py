"""Dify Chatflow API client.

V1 only uses the blocking ``POST /chat-messages`` endpoint.  Keeping the
conversation id in LangGraph state is what allows a later turn to continue the
same Dify conversation.

The client deliberately owns the HTTP details (timeouts, retries, error
mapping) so graph nodes can stay small and testable.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Callable, Mapping, Sequence

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# 429/5xx are the only HTTP statuses we retry.  A retry of a chat message can
# create a duplicate message in Dify, so timeouts are opt-in via config.
_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


class DifyError(Exception):
    """Base class for all Dify integration errors."""

    category = "dify_error"

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code

    @property
    def retryable(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "message": str(self),
            "status_code": self.status_code,
            "code": self.code,
        }


class DifyConfigurationError(DifyError):
    category = "configuration"


class DifyAPIError(DifyError):
    category = "api"

    @property
    def retryable(self) -> bool:
        return self.status_code in _RETRYABLE_STATUS_CODES


class DifyTimeoutError(DifyError):
    category = "timeout"


class DifyConnectionError(DifyError):
    category = "connection"

    @property
    def retryable(self) -> bool:
        return True


class DifyResponseError(DifyError):
    category = "response"


@dataclass(frozen=True, slots=True)
class DifyConfig:
    """Runtime configuration read from environment variables."""

    api_url: str
    api_key: str
    timeout_seconds: float = 30.0
    max_retries: int = 1
    retry_backoff_seconds: float = 1.0
    retry_on_timeout: bool = False

    @classmethod
    def from_env(
        cls, env: Mapping[str, str] | None = None
    ) -> "DifyConfig":
        source = os.environ if env is None else env

        api_url = (source.get("DIFY_API_URL") or "").strip().rstrip("/")
        api_key = (source.get("DIFY_API_KEY") or "").strip()

        if not api_url or not api_key:
            raise DifyConfigurationError(
                "DIFY_API_URL and DIFY_API_KEY must be set; "
                "see .env.example for the required variables."
            )
        if not api_url.startswith(("http://", "https://")):
            raise DifyConfigurationError(
                "DIFY_API_URL must start with http:// or https://, "
                f"got {api_url!r}."
            )

        try:
            timeout_seconds = float(
                source.get("DIFY_TIMEOUT_SECONDS", "30")
            )
            max_retries = int(source.get("DIFY_MAX_RETRIES", "1"))
            retry_backoff_seconds = float(
                source.get("DIFY_RETRY_BACKOFF_SECONDS", "1")
            )
        except ValueError as exc:
            raise DifyConfigurationError(
                f"Invalid numeric Dify configuration: {exc}"
            ) from exc

        if timeout_seconds <= 0:
            raise DifyConfigurationError(
                "DIFY_TIMEOUT_SECONDS must be greater than 0."
            )
        if max_retries < 0:
            raise DifyConfigurationError(
                "DIFY_MAX_RETRIES must be 0 or greater."
            )
        if retry_backoff_seconds < 0:
            raise DifyConfigurationError(
                "DIFY_RETRY_BACKOFF_SECONDS must be 0 or greater."
            )

        retry_on_timeout = (
            source.get("DIFY_RETRY_ON_TIMEOUT", "false")
            .strip()
            .lower()
            in {"1", "true", "yes", "on"}
        )

        return cls(
            api_url=api_url,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            retry_backoff_seconds=retry_backoff_seconds,
            retry_on_timeout=retry_on_timeout,
        )


@dataclass(frozen=True, slots=True)
class DifyChatResult:
    """Normalised result of one blocking Dify chat turn."""

    answer: str
    conversation_id: str
    message_id: str
    task_id: str
    mode: str
    metadata: dict[str, Any]
    retriever_resources: list[dict[str, Any]]
    usage: dict[str, Any]
    latency_ms: float

    @classmethod
    def from_payload(
        cls, payload: Any, *, latency_ms: float
    ) -> "DifyChatResult":
        if not isinstance(payload, dict):
            raise DifyResponseError(
                "Dify returned a non-object JSON body."
            )

        # A streaming-style error event can still arrive with HTTP 200.
        if payload.get("event") == "error":
            code = payload.get("code") or payload.get("status")
            message = payload.get("message") or "Dify returned an error event."
            raise DifyAPIError(
                f"Dify error event: {message}",
                code=str(code) if code is not None else None,
            )

        answer = payload.get("answer")
        if not isinstance(answer, str):
            raise DifyResponseError(
                "Dify response is missing a string 'answer' field."
            )

        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}

        retriever_resources = (
            payload.get("retriever_resources")
            or metadata.get("retriever_resources")
            or []
        )
        if not isinstance(retriever_resources, list):
            retriever_resources = []

        usage = payload.get("usage") or metadata.get("usage") or {}
        if not isinstance(usage, dict):
            usage = {}

        return cls(
            answer=answer,
            conversation_id=str(payload.get("conversation_id") or ""),
            message_id=str(payload.get("message_id") or ""),
            task_id=str(payload.get("task_id") or ""),
            mode=str(payload.get("mode") or ""),
            metadata=metadata,
            retriever_resources=retriever_resources,
            usage=usage,
            latency_ms=latency_ms,
        )

    def to_dict(self) -> dict[str, Any]:
        """Compact form safe to keep in LangGraph state."""
        return {
            "answer": self.answer,
            "conversation_id": self.conversation_id,
            "message_id": self.message_id,
            "task_id": self.task_id,
            "mode": self.mode,
            "usage": self.usage,
            "retriever_resources": self.retriever_resources,
            "latency_ms": round(self.latency_ms, 2),
        }


class DifyClient:
    """Small synchronous client for the Dify Chatflow API."""

    def __init__(
        self,
        config: DifyConfig,
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.config = config
        self._sleep = sleep
        self._http = httpx.Client(
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Accept": "application/json",
            },
            timeout=httpx.Timeout(config.timeout_seconds),
            transport=transport,
        )

    def chat(
        self,
        *,
        query: str,
        user: str,
        conversation_id: str | None = None,
        inputs: Mapping[str, Any] | None = None,
        files: Sequence[Mapping[str, Any]] | None = None,
        auto_generate_name: bool = True,
    ) -> DifyChatResult:
        """Send one blocking message to the Dify Chatflow app.

        ``conversation_id`` is optional on the first turn.  Pass the id
        returned by Dify on later turns to preserve the chat context.
        """
        query = (query or "").strip()
        if not query:
            raise ValueError("query must be a non-empty string.")
        if not user:
            raise ValueError("user must be a non-empty string.")

        payload: dict[str, Any] = {
            "query": query,
            "inputs": dict(inputs or {}),
            "response_mode": "blocking",
            "user": user,
            "auto_generate_name": auto_generate_name,
        }
        if conversation_id:
            payload["conversation_id"] = conversation_id
        if files:
            payload["files"] = [dict(item) for item in files]

        started = time.perf_counter()
        response = self._post_with_retry("/chat-messages", payload)
        latency_ms = (time.perf_counter() - started) * 1000

        try:
            body = response.json()
        except ValueError as exc:
            raise DifyResponseError(
                "Dify returned a non-JSON response."
            ) from exc

        return DifyChatResult.from_payload(body, latency_ms=latency_ms)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "DifyClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _post_with_retry(
        self, path: str, payload: dict[str, Any]
    ) -> httpx.Response:
        url = f"{self.config.api_url}{path}"
        attempts = self.config.max_retries + 1
        last_error: DifyError | None = None

        for attempt in range(1, attempts + 1):
            try:
                response = self._http.post(url, json=payload)
            except httpx.TimeoutException as exc:
                last_error = DifyTimeoutError(
                    "Dify request timed out after "
                    f"{self.config.timeout_seconds:g}s."
                )
                if (
                    self.config.retry_on_timeout
                    and attempt < attempts
                ):
                    logger.warning(
                        "Dify timeout, retrying (attempt %d/%d)",
                        attempt,
                        attempts,
                    )
                    self._backoff(attempt)
                    continue
                raise last_error from exc
            except httpx.RequestError as exc:
                last_error = DifyConnectionError(
                    f"Could not connect to Dify: {exc}"
                )
                if attempt < attempts:
                    logger.warning(
                        "Dify connection error, retrying (attempt %d/%d)",
                        attempt,
                        attempts,
                    )
                    self._backoff(attempt)
                    continue
                raise last_error from exc

            if response.is_success:
                return response

            error = self._api_error(response)
            if error.retryable and attempt < attempts:
                logger.warning(
                    "Dify returned retryable HTTP %d, retrying "
                    "(attempt %d/%d)",
                    response.status_code,
                    attempt,
                    attempts,
                )
                last_error = error
                self._backoff(attempt)
                continue
            raise error

        # Defensive: the loop either returns or raises.
        if last_error is not None:
            raise last_error
        raise DifyError("Dify request failed without a specific error.")

    def _backoff(self, attempt: int) -> None:
        delay = self.config.retry_backoff_seconds * (2 ** (attempt - 1))
        if delay > 0:
            self._sleep(delay)

    @staticmethod
    def _api_error(response: httpx.Response) -> DifyAPIError:
        message = response.text[:500] or f"HTTP {response.status_code}"
        code: str | None = None

        try:
            body = response.json()
        except ValueError:
            body = None

        if isinstance(body, dict):
            raw_code = body.get("code")
            code = str(raw_code) if raw_code is not None else None
            raw_message = body.get("message")
            if raw_message:
                message = str(raw_message)

        return DifyAPIError(
            f"Dify API error {response.status_code} "
            f"({code or 'unknown'}): {message}",
            status_code=response.status_code,
            code=code,
        )


@lru_cache(maxsize=1)
def get_dify_client() -> DifyClient:
    """Return the process-wide Dify client (lazy, cached)."""
    return DifyClient(DifyConfig.from_env())


def reset_dify_client() -> None:
    """Clear the cached client; useful in tests or after env changes."""
    get_dify_client.cache_clear()
