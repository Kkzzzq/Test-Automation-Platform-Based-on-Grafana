from __future__ import annotations

from typing import Any


def _status_map(http_steps: list[dict[str, Any]]) -> dict[str, int]:
    return {str(step.get("step")): int(step.get("status_code", 0)) for step in http_steps if step.get("step")}


def _expected_map(http_steps: list[dict[str, Any]]) -> dict[str, Any]:
    return {str(step.get("step")): step.get("expected_status") for step in http_steps if step.get("step")}


def _log_events(snapshot: dict[str, Any]) -> set[str]:
    items = snapshot.get("after", {}).get("service_logs", {}).get("items", []) or []
    events: set[str] = set()
    for item in items:
        event = item.get("event")
        if isinstance(event, str) and event:
            events.add(event)
    return events


def _present(value: Any) -> bool:
    return value is not None


def _bool_text(flag: bool | None, yes: str, no: str) -> str | None:
    if flag is True:
        return yes
    if flag is False:
        return no
    return None


def _summarize_scope(first_abnormal_stage: str | None) -> tuple[list[str], list[str]]:
    remaining_map = {
        "request_validation": ["请求接收与参数校验段"],
        "main_state_write": ["主状态写入段", "写入后的持久化一致性检查段"],
        "main_state_delete": ["主状态删除段", "删除提交后的持久化一致性检查段"],
        "list_payload_consistency": ["订阅列表读取结果构造段"],
        "cache_fill_after_read": ["读取后的缓存写入段"],
        "cache_invalidation_after_delete": ["删除后的缓存失效段"],
        "share_read_consistency": ["分享链接读取与视图计数更新段"],
        "summary_generation": ["摘要生成段"],
        "summary_cache_write": ["摘要读取后的缓存写入段"],
        "negative_side_effect_absence": ["负向请求后的无副作用保障段"],
        "replay_execution": ["agent 重放执行段"],
    }
    manual_map = {
        "request_validation": [
            "检查接口入参、鉴权与状态码分支是否按预期返回。",
            "核对服务端结构化日志里的 started/finished/error 事件是否完整。",
        ],
        "main_state_write": [
            "检查写库语句是否真正提交，以及关键字段是否与请求一致。",
            "核对写入成功后的结构化日志和数据库实际记录是否一致。",
        ],
        "main_state_delete": [
            "检查删除逻辑是否真正执行到 db.commit 之后。",
            "核对删除后主记录是否仍残留，以及是否存在提前 return 或吞异常。",
        ],
        "list_payload_consistency": [
            "检查列表查询结果构造是否漏掉刚创建的主记录。",
            "核对查询排序、过滤条件和返回 payload 组装逻辑。",
        ],
        "cache_fill_after_read": [
            "检查读取成功后是否执行缓存写入。",
            "核对 cache key 计算与 payload 结构是否正确。",
        ],
        "cache_invalidation_after_delete": [
            "检查 delete 成功后是否执行 cache.delete。",
            "核对删除路径里的 cache invalidated 结构化日志是否缺失。",
            "检查删除路径是否在删缓存前提前结束。",
        ],
        "share_read_consistency": [
            "检查分享链接读取后 view_count 是否更新并提交。",
            "核对缓存命中/回源路径下 view_count 更新是否一致。",
        ],
        "summary_generation": [
            "检查摘要生成路径是否返回 ai_summary，以及 source/provider/model 是否合理。",
            "核对 AI/fallback 分支日志与最终返回 payload 是否一致。",
        ],
        "summary_cache_write": [
            "检查摘要读取成功后是否执行 summary cache 写入。",
            "核对 summary cache key 与 payload 内容是否一致。",
        ],
        "negative_side_effect_absence": [
            "检查负向请求返回错误后是否仍误写数据库或缓存。",
            "核对错误分支里是否存在多余的副作用动作。",
        ],
        "replay_execution": [
            "先人工确认该失败是否属于当前已支持的失败用例重放范围。",
            "检查 agent 重放环境、测试数据准备和清理流程。",
        ],
    }
    return remaining_map.get(first_abnormal_stage or "", []), manual_map.get(first_abnormal_stage or "", [])


