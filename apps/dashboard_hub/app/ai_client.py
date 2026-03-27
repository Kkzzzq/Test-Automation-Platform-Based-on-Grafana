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
        panel_titles: list[str],
        panel_payloads: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not self.api_key:
            raise AIClientError("AI_API_KEY is empty")

        prompt = self._build_prompt(
            title=title,
            tags=tags,
            panel_titles=panel_titles,
            panel_payloads=panel_payloads,
        )

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
                            "你会根据 dashboard 标题、标签，以及 panel 的完整配置数据生成中文摘要。"
                            "你只能基于给定内容总结，不能编造不存在的信息。"
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
    def _build_prompt(
        *,
        title: str,
        tags: list[str],
        panel_titles: list[str],
        panel_payloads: list[dict[str, Any]],
    ) -> str:
        safe_title = title or "未命名 dashboard"
        safe_tags = "、".join(tags[:8]) if tags else "无"
        safe_panel_titles = "、".join(panel_titles[:10]) if panel_titles else "无"

        panel_blocks: list[str] = []
        for index, panel in enumerate(panel_payloads, start=1):
            panel_blocks.append(
                f"panel_{index}:\n{panel['panel_json']}"
            )

        panel_context = "\n\n".join(panel_blocks) if panel_blocks else "无"

        return (
            "请根据下面 dashboard 信息生成一段中文摘要。\n"
            "要求：\n"
            f"1. 不超过 {AI_MAX_SUMMARY_CHARS} 个字\n"
            "2. 不要编造不存在的信息\n"
            "3. 优先总结 dashboard 主要关注的监控对象、指标主题和面板结构\n"
            "4. 如果 panel 数据显示为空或没有实际监控内容，可以明确说明\n\n"
            f"title: {safe_title}\n"
            f"tags: {safe_tags}\n"
            f"panel_titles: {safe_panel_titles}\n\n"
            "下面是用于摘要的 panel 完整数据（已限制为前几个核心 panel）：\n"
            f"{panel_context}\n"
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
