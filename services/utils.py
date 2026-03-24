from __future__ import annotations

import json
import logging
from typing import Any, Type

from pydantic import BaseModel


def safe_json(response) -> dict[str, Any] | list[Any] | dict[str, str]:
    try:
        return response.json()
    except Exception:  # noqa: BLE001
        return {"raw": response.text}


def total_log_in_method(response) -> None:
    payload = safe_json(response)
    logging.info(
        "status=%s payload=%s",
        response.status_code,
        json.dumps(payload, ensure_ascii=False),
    )


def validate_schema(schema: Type[BaseModel], payload: dict[str, Any] | list[Any]):
    return schema.model_validate(payload)


def assert_json_response(response) -> None:
    content_type = response.headers.get("Content-Type", "")
    assert "application/json" in content_type, (
        f"Expected JSON response, got Content-Type={content_type!r}, body={response.text!r}"
    )


def validate_status_code_and_body(response, schema: Type[BaseModel] | None, expected_status: int):
    assert response.status_code == expected_status, (
        f"Expected status {expected_status}, got {response.status_code}, body={response.text!r}"
    )
    payload = safe_json(response)
    if schema is not None:
        validate_schema(schema, payload)
    return payload
