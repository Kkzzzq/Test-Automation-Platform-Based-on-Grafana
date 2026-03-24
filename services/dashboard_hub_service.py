from __future__ import annotations

from datetime import datetime

from requests import Response

import config.settings as settings
from helpers.decorators import api_error_handler, retry
from services.http_client import HttpClient
from services.utils import safe_json, total_log_in_method


class DashboardHubService:
    client = HttpClient(settings.DASHBOARD_HUB_BASE_URL)

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def create_subscription(
        dashboard_uid: str,
        user_login: str,
        channel: str = "email",
        cron: str = "0 */6 * * *",
    ) -> tuple[Response, int | None]:
        response = DashboardHubService.client.request(
            "POST",
            "/api/v1/subscriptions",
            json={
                "dashboard_uid": dashboard_uid,
                "user_login": user_login,
                "channel": channel,
                "cron": cron,
            },
            headers={"Content-Type": "application/json"},
        )
        total_log_in_method(response)
        return response, safe_json(response).get("id")

    @staticmethod
    @api_error_handler
    def list_subscriptions(dashboard_uid: str) -> Response:
        response = DashboardHubService.client.request(
            "GET",
            f"/api/v1/dashboards/{dashboard_uid}/subscriptions",
        )
        total_log_in_method(response)
        return response

    @staticmethod
    @api_error_handler
    def delete_subscription(subscription_id: int) -> Response:
        response = DashboardHubService.client.request(
            "DELETE",
            f"/api/v1/subscriptions/{subscription_id}",
        )
        total_log_in_method(response)
        return response

    @staticmethod
    @api_error_handler
    def create_share_link(
        dashboard_uid: str,
        expire_at: datetime | str | None = None,
    ) -> tuple[Response, str | None]:
        expire_value = expire_at.isoformat() if isinstance(expire_at, datetime) else expire_at
        response = DashboardHubService.client.request(
            "POST",
            "/api/v1/share-links",
            json={"dashboard_uid": dashboard_uid, "expire_at": expire_value},
            headers={"Content-Type": "application/json"},
        )
        total_log_in_method(response)
        return response, safe_json(response).get("token")

    @staticmethod
    @api_error_handler
    def get_share_link(token: str) -> Response:
        response = DashboardHubService.client.request("GET", f"/api/v1/share-links/{token}")
        total_log_in_method(response)
        return response

    @staticmethod
    @api_error_handler
    def get_dashboard_summary(dashboard_uid: str) -> Response:
        response = DashboardHubService.client.request(
            "GET",
            f"/api/v1/dashboards/{dashboard_uid}/summary",
        )
        total_log_in_method(response)
        return response
