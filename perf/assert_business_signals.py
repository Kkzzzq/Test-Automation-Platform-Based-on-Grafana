from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _sum_values(mapping: dict[str, int] | None) -> int:
    if not isinstance(mapping, dict):
        return 0
    return sum(int(value) for value in mapping.values())


def _get_nested(payload: dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _delta(before: dict[str, Any], after: dict[str, Any], *keys: str) -> int:
    before_value = _get_nested(before, *keys)
    after_value = _get_nested(after, *keys)
    if isinstance(before_value, dict) or isinstance(after_value, dict):
        return _sum_values(after_value) - _sum_values(before_value)
    return int(after_value or 0) - int(before_value or 0)


def _profile_assertions(before: dict[str, Any], after: dict[str, Any], profile: str) -> tuple[dict[str, int], list[str]]:
    summary: dict[str, int] = {}
    errors: list[str] = []

    if profile == 'write_conflict':
        conflicts_delta = _delta(before, after, 'business', 'subscription_conflicts_by_channel')
        creates_delta = _delta(before, after, 'cache', 'invalidations_by_name_reason')
        summary['subscription_conflicts_delta'] = conflicts_delta
        summary['cache_invalidations_delta'] = creates_delta
        if conflicts_delta <= 0:
            errors.append('write_conflict 场景没有观察到 subscription_conflicts 指标增长，说明并发冲突没有被真正打出来')
    elif profile == 'hot_read':
        subscription_hits_delta = _delta(before, after, 'cache', 'hits_by_name', 'subscriptions')
        share_hits_delta = _delta(before, after, 'cache', 'hits_by_name', 'share_link')
        summary['subscriptions_cache_hits_delta'] = subscription_hits_delta
        summary['share_link_cache_hits_delta'] = share_hits_delta
        if subscription_hits_delta + share_hits_delta <= 0:
            errors.append('hot_read 场景没有观察到 subscriptions/share_link 缓存命中增长，说明热点读没有真正打到缓存')
    elif profile == 'cache_penetration':
        share_misses_delta = _delta(before, after, 'cache', 'misses_by_name', 'share_link')
        dashboard_exists_misses_delta = _delta(before, after, 'cache', 'misses_by_name', 'dashboard_exists')
        summary['share_link_cache_misses_delta'] = share_misses_delta
        summary['dashboard_exists_cache_misses_delta'] = dashboard_exists_misses_delta
        if share_misses_delta + dashboard_exists_misses_delta <= 0:
            errors.append('cache_penetration 场景没有观察到 share_link/dashboard_exists 缓存未命中增长，说明穿透流量没有真正形成')
    elif profile == 'cache_breakdown':
        subscription_misses_delta = _delta(before, after, 'cache', 'misses_by_name', 'subscriptions')
        subscription_hits_delta = _delta(before, after, 'cache', 'hits_by_name', 'subscriptions')
        summary['subscriptions_cache_misses_delta'] = subscription_misses_delta
        summary['subscriptions_cache_hits_delta'] = subscription_hits_delta
        if subscription_misses_delta <= 0:
            errors.append('cache_breakdown 场景没有观察到 subscriptions 缓存未命中增长，说明热点 key 删除后没有真正发生回源')
    else:
        errors.append(f'unsupported profile: {profile}')

    total_requests_delta = _delta(before, after, 'http', 'total_requests')
    summary['http_total_requests_delta'] = total_requests_delta
    if total_requests_delta <= 0:
        errors.append('没有观察到 HTTP 总请求数增长，说明压测流量本身没有真正进入服务')

    return summary, errors


def main() -> int:
    parser = argparse.ArgumentParser(description='Assert business-level signals from before/after metrics snapshots')
    parser.add_argument('--before', required=True)
    parser.add_argument('--after', required=True)
    parser.add_argument('--profile', choices=['hot_read', 'write_conflict', 'cache_penetration', 'cache_breakdown'], required=True)
    parser.add_argument('--summary-output')
    args = parser.parse_args()

    before = _load(args.before)
    after = _load(args.after)
    summary, errors = _profile_assertions(before, after, args.profile)

    payload = {
        'profile': args.profile,
        'summary': summary,
        'errors': errors,
    }

    if args.summary_output:
        Path(args.summary_output).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit('Business signal assertion failed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
