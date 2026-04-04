from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path

TARGET_METRICS = (
    'dashboard_hub_requests_total',
    'dashboard_hub_request_latency_seconds_count',
    'dashboard_hub_cache_hit_total',
    'dashboard_hub_cache_miss_total',
    'dashboard_hub_summary_source_total',
)


def collect_metrics(metrics_url: str) -> dict[str, list[str]]:
    with urllib.request.urlopen(metrics_url, timeout=10) as response:
        text = response.read().decode('utf-8')

    result: dict[str, list[str]] = {key: [] for key in TARGET_METRICS}
    for line in text.splitlines():
        if not line or line.startswith('#'):
            continue
        for metric in TARGET_METRICS:
            if line.startswith(metric):
                result[metric].append(line)
                break
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description='Collect selected Prometheus metric samples')
    parser.add_argument('--metrics-url', default='http://localhost:8000/metrics')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    payload = collect_metrics(args.metrics_url)
    Path(args.output).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'metrics snapshot written to {args.output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