def _default_analysis(replay_result: dict[str, Any], facts: dict[str, Any]) -> dict[str, Any]:
    execution_error = replay_result.get("execution_error")
    if execution_error:
        return {
            "facts": facts,
            "stage_results": {},
            "reproduced_original_failure": False,
            "chain_status": "interrupted",
            "first_abnormal_stage": "replay_execution",
            "suspected_segment": "agent replay execution",
            "confirmed_facts": [f"重放执行异常：{execution_error}"],
            "excluded_scope": [],
            "remaining_scope": ["agent 重放执行段"],
            "manual_checks": [
                "先确认该失败是否属于当前已支持的失败用例重放范围。",
                "检查 agent 重放环境、测试数据准备和清理流程。",
            ],
        }

    first_abnormal_stage = None
    for step in replay_result.get("http_steps", []):
        status_code = step.get("status_code")
        expected_status = step.get("expected_status")
        if isinstance(expected_status, tuple):
            ok = status_code in expected_status
        else:
            ok = status_code == expected_status
        if not ok:
            first_abnormal_stage = "request_validation"
            break

    confirmed_facts = []
    for step in replay_result.get("http_steps", []):
        confirmed_facts.append(
            f"{step.get('step')} 返回 {step.get('status_code')}，预期 {step.get('expected_status')}"
        )
    remaining_scope, manual_checks = _summarize_scope(first_abnormal_stage)
    return {
        "facts": facts,
        "stage_results": {},
        "reproduced_original_failure": first_abnormal_stage is not None,
        "chain_status": "complete",
        "first_abnormal_stage": first_abnormal_stage,
        "suspected_segment": "request validation" if first_abnormal_stage else None,
        "confirmed_facts": confirmed_facts,
        "excluded_scope": [],
        "remaining_scope": remaining_scope,
        "manual_checks": manual_checks,
    }


def _extract_facts(replay_result: dict[str, Any]) -> dict[str, Any]:
    http_steps = replay_result.get("http_steps", []) or []
    status_map = _status_map(http_steps)
    expected_map = _expected_map(http_steps)
    snapshot = replay_result.get("snapshot", {}) or {}
    after = snapshot.get("after", {}) or {}
    intermediate = replay_result.get("intermediate", {}) or {}
    log_events = _log_events(snapshot)

    facts: dict[str, Any] = {
        "status_by_step": status_map,
        "expected_by_step": expected_map,
        "service_log_events": sorted(log_events),
    }

    facts["create_status"] = status_map.get("create_subscription") or status_map.get("create_share_link")
    facts["list_status"] = status_map.get("list_subscriptions")
    facts["get_status"] = status_map.get("get_share_link")
    facts["summary_status"] = status_map.get("get_dashboard_summary")
    facts["delete_status"] = status_map.get("delete_subscription") or status_map.get("delete_share_link")
    facts["first_create_status"] = status_map.get("create_subscription_first")
    facts["second_create_status"] = status_map.get("create_subscription_second")
    facts["unknown_dashboard_status"] = status_map.get("create_subscription_unknown_dashboard")
    facts["invalid_channel_status"] = status_map.get("create_subscription_invalid_channel")
    facts["unknown_share_status"] = status_map.get("get_unknown_share_token")
    facts["expired_share_status"] = status_map.get("get_expired_share_link")

    subscription_after = after.get("subscription", {}) or {}
    share_after = after.get("share_link", {}) or {}
    summary_after = after.get("summary", {}) or {}

    facts["subscription_business_key_count_after"] = subscription_after.get("business_key_count")
    facts["subscription_row_after_present"] = _present(subscription_after.get("subscription_row"))
    facts["subscription_cache_exists_after"] = subscription_after.get("cache_exists")
    facts["share_row_after_present"] = _present(share_after.get("mysql_row"))
    facts["share_cache_exists_after"] = share_after.get("cache_exists")
    facts["summary_cache_exists_after"] = summary_after.get("cache_exists")
    facts["summary_cache_payload_after_present"] = _present(summary_after.get("cache_payload"))

    facts["cache_payload_after_list_present"] = _present(intermediate.get("cache_payload_after_list"))
    facts["cache_payload_after_read_present"] = _present(intermediate.get("cache_payload_after_read"))
    facts["list_payload_present"] = _present(intermediate.get("list_payload"))
    facts["db_row_after_create_present"] = _present(intermediate.get("db_row_after_create"))
    facts["db_row_after_get_present"] = _present(intermediate.get("db_row_after_get"))
    facts["summary_response_present"] = _present(intermediate.get("summary_response"))

    list_payload = intermediate.get("list_payload") or {}
    runtime = replay_result.get("runtime", {}) or {}
    subscription_id = runtime.get("subscription_id")
    if subscription_id is not None and isinstance(list_payload, dict):
        items = list_payload.get("items", []) or []
        facts["created_subscription_present_in_list"] = any(item.get("id") == subscription_id for item in items)

    created_row = intermediate.get("db_row_after_create") or {}
    row_after_get = intermediate.get("db_row_after_get") or {}
    facts["db_row_after_create_dashboard_uid_matches"] = created_row.get("dashboard_uid") == runtime.get("dashboard_uid") if created_row else None
    facts["db_row_after_create_user_login_matches"] = created_row.get("user_login") == runtime.get("user_login") if created_row else None
    facts["db_row_after_create_channel_matches"] = created_row.get("channel") == runtime.get("channel") if created_row else None
    facts["share_row_after_create_dashboard_uid_matches"] = created_row.get("dashboard_uid") == runtime.get("dashboard_uid") if created_row else None
    facts["share_row_initial_view_count_zero"] = int(created_row.get("view_count", -1)) == 0 if created_row else None
    facts["share_row_view_count_advanced_after_get"] = int(row_after_get.get("view_count", 0)) >= 1 if row_after_get else None

    summary_response = intermediate.get("summary_response") or {}
    summary_cache_payload = summary_after.get("cache_payload") or {}
    if summary_response and summary_cache_payload:
        facts["summary_payload_matches_after_read"] = summary_cache_payload.get("ai_summary") == summary_response.get("ai_summary")
    else:
        facts["summary_payload_matches_after_read"] = None
    facts["summary_source_valid"] = summary_response.get("source") in {"ai", "fallback"} if summary_response else None

    facts["service_log_subscription_delete_db_committed_seen"] = "subscription_delete_db_committed" in log_events
    facts["service_log_subscription_delete_cache_invalidated_seen"] = "subscription_delete_cache_invalidated" in log_events
    facts["service_log_subscription_list_cache_populated_seen"] = "subscription_list_cache_populated" in log_events
    facts["service_log_share_link_delete_cache_invalidated_seen"] = "share_link_delete_cache_invalidated" in log_events
    facts["service_log_share_link_delete_finished_seen"] = "share_link_delete_finished" in log_events
    facts["service_log_summary_cache_populated_seen"] = "summary_cache_populated" in log_events
    facts["service_log_summary_ai_request_failed_seen"] = "summary_ai_request_failed" in log_events

    return facts


