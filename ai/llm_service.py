import json
import os
import time

import requests
from dotenv import load_dotenv

from utils.trace import record_llm_call


load_dotenv()


class LLMError(Exception):
    """LLM 服务统一异常。"""
    pass


def _get_llm_config():
    """读取并校验 LLM 配置。"""

    base_url = os.getenv("LLM_BASE_URL", "").strip().rstrip("/")
    api_key = os.getenv("LLM_API_KEY", "").strip()
    model = os.getenv("LLM_MODEL", "").strip()

    try:
        timeout = int(os.getenv("LLM_TIMEOUT", "60"))
    except ValueError as error:
        raise LLMError("LLM_TIMEOUT 必须是整数。") from error

    if not base_url:
        raise LLMError("未配置 LLM_BASE_URL。")

    if not api_key:
        raise LLMError("未配置 LLM_API_KEY。")

    if not model:
        raise LLMError("未配置 LLM_MODEL。")

    if not base_url.startswith(("http://", "https://")):
        raise LLMError("LLM_BASE_URL 必须以 http:// 或 https:// 开头。")

    if timeout <= 0:
        raise LLMError("LLM_TIMEOUT 必须大于 0。")

    return {
        "base_url": base_url,
        "api_key": api_key,
        "model": model,
        "timeout": timeout,
    }


def chat_completion(messages, temperature=0.1, max_tokens=None):

    """
    调用 OpenAI 兼容 Chat Completions 接口。

    参数：
        messages: 对话消息列表
        temperature: 模型生成随机性
        max_tokens: 最大生成 Token 数，可选

    返回：
        content: 模型生成的文本
        model: 实际返回的模型名称
        usage: Token 使用情况
        elapsed_ms: 请求耗时
        request_id: 请求 ID
    """

    if not isinstance(messages, list) or not messages:
        raise LLMError("messages 必须是非空列表。")

    for message in messages:
        if not isinstance(message, dict):
            raise LLMError("messages 中的每一项必须是字典。")

        if message.get("role") not in {
            "system", "user", "assistant"
        }:
            raise LLMError("消息 role 不合法。")

        if not isinstance(message.get("content"), str):
            raise LLMError("当前服务层只支持文本 content。")

    if not isinstance(temperature, (int, float)):
        raise LLMError("temperature 必须是数字。")

    if not 0 <= temperature <= 2:
        raise LLMError("temperature 必须在 0 到 2 之间。")

    if max_tokens is not None:
        if not isinstance(max_tokens, int) or max_tokens <= 0:
            raise LLMError("max_tokens 必须是正整数。")

    config = _get_llm_config()

    url = f"{config['base_url']}/chat/completions"

    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": config["model"],
        "messages": messages,
        "temperature": temperature,
    }

    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    start_time = time.perf_counter()

    def record_failure(error):
        record_llm_call({
            "model": config["model"],
            "status": "failed",
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
            "elapsed_ms": round(
                (time.perf_counter() - start_time) * 1000,
                2,
            ),
            "request_id": None,
            "error": str(error),
        })

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=config["timeout"],
        )

        response.raise_for_status()

    except requests.exceptions.Timeout as error:
        record_failure(error)
        raise LLMError("LLM 请求超时，请检查网络或调整超时时间。") from error

    except requests.exceptions.HTTPError as error:
        status_code = error.response.status_code
        error_detail = error.response.text[:1000]

        record_failure(error)
        raise LLMError(
            f"LLM API 返回 HTTP {status_code}: {error_detail}"
        ) from error

    except requests.exceptions.RequestException as error:
        record_failure(error)
        raise LLMError(f"LLM 网络请求失败：{error}") from error

    elapsed_ms = round(
        (time.perf_counter() - start_time) * 1000,
        2,
    )

    try:
        result = response.json()

        content = result["choices"][0]["message"]["content"]

        if not isinstance(content, str) or not content.strip():
            raise ValueError("模型返回了空文本。")

    except (ValueError, KeyError, IndexError, TypeError) as error:
        record_failure(error)
        raise LLMError(
            f"LLM 响应格式不符合预期：{error}"
        ) from error

    usage = result.get("usage") or {}

    record_llm_call({
        "model": result.get("model", config["model"]),
        "status": "success",
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "elapsed_ms": elapsed_ms,
        "request_id": (
            response.headers.get("x-request-id")
            or result.get("id")
        ),
        "error": None,
    })

    return {
        "content": content.strip(),
        "model": result.get("model", config["model"]),
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
        },
        "elapsed_ms": elapsed_ms,
        "request_id": (
            response.headers.get("x-request-id")
            or result.get("id")
        ),
    }

def chat_completion_json(
    messages,
    temperature=0.1,
    max_tokens=None,
):
    """
    调用 LLM，并将模型返回内容解析为 JSON。

    返回：
        Python dict 或 list
    """

    if not isinstance(messages, list) or not messages:
        raise LLMError("messages 必须是非空列表。")

    json_instruction = (
        "请严格按照 JSON 格式返回结果。"
        "不要使用 Markdown 代码块。"
        "不要在 JSON 前后添加解释性文字。"
        "确保返回内容是合法、完整的 JSON。"
    )

    prepared_messages = [message.copy() for message in messages]

    # 如果已有 system 消息，就在原有指令后追加 JSON 规则。
    if prepared_messages[0].get("role") == "system":
        prepared_messages[0]["content"] += "\n" + json_instruction
    else:
        prepared_messages.insert(
            0,
            {
                "role": "system",
                "content": json_instruction,
            },
        )

    result = chat_completion(
        messages=prepared_messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    content = result["content"]

    try:
        parsed_result = json.loads(content)

    except json.JSONDecodeError as error:
        raise LLMError(
            f"模型返回的内容不是合法 JSON：{error}"
        ) from error

    if not isinstance(parsed_result, (dict, list)):
        raise LLMError(
            "模型返回的 JSON 顶层必须是对象或数组。"
        )

    return {
        "data": parsed_result,
        "model": result["model"],
        "usage": result["usage"],
        "elapsed_ms": result["elapsed_ms"],
        "request_id": result["request_id"],
    }