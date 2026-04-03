from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from data.dashboard_hub_data import make_share_link_payload, make_subscription_payload
from services.dashboard_hub_service import DashboardHubService


@pytest.mark.metrics
def test_metrics_include_internal_dependency_and_business_indicators(session_context):
    create_payload = make_subscription_payload(
        session_context.dashboard_uid,
        session_context.existing_user_login,
        channel="metrics-email",
    )
    create_response, subscription_id = DashboardHubService.create_subscription(**create_payload)
    assert create_response.status_code == 201
    session_context.register_subscription(subscription_id)

    conflict_response, _ = DashboardHubService.create_subscription(**create_payload)
    assert conflict_response.status_code == 409

    list_response = DashboardHubService.list_subscriptions(session_context.dashboard_uid)
    assert list_response.status_code == 200

    share_response, token = DashboardHubService.create_share_link(
        session_context.dashboard_uid,
        expire_at=(datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat(),
    )
    assert share_response.status_code == 201
    session_context.register_share_token(token)

    read_response = DashboardHubService.get_share_link(token)
    assert read_response.status_code == 200

    metrics_response = DashboardHubService.get_metrics()
    assert metrics_response.status_code == 200
    body = metrics_response.text

    assert "dashboard_hub_grafana_requests_total" in body
    assert "dashboard_hub_grafana_request_latency_seconds" in body
    assert "dashboard_hub_grafana_request_failures_total" in body
    assert "dashboard_hub_db_operation_latency_seconds" in body
    assert "dashboard_hub_cache_operation_latency_seconds" in body
    assert "dashboard_hub_subscription_conflicts_total" in body
    assert "dashboard_hub_cache_invalidations_total" in body


@pytest.mark.metrics
def test_expired_share_link_metric_is_exposed(session_context):
    create_response, token = DashboardHubService.create_share_link(
        session_context.dashboard_uid,
        expire_at=(datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
    )
    assert create_response.status_code == 201
    session_context.register_share_token(token)

    read_response = DashboardHubService.get_share_link(token)
    assert read_response.status_code == 410

    metrics_response = DashboardHubService.get_metrics()
    assert metrics_response.status_code == 200
    assert "dashboard_hub_share_link_expired_total" in metrics_response.text