def _first_failed(stages: list[tuple[str, bool]]) -> str | None:
    for name, ok in stages:
        if not ok:
            return name
    return None


def _filtered_texts(*items: str | None) -> list[str]:
    return [item for item in items if item]


def _analyze_subscriptions_are_cached_and_invalidated(facts: dict[str, Any]) -> dict[str, Any]:
    create_ok = facts.get("create_status") == 201
    list_ok = facts.get("list_status") == 200
    delete_ok = facts.get("delete_status") == 200
    cache_fill_ok = facts.get("cache_payload_after_list_present") is True
    delete_db_ok = facts.get("subscription_business_key_count_after") in (0, None)
    cache_invalidation_ok = facts.get("subscription_cache_exists_after") is False
    stages = [
        ("main_state_write", create_ok),
        ("cache_fill_after_read", list_ok and cache_fill_ok),
        ("main_state_delete", delete_ok and delete_db_ok),
        ("cache_invalidation_after_delete", cache_invalidation_ok),
    ]
    first_abnormal_stage = _first_failed(stages)
    chain_status = "interrupted" if not (create_ok and list_ok and delete_ok) else "complete"
    reproduced_original_failure = all([create_ok, list_ok, delete_ok, cache_fill_ok, delete_db_ok]) and not cache_invalidation_ok
    confirmed_facts = _filtered_texts(
        f"创建订阅返回 {facts.get('create_status')}" if facts.get("create_status") is not None else None,
        f"查询订阅列表返回 {facts.get('list_status')}" if facts.get("list_status") is not None else None,
        _bool_text(facts.get("cache_payload_after_list_present"), "查询后订阅列表缓存已建立", "查询后订阅列表缓存未建立"),
        f"删除订阅返回 {facts.get('delete_status')}" if facts.get("delete_status") is not None else None,
        "删除后数据库中该订阅业务记录已不存在" if delete_db_ok else "删除后数据库中该订阅业务记录仍存在",
        _bool_text(facts.get("subscription_cache_exists_after"), "删除后 Redis 订阅缓存 key 仍存在", "删除后 Redis 订阅缓存 key 已清除"),
        _bool_text(facts.get("service_log_subscription_delete_cache_invalidated_seen"), "结构化日志中已看到 subscription_delete_cache_invalidated", "结构化日志中未看到 subscription_delete_cache_invalidated"),
    )
    excluded_scope = []
    if create_ok:
        excluded_scope.append("不是创建订阅失败")
    if list_ok:
        excluded_scope.append("不是查询订阅列表失败")
    if delete_ok:
        excluded_scope.append("不是删除订阅接口未返回成功")
    if delete_db_ok:
        excluded_scope.append("不是数据库删除未生效")
    if cache_fill_ok:
        excluded_scope.append("不是订阅列表缓存从未建立")
    remaining_scope, manual_checks = _summarize_scope(first_abnormal_stage)
    return {
        "facts": facts,
        "stage_results": {name: ok for name, ok in stages},
        "reproduced_original_failure": reproduced_original_failure,
        "chain_status": chain_status,
        "first_abnormal_stage": first_abnormal_stage,
        "suspected_segment": "subscription delete post-action cache invalidation" if first_abnormal_stage == "cache_invalidation_after_delete" else ("subscription request/delete execution" if first_abnormal_stage else None),
        "confirmed_facts": confirmed_facts,
        "excluded_scope": excluded_scope,
        "remaining_scope": remaining_scope,
        "manual_checks": manual_checks,
    }


