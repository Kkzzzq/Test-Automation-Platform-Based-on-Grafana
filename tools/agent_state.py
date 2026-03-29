from __future__ import annotations

from typing import Any


def evaluate_evidence_status(replay_result: dict[str, Any] | None) -> str:
    if not replay_result:
        return "insufficient"

    evidence_points = 0
    if replay_result.get("http_steps"):
        evidence_points += 1
    if replay_result.get("snapshot", {}).get("before") or replay_result.get("snapshot", {}).get("after"):
        evidence_points += 1
    if replay_result.get("snapshot", {}).get("diff"):
        evidence_points += 1
    if replay_result.get("intermediate"):
        evidence_points += 1
    if replay_result.get("snapshot", {}).get("after", {}).get("service_logs", {}).get("items"):
        evidence_points += 1

    if evidence_points >= 4:
        return "sufficient"
    if evidence_points >= 2:
        return "partial"
    return "insufficient"


def evaluate_replay_status(replay_result: dict[str, Any] | None) -> str:
    if not replay_result:
        return "not_replayed"
    if replay_result.get("execution_error"):
        if "unsupported failed test replay" in str(replay_result.get("execution_error", "")):
            return "unsupported_test"
        return "replay_failed"
    if replay_result.get("failure_reproduced"):
        return "reproduced"
    return "not_reproduced"


def evaluate_diagnosis_status(replay_status: str, evidence_status: str) -> str:
    if replay_status in {"unsupported_test", "replay_failed"}:
        return "manual_check_required"
    if replay_status == "reproduced" and evidence_status == "sufficient":
        return "high_confidence"
    if replay_status == "reproduced" and evidence_status == "partial":
        return "medium_confidence"
    if replay_status == "not_reproduced" and evidence_status in {"sufficient", "partial"}:
        return "low_confidence"
    return "manual_check_required"


def build_case_state(replay_result: dict[str, Any] | None) -> dict[str, Any]:
    replay_status = evaluate_replay_status(replay_result)
    evidence_status = evaluate_evidence_status(replay_result)
    diagnosis_status = evaluate_diagnosis_status(replay_status, evidence_status)
    return {
        "replay_status": replay_status,
        "evidence_status": evidence_status,
        "diagnosis_status": diagnosis_status,
    }
