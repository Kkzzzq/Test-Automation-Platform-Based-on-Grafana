from __future__ import annotations

import json
import os
from urllib import error, request

AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
AI_MODEL = os.getenv("AI_MODEL", "deepseek-chat")
AI_TIMEOUT_SECONDS = int(os.getenv("AI_TIMEOUT_SECONDS", "180"))


def _build_prompt(payload: dict) -> str:
    return (
        "你是测试故障复现与排障助手。\n"
        "下面只提供运行时观测证据，不提供问题层预判、排查建议或结论。\n"
        "请仅基于这些证据做中文 Markdown 诊断总结。\n\n"
        "要求：\n"
        "- 先写观测事实，再写推断结论\n"
        "- 明确区分‘已观测到’和‘推断认为’\n"
        "- 如果证据不足，必须直接说明证据不足\n"
        "- 优先引用 HTTP 步骤、快照 diff、结构化日志\n"
        "- 不要把推断写成确定事实\n\n"
        f"输入数据：\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def maybe_generate_ai_summary(payload: dict) -> str | None:
    if not AI_API_KEY:
        return None

    req_payload = {
        "model": AI_MODEL,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": "你是测试故障复现与排障助手。"},
            {"role": "user", "content": _build_prompt(payload)},
        ],
    }

    req = request.Request(
        f"{AI_BASE_URL}/chat/completions",
        data=json.dumps(req_payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {AI_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=AI_TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8")
    except error.HTTPError:
        return None
    except Exception:
        return None

    try:
        payload = json.loads(raw)
        return payload["choices"][0]["message"]["content"].strip()
    except Exception:
        return None