def _analyze_share_link_is_cached_and_invalidated(facts: dict[str, Any]) -> dict[str, Any]:
    create_ok = facts.get("create_status") == 201
    get_ok = facts.get("get_status") == 200
    delete_ok = facts.get("delete_status") == 200
    cache_fill_ok = facts.get("cache_payload_after_read_present") is True
    delete_db_ok = facts.get("share_row_after_present") is False
    cache_invalidation_ok = facts.get("share_cache_exists_after") is False
    stages = [
        ("main_state_write", create_ok),
        ("cache_fill_after_read", get_ok and cache_fill_ok),
        ("main_state_delete", delete_ok and delete_db_ok),
        ("cache_invalidation_after_delete", cache_invalidation_ok),
    ]
    first_abnormal_stage = _first_failed(stages)
    chain_status = "interrupted" if not (create_ok and get_ok and delete_ok) else "complete"
    reproduced_original_failure = all([create_ok, get_ok, delete_ok, cache_fill_ok, delete_db_ok]) and not cache_invalidation_ok
    confirmed_facts = _filtered_texts(
        f"创建分享链接返回 {facts.get('create_status')}" if facts.get("create_status") is not None else None,
        f"读取分享链接返回 {facts.get('get_status')}" if facts.get("get_status") is not None else None,
        _bool_text(facts.get("cache_payload_after_read_present"), "读取后分享链接缓存已建立", "读取后分享链接缓存未建立"),
        f"删除分享链接返回 {facts.get('delete_status')}" if facts.get("delete_status") is not None else None,
        "删除后数据库中该分享链接记录已不存在" if delete_db_ok else "删除后数据库中该分享链接记录仍存在",
        _bool_text(facts.get("share_cache_exists_after"), "删除后 Redis 分享链接缓存 key 仍存在", "删除后 Redis 分享链接缓存 key 已清除"),
        _bool_text(facts.get("service_log_share_link_delete_cache_invalidated_seen"), "结构化日志中已看到 share_link_delete_cache_invalidated", "结构化日志中未看到 share_link_delete_cache_invalidated"),
    )
    excluded_scope = []
    if create_ok:
        excluded_scope.append("不是创建分享链接失败")
    if get_ok:
        excluded_scope.append("不是读取分享链接失败")
    if delete_ok:
        excluded_scope.append("不是删除分享链接接口未返回成功")
    if delete_db_ok:
        excluded_scope.append("不是分享链接数据库删除未生效")
    if cache_fill_ok:
        excluded_scope.append("不是分享链接缓存从未建立")
    remaining_scope, manual_checks = _summarize_scope(first_abnormal_stage)
    return {
        "facts": facts,
        "stage_results": {name: ok for name, ok in stages},
        "reproduced_original_failure": reproduced_original_failure,
        "chain_status": chain_status,
        "first_abnormal_stage": first_abnormal_stage,
        "suspected_segment": "share link delete post-action cache invalidation" if first_abnormal_stage == "cache_invalidation_after_delete" else ("share link request/delete execution" if first_abnormal_stage else None),
        "confirmed_facts": confirmed_facts,
        "excluded_scope": excluded_scope,
        "remaining_scope": remaining_scope,
        "manual_checks": manual_checks,
    }


