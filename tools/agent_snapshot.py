from __future__ import annotations

from typing import Any

from tools.agent_evidence import (
    collect_metrics_snapshot,
    collect_service_log_snapshot,
    collect_share_link_snapshot,
    collect_subscription_snapshot,
    collect_summary_snapshot,
    diff_metrics,
)

SUBSCRIPTION_TESTS = {
    "test_create_subscription_success",
    "test_get_subscriptions_success",
    "test_create_duplicate_subscription",
    "test_create_subscription_with_unknown_dashboard",
    "test_create_subscription_with_illegal_channel",
    "test_subscription_written_to_mysql",
    "test_subscriptions_are_cached_and_invalidated",
}

SHARE_TESTS = {
    "test_create_share_link_success",
    "test_get_share_link_success",
    "test_get_unknown_share_token",
    "test_get_expired_share_link",
    "test_share_link_written_to_mysql_and_view_count_updated",
    "test_share_link_is_cached_and_invalidated",
}

SUMMARY_TESTS = {
    "test_get_dashboard_summary_success",
    "test_dashboard_summary_is_cached",
}


def capture_snapshot(replay_target: str, runtime: dict[str, Any]) -> dict[str, Any]:
    snapshot: dict[str, Any] = {"metrics": collect_metrics_snapshot()}

    replay_id = runtime.get("replay_id")
    if replay_id:
        snapshot["service_logs"] = collect_service_log_snapshot(replay_id=replay_id)

    if replay_target in SUBSCRIPTION_TESTS and all(
        runtime.get(key) is not None for key in ("dashboard_uid", "user_login", "channel")
    ):
        snapshot["subscription"] = collect_subscription_snapshot(
            dashboard_uid=runtime["dashboard_uid"],
            user_login=runtime["user_login"],
            channel=runtime["channel"],
            subscription_id=runtime.get("subscription_id"),
        )

    if replay_target in SHARE_TESTS and runtime.get("token"):
        snapshot["share_link"] = collect_share_link_snapshot(runtime["token"])

    if replay_target in SUMMARY_TESTS and runtime.get("dashboard_uid"):
        snapshot["summary"] = collect_summary_snapshot(
            dashboard_uid=runtime["dashboard_uid"],
            summary_key=runtime.get("summary_key"),
        )

    return snapshot


def diff_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    diff: dict[str, Any] = {}
    for key in sorted(set(before) | set(after)):
        before_value = before.get(key)
        after_value = after.get(key)
        if key == "metrics":
            before_metrics = (before_value or {}).get("parsed", {})
            after_metrics = (after_value or {}).get("parsed", {})
            metric_diff = diff_metrics(before_metrics, after_metrics)
            if metric_diff:
                diff[key] = metric_diff
            continue
        if before_value != after_value:
            diff[key] = {"before": before_value, "after": after_value}
    return diff
