from __future__ import annotations

from typing import Any

import requests

from app.config import (
    AI_API_KEY,
    AI_BASE_URL,
    AI_MAX_SUMMARY_CHARS,
    AI_MODEL,
    AI_PROMPT_VERSION,
    AI_PROVIDER,
    AI_TIMEOUT_SECONDS,
)


class AIClientError(RuntimeError):
    pass


class AIClient:
    def __init__(self) -> None:
        self.provider = AI_PROVIDER
        self.base_url = self._normalize_base_url(AI_BASE_URL)
        self.api_key = AI_API_KEY
        self.model = AI_MODEL
        self.timeout = AI_TIMEOUT_SECONDS
        self.prompt_version = AI_PROMPT_VERSION

    @staticmethod
    def _normalize_base_url(base_url: str) -> str:
        base = (base_url or "").rstrip("/")
        if not base:
            raise AIClientError("AI_BASE_URL is empty")
        if not base.endswith("/v1"):
            base = f"{base}/v1"
        return base

    def summarize_dashboard(
        self,
        *,
        title: str,
        tags: list[str],
        panels: list[str],
    ) -> dict[str, Any]:
        if not self.api_key:
            raise AIClientError("AI_API_KEY is empty")

        prompt = self._build_prompt(title=title, tags=tags, panels=panels)

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "temperature": 0.2,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "你是监控平台 Dashboard 摘要助手。"
                            "你只能根据给定信息生成一句中文摘要，"
                            "不能编造不存在的内容。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
            },
            timeout=self.timeout,
        )

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise AIClientError(f"AI request failed: {response.status_code} {response.text}") from exc

        payload = response.json()
        ai_summary = self._extract_content(payload)

        return {
            "ai_summary": ai_summary,
            "provider": self.provider,
            "model": self.model,
            "prompt_version": self.prompt_version,
        }

    @staticmethod
    def _build_prompt(*, title: str, tags: list[str], panels: list[str]) -> str:
        safe_title = title or "未命名 dashboard"
        safe_tags = "、".join(tags[:8]) if tags else "无"
        safe_panels = "、".join(panels[:10]) if panels else "无"

        return (
            "请根据下面 dashboard 信息生成一句简洁摘要。\n"
            f"要求：\n"
            f"1. 使用中文\n"
            f"2. 不超过 {AI_MAX_SUMMARY_CHARS} 个字\n"
            f"3. 不要编造不存在的信息\n"
            f"4. 尽量点出主要监控对象或指标\n\n"
            f"title: {safe_title}\n"
            f"tags: {safe_tags}\n"
            f"panels: {safe_panels}\n"
        )

    @staticmethod
    def _extract_content(payload: dict[str, Any]) -> str:
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIClientError(f"unexpected AI response: {payload}") from exc

        if not isinstance(content, str):
            raise AIClientError(f"AI content is not string: {content!r}")

        normalized = " ".join(content.split()).strip().strip('"').strip("'")
        if not normalized:
            raise AIClientError("AI content is empty")

        return normalized[:AI_MAX_SUMMARY_CHARS]
