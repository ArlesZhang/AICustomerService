import json

import httpx
import pytest

from src.customer_service.dify_client import (
    DifyAPIError,
    DifyClient,
    DifyConfig,
    DifyConfigurationError,
    DifyResponseError,
    DifyTimeoutError,
)


def make_config(**overrides) -> DifyConfig:
    values = {
        "api_url": "https://dify.example/v1",
        "api_key": "app-test",
        "timeout_seconds": 5,
        "max_retries": 1,
        "retry_backoff_seconds": 0,
        "retry_on_timeout": False,
    }
    values.update(overrides)
    return DifyConfig(**values)


def success_payload(
    answer: str = "退款到账时间以退款页面为准。",
) -> dict:
    return {
        "event": "message",
        "task_id": "task-1",
        "id": "id-1",
        "message_id": "msg-1",
        "conversation_id": "conv-2",
        "mode": "advanced-chat",
        "answer": answer,
        "metadata": {
            "usage": {"total_tokens": 42, "latency": 1.2},
            "retriever_resources": [{"document_id": "doc-1"}],
        },
    }


def make_client(handler, config: DifyConfig | None = None):
    sleeps: list[float] = []
    client = DifyClient(
        config or make_config(),
        transport=httpx.MockTransport(handler),
        sleep=sleeps.append,
    )
    return client, sleeps


def test_chat_sends_expected_request_and_parses_response():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers["authorization"]
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200, json=success_payload(), request=request
        )

    client, sleeps = make_client(handler)
    result = client.chat(
        query="  退款多久到账？  ",
        user="user-001",
        conversation_id="conv-1",
        inputs={"channel": "web"},
    )

    assert captured["url"] == (
        "https://dify.example/v1/chat-messages"
    )
    assert captured["auth"] == "Bearer app-test"
    assert captured["body"] == {
        "query": "退款多久到账？",
        "inputs": {"channel": "web"},
        "response_mode": "blocking",
        "user": "user-001",
        "auto_generate_name": True,
        "conversation_id": "conv-1",
    }
    assert result.answer == "退款到账时间以退款页面为准。"
    assert result.conversation_id == "conv-2"
    assert result.message_id == "msg-1"
    assert result.usage["total_tokens"] == 42
    assert result.retriever_resources == [{"document_id": "doc-1"}]
    assert result.latency_ms >= 0
    assert sleeps == []


def test_chat_omits_empty_conversation_id():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200, json=success_payload(), request=request
        )

    client, _ = make_client(handler)
    client.chat(query="hello", user="user-001")

    assert "conversation_id" not in captured["body"]


def test_chat_retries_retryable_http_error():
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(
                500,
                json={
                    "code": "completion_request_error",
                    "message": "boom",
                },
                request=request,
            )
        return httpx.Response(
            200, json=success_payload(), request=request
        )

    client, sleeps = make_client(
        handler, make_config(retry_backoff_seconds=0.5)
    )
    result = client.chat(query="hi", user="user-001")

    assert result.answer
    assert len(calls) == 2
    assert sleeps == [0.5]


def test_chat_does_not_retry_unauthorized():
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(
            401,
            json={"code": "unauthorized", "message": "bad key"},
            request=request,
        )

    client, sleeps = make_client(handler)

    with pytest.raises(DifyAPIError) as exc_info:
        client.chat(query="hi", user="user-001")

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "unauthorized"
    assert not exc_info.value.retryable
    assert len(calls) == 1
    assert sleeps == []


def test_chat_timeout_not_retried_by_default():
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        raise httpx.ReadTimeout("slow", request=request)

    client, _ = make_client(handler, make_config(max_retries=2))

    with pytest.raises(DifyTimeoutError):
        client.chat(query="hi", user="user-001")

    assert len(calls) == 1


def test_chat_timeout_retried_when_enabled():
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            raise httpx.ReadTimeout("slow", request=request)
        return httpx.Response(
            200, json=success_payload(), request=request
        )

    client, sleeps = make_client(
        handler,
        make_config(
            max_retries=1,
            retry_backoff_seconds=0.5,
            retry_on_timeout=True,
        ),
    )
    result = client.chat(query="hi", user="user-001")

    assert result.answer
    assert len(calls) == 2
    assert sleeps == [0.5]


def test_chat_rejects_response_without_answer():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"conversation_id": "conv-1"},
            request=request,
        )

    client, _ = make_client(handler)

    with pytest.raises(DifyResponseError):
        client.chat(query="hi", user="user-001")


def test_chat_rejects_non_json_response():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, content=b"<html>not json</html>", request=request
        )

    client, _ = make_client(handler)

    with pytest.raises(DifyResponseError):
        client.chat(query="hi", user="user-001")


def test_chat_raises_on_error_event():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "event": "error",
                "code": "workflow_error",
                "message": "node failed",
            },
            request=request,
        )

    client, _ = make_client(handler)

    with pytest.raises(DifyAPIError) as exc_info:
        client.chat(query="hi", user="user-001")

    assert exc_info.value.code == "workflow_error"


def test_config_requires_credentials():
    with pytest.raises(DifyConfigurationError):
        DifyConfig.from_env({})


def test_config_rejects_invalid_url():
    with pytest.raises(DifyConfigurationError):
        DifyConfig.from_env(
            {
                "DIFY_API_URL": "dify.example/v1",
                "DIFY_API_KEY": "app-test",
            }
        )


def test_config_reads_and_normalises_env():
    config = DifyConfig.from_env(
        {
            "DIFY_API_URL": "https://dify.example/v1/",
            "DIFY_API_KEY": "app-test",
            "DIFY_TIMEOUT_SECONDS": "12",
            "DIFY_MAX_RETRIES": "0",
            "DIFY_RETRY_BACKOFF_SECONDS": "0.5",
            "DIFY_RETRY_ON_TIMEOUT": "true",
        }
    )

    assert config.api_url == "https://dify.example/v1"
    assert config.timeout_seconds == 12
    assert config.max_retries == 0
    assert config.retry_backoff_seconds == 0.5
    assert config.retry_on_timeout is True