def _analyze_dashboard_summary_is_cached(facts: dict[str, Any]) -> dict[str, Any]:
    summary_ok = facts.get("summary_status") == 200
    cache_write_ok = facts.get("summary_cache_exists_after") is True
    payload_ok = facts.get("summary_payload_matches_after_read") is not False
    source_ok = facts.get("summary_source_valid") is not False
    stages = [
        ("summary_generation", summary_ok and facts.get("summary_response_present") is True),
        ("summary_cache_write", cache_write_ok and payload_ok and source_ok),
    ]
    first_abnormal_stage = _first_failed(stages)
    chain_status = "interrupted" if not summary_ok else "complete"
    reproduced_original_failure = summary_ok and (not cache_write_ok or facts.get("summary_payload_matches_after_read") is False or facts.get("summary_source_valid") is False)
    confirmed_facts = _filtered_texts(
        f"获取摘要返回 {facts.get('summary_status')}" if facts.get("summary_status") is not None else None,
        _bool_text(facts.get("summary_cache_exists_after"), "摘要读取后 summary cache 已建立", "摘要读取后 summary cache 未建立"),
        _bool_text(facts.get("summary_payload_matches_after_read"), "summary cache payload 与响应摘要一致", "summary cache payload 与响应摘要不一致"),
        _bool_text(facts.get("summary_source_valid"), "摘要 source 字段有效", "摘要 source 字段异常"),
        _bool_text(facts.get("service_log_summary_cache_populated_seen"), "结构化日志中已看到 summary_cache_populated", "结构化日志中未看到 summary_cache_populated"),
    )
    excluded_scope = []
    if summary_ok:
        excluded_scope.append("不是摘要接口未返回成功")
    if facts.get("summary_response_present") is True:
        excluded_scope.append("不是摘要响应完全缺失")
    remaining_scope, manual_checks = _summarize_scope(first_abnormal_stage)
    return {
        "facts": facts,
        "stage_results": {name: ok for name, ok in stages},
        "reproduced_original_failure": reproduced_original_failure,
        "chain_status": chain_status,
        "first_abnormal_stage": first_abnormal_stage,
        "suspected_segment": "summary read cache persistence" if first_abnormal_stage == "summary_cache_write" else ("summary generation" if first_abnormal_stage else None),
        "confirmed_facts": confirmed_facts,
        "excluded_scope": excluded_scope,
        "remaining_scope": remaining_scope,
        "manual_checks": manual_checks,
    }


def _analyze_subscription_written_to_mysql(facts: dict[str, Any]) -> dict[str, Any]:
    create_ok = facts.get("create_status") == 201
    db_after_create_ok = all(
        facts.get(key) is True
        for key in (
            "db_row_after_create_present",
            "db_row_after_create_dashboard_uid_matches",
            "db_row_after_create_user_login_matches",
            "db_row_after_create_channel_matches",
        )
    )
    delete_ok = facts.get("delete_status") == 200
    delete_db_ok = facts.get("subscription_row_after_present") is False
    stages = [
        ("main_state_write", create_ok and db_after_create_ok),
        ("main_state_delete", delete_ok and delete_db_ok),
    ]
    first_abnormal_stage = _first_failed(stages)
    chain_status = "interrupted" if not (create_ok and delete_ok) else "complete"
    reproduced_original_failure = first_abnormal_stage is not None and chain_status == "complete"
    confirmed_facts = _filtered_texts(
        f"创建订阅返回 {facts.get('create_status')}" if facts.get("create_status") is not None else None,
        _bool_text(facts.get("db_row_after_create_present"), "创建后数据库中已查到该订阅记录", "创建后数据库中未查到该订阅记录"),
        _bool_text(facts.get("db_row_after_create_dashboard_uid_matches"), "创建后 dashboard_uid 与请求一致", "创建后 dashboard_uid 与请求不一致"),
        _bool_text(facts.get("db_row_after_create_user_login_matches"), "创建后 user_login 与请求一致", "创建后 user_login 与请求不一致"),
        _bool_text(facts.get("db_row_after_create_channel_matches"), "创建后 channel 与请求一致", "创建后 channel 与请求不一致"),
        f"删除订阅返回 {facts.get('delete_status')}" if facts.get("delete_status") is not None else None,
        _bool_text(delete_db_ok, "删除后数据库中该订阅记录已不存在", "删除后数据库中该订阅记录仍存在"),
    )
    excluded_scope = []
    if create_ok:
        excluded_scope.append("不是创建订阅接口未返回成功")
    if delete_ok:
        excluded_scope.append("不是删除订阅接口未返回成功")
    remaining_scope, manual_checks = _summarize_scope(first_abnormal_stage)
    return {
        "facts": facts,
        "stage_results": {name: ok for name, ok in stages},
        "reproduced_original_failure": reproduced_original_failure,
        "chain_status": chain_status,
        "first_abnormal_stage": first_abnormal_stage,
        "suspected_segment": "subscription DB persistence/deletion" if first_abnormal_stage else None,
        "confirmed_facts": confirmed_facts,
        "excluded_scope": excluded_scope,
        "remaining_scope": remaining_scope,
        "manual_checks": manual_checks,
    }


