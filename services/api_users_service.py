from __future__ import annotations

from requests import Response

import config.settings as settings
from data.users_credentials import change_password
from helpers.decorators import api_error_handler, retry
from services.db_service import DBService
from services.http_client import HttpClient
from services.utils import safe_json, total_log_in_method


class ApiUsersService:
    client = HttpClient(settings.GRAFANA_BASE_URL, auth=settings.BASIC_AUTH)

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def create_api_user(
        credentials: dict,
        auth: tuple[str, str] | None = None,
    ) -> tuple[Response, int | None]:
        response = ApiUsersService.client.request(
            "POST",
            "/api/admin/users",
            auth=auth or settings.BASIC_AUTH,
            json=credentials,
            headers={"Content-Type": "application/json"},
        )
        total_log_in_method(response)
        return response, safe_json(response).get("id")

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def create_bad_request(
        payload: dict,
        auth: tuple[str, str] | None = None,
    ) -> Response:
        response = ApiUsersService.client.request(
            "POST",
            "/api/admin/users",
            auth=auth or settings.BASIC_AUTH,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        total_log_in_method(response)
        return response

    @staticmethod
    @api_error_handler
    def delete_api_user(
        user_id: int | None = None,
        userid: int | None = None,
        auth: tuple[str, str] | None = None,
    ) -> Response:
        target_id = user_id if user_id is not None else userid
        if target_id is None:
            raise ValueError("user_id or userid must be provided")
        response = ApiUsersService.client.request(
            "DELETE",
            f"/api/admin/users/{target_id}",
            auth=auth or settings.BASIC_AUTH,
        )
        total_log_in_method(response)
        return response

    @staticmethod
    @api_error_handler
    def change_user_password(
        user_id: int | None = None,
        userid: int | None = None,
        auth: tuple[str, str] | None = None,
        body: dict | None = None,
    ) -> Response:
        target_id = user_id if user_id is not None else userid
        if target_id is None:
            raise ValueError("user_id or userid must be provided")
        response = ApiUsersService.client.request(
            "PUT",
            f"/api/admin/users/{target_id}/password",
            auth=auth or settings.BASIC_AUTH,
            json=body or {"password": change_password["password"]},
            headers={"Content-Type": "application/json"},
        )
        total_log_in_method(response)
        return response

    @staticmethod
    def find_user_by_login(login: str) -> int | None:
        row = DBService.find_user_by_login(login)
        return row[3] if row else None
