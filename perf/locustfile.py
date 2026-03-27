from __future__ import annotations

import os
from itertools import count

from locust import HttpUser, between, task


DASHBOARD_UID = os.getenv("LOCUST_DASHBOARD_UID", "replace-me")
SHARE_TOKEN = os.getenv("LOCUST_SHARE_TOKEN", "replace-me")
CONFLICT_USER_LOGIN = os.getenv("LOCUST_CONFLICT_USER_LOGIN", "locust_conflict_user")

_CHANNELS = ("email", "slack", "webhook")
_login_counter = count(1)
_channel_counter = count(0)


def _next_user_login() -> str:
    return f"locust_user_{next(_login_counter)}"


def _next_channel() -> str:
    return _CHANNELS[next(_channel_counter) % len(_CHANNELS)]


class DashboardHubUser(HttpUser):
    wait_time = between(1, 2)

    @task(4)
    def list_subscriptions(self):
        if DASHBOARD_UID != "replace-me":
            self.client.get(
                f"/api/v1/dashboards/{DASHBOARD_UID}/subscriptions",
                name="/api/v1/dashboards/{dashboard_uid}/subscriptions",
            )

    @task(4)
    def get_share_link(self):
        if SHARE_TOKEN != "replace-me":
            self.client.get(
                f"/api/v1/share-links/{SHARE_TOKEN}",
                name="/api/v1/share-links/{token}",
            )

    @task(5)
    def get_dashboard_summary(self):
        if DASHBOARD_UID != "replace-me":
            self.client.get(
                f"/api/v1/dashboards/{DASHBOARD_UID}/summary",
                name="/api/v1/dashboards/{dashboard_uid}/summary",
            )

    @task(1)
    def create_subscription_normal(self):
        if DASHBOARD_UID == "replace-me":
            return

        payload = {
            "dashboard_uid": DASHBOARD_UID,
            "user_login": _next_user_login(),
            "channel": _next_channel(),
            "cron": "0 */6 * * *",
        }

        self.client.post(
            "/api/v1/subscriptions",
            json=payload,
            name="/api/v1/subscriptions:create_normal",
        )

    @task(2)
    def create_subscription_conflict(self):
        if DASHBOARD_UID == "replace-me":
            return

        payload = {
            "dashboard_uid": DASHBOARD_UID,
            "user_login": CONFLICT_USER_LOGIN,
            "channel": "email",
            "cron": "0 */6 * * *",
        }

        with self.client.post(
            "/api/v1/subscriptions",
            json=payload,
            name="/api/v1/subscriptions:create_conflict",
            catch_response=True,
        ) as response:
            if response.status_code in (201, 409):
                response.success()
            else:
                response.failure(
                    f"unexpected status={response.status_code}, body={response.text[:200]}"
                )