def _analyze_share_link_written_to_mysql_and_view_count_updated(facts: dict[str, Any]) -> dict[str, Any]:
    create_ok = facts.get("create_status") == 201
    get_ok = facts.get("get_status") == 200
    delete_ok = facts.get("delete_status") == 200
    create_db_ok = all(
        facts.get(key) is True
        for key in (
            "db_row_after_create_present",
            "share_row_after_create_dashboard_uid_matches",
            "share_row_initial_view_count_zero",
        )
    )
    read_db_ok = facts.get("db_row_after_get_present") is True and facts.get("share_row_view_count_advanced_after_get") is True
    delete_db_ok = facts.get("share_row_after_present") is False
    stages = [
        ("main_state_write", create_ok and create_db_ok),
        ("share_read_consistency", get_ok and read_db_ok),
        ("main_state_delete", delete_ok and delete_db_ok),
    ]
    first_abnormal_stage = _first_failed(stages)
    chain_status = "interrupted" if not (create_ok and get_ok and delete_ok) else "complete"
    reproduced_original_failure = first_abnormal_stage is not None and chain_status == "complete"
    confirmed_facts = _filtered_texts(
        f"创建分享链接返回 {facts.get('create_status')}" if facts.get("create_status") is not None else None,
        _bool_text(facts.get("db_row_after_create_present"), "创建后数据库中已查到该分享链接记录", "创建后数据库中未查到该分享链接记录"),
        _bool_text(facts.get("share_row_initial_view_count_zero"), "创建后初始 view_count 为 0", "创建后初始 view_count 异常"),
        f"读取分享链接返回 {facts.get('get_status')}" if facts.get("get_status") is not None else None,
        _bool_text(facts.get("share_row_view_count_advanced_after_get"), "读取后 view_count 已递增", "读取后 view_count 未递增"),
        f"删除分享链接返回 {facts.get('delete_status')}" if facts.get("delete_status") is not None else None,
        _bool_text(delete_db_ok, "删除后数据库中该分享链接记录已不存在", "删除后数据库中该分享链接记录仍存在"),
    )
    excluded_scope = []
    if create_ok:
        excluded_scope.append("不是创建分享链接接口未返回成功")
    if get_ok:
        excluded_scope.append("不是读取分享链接接口未返回成功")
    if delete_ok:
        excluded_scope.append("不是删除分享链接接口未返回成功")
    remaining_scope, manual_checks = _summarize_scope(first_abnormal_stage)
    return {
        "facts": facts,
        "stage_results": {name: ok for name, ok in stages},
        "reproduced_original_failure": reproduced_original_failure,
        "chain_status": chain_status,
        "first_abnormal_stage": first_abnormal_stage,
        "suspected_segment": "share link DB persistence / read consistency / deletion" if first_abnormal_stage else None,
        "confirmed_facts": confirmed_facts,
        "excluded_scope": excluded_scope,
        "remaining_scope": remaining_scope,
        "manual_checks": manual_checks,
    }


def _analyze_get_subscriptions_success(facts: dict[str, Any]) -> dict[str, Any]:
    create_ok = facts.get("create_status") == 201
    list_ok = facts.get("list_status") == 200
    list_contains_created = facts.get("created_subscription_present_in_list") is True
    stages = [
        ("main_state_write", create_ok),
        ("list_payload_consistency", list_ok and list_contains_created),
    ]
    first_abnormal_stage = _first_failed(stages)
    chain_status = "interrupted" if not (create_ok and list_ok) else "complete"
    reproduced_original_failure = first_abnormal_stage is not None and chain_status == "complete"
    confirmed_facts = _filtered_texts(
        f"创建订阅返回 {facts.get('create_status')}" if facts.get("create_status") is not None else None,
        f"查询订阅列表返回 {facts.get('list_status')}" if facts.get("list_status") is not None else None,
        _bool_text(facts.get("created_subscription_present_in_list"), "刚创建的订阅已出现在列表中", "刚创建的订阅未出现在列表中"),
    )
    excluded_scope = []
    if create_ok:
        excluded_scope.append("不是创建订阅接口未返回成功")
    if list_ok:
        excluded_scope.append("不是订阅列表接口未返回成功")
    remaining_scope, manual_checks = _summarize_scope(first_abnormal_stage)
    return {
        "facts": facts,
        "stage_results": {name: ok for name, ok in stages},
        "reproduced_original_failure": reproduced_original_failure,
        "chain_status": chain_status,
        "first_abnormal_stage": first_abnormal_stage,
        "suspected_segment": "subscription list payload construction" if first_abnormal_stage else None,
        "confirmed_facts": confirmed_facts,
        "excluded_scope": excluded_scope,
        "remaining_scope": remaining_scope,
        "manual_checks": manual_checks,
    }


