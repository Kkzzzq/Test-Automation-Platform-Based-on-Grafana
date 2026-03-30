from __future__ import annotations

from typing import Any


def build_case_state(replay_result: dict[str, Any] | None) -> dict[str, Any]:
    if not replay_result:
        return {"replay_status": "not_replayed", "chain_status": None}

    execution_error = replay_result.get("execution_error")
    if execution_error:
        if "unsupported failed test replay" in str(execution_error):
            return {"replay_status": "unsupported_test", "chain_status": "interrupted"}
        return {"replay_status": "replay_failed", "chain_status": "interrupted"}

    if replay_result.get("reproduced_original_failure"):
        return {"replay_status": "reproduced_original_failure", "chain_status": replay_result.get("chain_status")}

    if replay_result.get("first_abnormal_stage"):
        return {"replay_status": "not_reproduced_but_new_error", "chain_status": replay_result.get("chain_status")}

    return {"replay_status": "not_reproduced", "chain_status": replay_result.get("chain_status")}