def _analyze_generic_create_and_read_or_write(replay_result: dict[str, Any], facts: dict[str, Any]) -> dict[str, Any]:
    target = replay_result.get("replay_target")
    if target == "test_create_subscription_success":
        create_ok = facts.get("create_status") == 201
        db_ok = facts.get("subscription_row_after_present") is True
        stages = [("main_state_write", create_ok and db_ok)]
        suspected_segment = "subscription create persistence"
        confirmed_facts = _filtered_texts(
            f"创建订阅返回 {facts.get('create_status')}" if facts.get("create_status") is not None else None,
            _bool_text(facts.get("subscription_row_after_present"), "创建后快照中已看到订阅记录", "创建后快照中未看到订阅记录"),
        )
    elif target == "test_create_share_link_success":
        create_ok = facts.get("create_status") == 201
        db_ok = facts.get("share_row_after_present") is True
        stages = [("main_state_write", create_ok and db_ok)]
        suspected_segment = "share link create persistence"
        confirmed_facts = _filtered_texts(
            f"创建分享链接返回 {facts.get('create_status')}" if facts.get("create_status") is not None else None,
            _bool_text(facts.get("share_row_after_present"), "创建后快照中已看到分享链接记录", "创建后快照中未看到分享链接记录"),
        )
    elif target == "test_get_share_link_success":
        create_ok = facts.get("create_status") == 201
        get_ok = facts.get("get_status") == 200
        stages = [("main_state_write", create_ok), ("share_read_consistency", get_ok)]
        suspected_segment = "share link read"
        confirmed_facts = _filtered_texts(
            f"创建分享链接返回 {facts.get('create_status')}" if facts.get("create_status") is not None else None,
            f"读取分享链接返回 {facts.get('get_status')}" if facts.get("get_status") is not None else None,
        )
    elif target == "test_get_dashboard_summary_success":
        summary_ok = facts.get("summary_status") == 200
        summary_present = facts.get("summary_response_present") is True
        stages = [("summary_generation", summary_ok and summary_present)]
        suspected_segment = "summary generation"
        confirmed_facts = _filtered_texts(
            f"获取摘要返回 {facts.get('summary_status')}" if facts.get("summary_status") is not None else None,
            _bool_text(facts.get("summary_response_present"), "摘要响应已生成", "摘要响应未生成"),
        )
    else:
        return _default_analysis(replay_result, facts)

    first_abnormal_stage = _first_failed(stages)
    chain_status = "interrupted" if any(not ok and name in {"main_state_write", "share_read_consistency", "summary_generation"} for name, ok in stages) else "complete"
    reproduced_original_failure = first_abnormal_stage is not None and chain_status == "complete"
    remaining_scope, manual_checks = _summarize_scope(first_abnormal_stage)
    excluded_scope = []
    if stages and stages[0][1]:
        excluded_scope.append("首个请求步骤已按预期返回")
    return {
        "facts": facts,
        "stage_results": {name: ok for name, ok in stages},
        "reproduced_original_failure": reproduced_original_failure,
        "chain_status": chain_status,
        "first_abnormal_stage": first_abnormal_stage,
        "suspected_segment": suspected_segment if first_abnormal_stage else None,
        "confirmed_facts": confirmed_facts,
        "excluded_scope": excluded_scope,
        "remaining_scope": remaining_scope,
        "manual_checks": manual_checks,
    }


def _analyze_negative_cases(replay_result: dict[str, Any], facts: dict[str, Any]) -> dict[str, Any]:
    target = replay_result.get("replay_target")
    if target == "test_create_subscription_with_unknown_dashboard":
        status_ok = facts.get("unknown_dashboard_status") == 404
        side_effect_ok = facts.get("subscription_business_key_count_after") in (0, None)
        confirmed_facts = _filtered_texts(
            f"未知 dashboard 创建订阅返回 {facts.get('unknown_dashboard_status')}" if facts.get("unknown_dashboard_status") is not None else None,
            "未知 dashboard 后数据库中未新增订阅记录" if side_effect_ok else "未知 dashboard 后数据库中仍出现订阅记录",
        )
    elif target == "test_create_subscription_with_illegal_channel":
        status_ok = facts.get("invalid_channel_status") == 422
        side_effect_ok = facts.get("subscription_business_key_count_after") in (0, None)
        confirmed_facts = _filtered_texts(
            f"非法 channel 创建订阅返回 {facts.get('invalid_channel_status')}" if facts.get("invalid_channel_status") is not None else None,
            "非法 channel 后数据库中未新增订阅记录" if side_effect_ok else "非法 channel 后数据库中仍出现订阅记录",
        )
    elif target == "test_get_unknown_share_token":
        status_ok = facts.get("unknown_share_status") == 404
        side_effect_ok = (facts.get("share_row_after_present") is False) and (facts.get("share_cache_exists_after") is False)
        confirmed_facts = _filtered_texts(
            f"读取未知分享 token 返回 {facts.get('unknown_share_status')}" if facts.get("unknown_share_status") is not None else None,
            "未知 token 后数据库和缓存都未产生副作用" if side_effect_ok else "未知 token 后仍观察到数据库或缓存副作用",
        )
    elif target == "test_get_expired_share_link":
        create_ok = facts.get("create_status") == 201
        status_ok = facts.get("expired_share_status") == 410
        side_effect_ok = True
        confirmed_facts = _filtered_texts(
            f"创建过期分享链接返回 {facts.get('create_status')}" if facts.get("create_status") is not None else None,
            f"读取过期分享链接返回 {facts.get('expired_share_status')}" if facts.get("expired_share_status") is not None else None,
        )
        if not create_ok:
            status_ok = False
    else:
        return _default_analysis(replay_result, facts)

    stages = [("request_validation", status_ok), ("negative_side_effect_absence", side_effect_ok)]
    first_abnormal_stage = _first_failed(stages)
    chain_status = "complete"
    reproduced_original_failure = first_abnormal_stage is not None
    excluded_scope = []
    if status_ok:
        excluded_scope.append("错误状态码分支本身已按预期返回")
    if side_effect_ok:
        excluded_scope.append("错误分支后未观察到额外副作用")
    remaining_scope, manual_checks = _summarize_scope(first_abnormal_stage)
    return {
        "facts": facts,
        "stage_results": {name: ok for name, ok in stages},
        "reproduced_original_failure": reproduced_original_failure,
        "chain_status": chain_status,
        "first_abnormal_stage": first_abnormal_stage,
        "suspected_segment": "negative request validation / no-side-effect guard" if first_abnormal_stage else None,
        "confirmed_facts": confirmed_facts,
        "excluded_scope": excluded_scope,
        "remaining_scope": remaining_scope,
        "manual_checks": manual_checks,
    }


def _analyze_duplicate_subscription(facts: dict[str, Any]) -> dict[str, Any]:
    first_ok = facts.get("first_create_status") == 201
    second_ok = facts.get("second_create_status") == 409
    row_count_ok = facts.get("subscription_business_key_count_after") == 1
    stages = [
        ("main_state_write", first_ok),
        ("request_validation", second_ok),
        ("negative_side_effect_absence", row_count_ok),
    ]
    first_abnormal_stage = _first_failed(stages)
    chain_status = "complete"
    reproduced_original_failure = first_abnormal_stage is not None
    confirmed_facts = _filtered_texts(
        f"第一次创建订阅返回 {facts.get('first_create_status')}" if facts.get("first_create_status") is not None else None,
        f"第二次重复创建返回 {facts.get('second_create_status')}" if facts.get("second_create_status") is not None else None,
        f"重复创建后业务键对应记录数为 {facts.get('subscription_business_key_count_after')}" if facts.get("subscription_business_key_count_after") is not None else None,
    )
    excluded_scope = []
    if first_ok:
        excluded_scope.append("第一次创建订阅已成功")
    if second_ok:
        excluded_scope.append("重复创建的冲突状态码已按预期返回")
    if row_count_ok:
        excluded_scope.append("重复创建后未产生多余订阅记录")
    remaining_scope, manual_checks = _summarize_scope(first_abnormal_stage)
    return {
        "facts": facts,
        "stage_results": {name: ok for name, ok in stages},
        "reproduced_original_failure": reproduced_original_failure,
        "chain_status": chain_status,
        "first_abnormal_stage": first_abnormal_stage,
        "suspected_segment": "duplicate subscription conflict handling" if first_abnormal_stage else None,
        "confirmed_facts": confirmed_facts,
        "excluded_scope": excluded_scope,
        "remaining_scope": remaining_scope,
        "manual_checks": manual_checks,
    }


def analyze_replay_result(replay_result: dict[str, Any]) -> dict[str, Any]:
    facts = _extract_facts(replay_result)
    target = replay_result.get("replay_target")

    if target == "test_subscriptions_are_cached_and_invalidated":
        return _analyze_subscriptions_are_cached_and_invalidated(facts)
    if target == "test_share_link_is_cached_and_invalidated":
        return _analyze_share_link_is_cached_and_invalidated(facts)
    if target == "test_dashboard_summary_is_cached":
        return _analyze_dashboard_summary_is_cached(facts)
    if target == "test_subscription_written_to_mysql":
        return _analyze_subscription_written_to_mysql(facts)
    if target == "test_share_link_written_to_mysql_and_view_count_updated":
        return _analyze_share_link_written_to_mysql_and_view_count_updated(facts)
    if target == "test_get_subscriptions_success":
        return _analyze_get_subscriptions_success(facts)
    if target in {
        "test_create_subscription_success",
        "test_create_share_link_success",
        "test_get_share_link_success",
        "test_get_dashboard_summary_success",
    }:
        return _analyze_generic_create_and_read_or_write(replay_result, facts)
    if target in {
        "test_create_subscription_with_unknown_dashboard",
        "test_create_subscription_with_illegal_channel",
        "test_get_unknown_share_token",
        "test_get_expired_share_link",
    }:
        return _analyze_negative_cases(replay_result, facts)
    if target == "test_create_duplicate_subscription":
        return _analyze_duplicate_subscription(facts)
    return _default_analysis(replay_result, facts)
