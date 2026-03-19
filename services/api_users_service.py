import logging

import requests
from requests import Response

import config.settings as settings
from data.users_credentials import change_password
from helpers.decorators import api_error_handler, retry
from services.utils import total_log_in_method


class ApiUsersService:
    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def create_api_user(credentials: dict, auth: tuple[str, str] | None = None) -> tuple[Response, int | None]:
        url = f"{settings.BASE_URL}/api/admin/users"
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            url,
            auth=auth or settings.BASIC_AUTH,
            json=credentials,
            headers=headers,
            timeout=10,
        )
        total_log_in_method(response)
        return response, response.json().get("id")

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def find_user_by_login(login: str, auth: tuple[str, str] | None = None) -> int | None:
        url = f"{settings.BASE_URL}/api/users/lookup?loginOrEmail={login}"
        headers = {"Content-Type": "application/json"}
        response = requests.get(
            url,
            auth=auth or settings.BASIC_AUTH,
            headers=headers,
            timeout=10,
        )
        total_log_in_method(response)
        return response.json().get("id")

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def delete_api_user(userid: int, auth: tuple[str, str] | None = None) -> Response | None:
        url = f"{settings.BASE_URL}/api/admin/users/{userid}"
        response = requests.delete(
            url,
            auth=auth or settings.BASIC_AUTH,
            timeout=10,
        )
        total_log_in_method(response)
        if response.status_code == 404:
            logging.warning(f"User {userid} already deleted. Skipping deletion")
            return None
        return response

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def create_bad_request(payload: dict | None = None, auth: tuple[str, str] | None = None) -> Response:
        url = f"{settings.BASE_URL}/api/admin/users"
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            url,
            auth=auth or settings.BASIC_AUTH,
            json=payload or {},
            headers=headers,
            timeout=10,
        )
        total_log_in_method(response)
        return response

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def change_user_password(
        userid: int,
        payload: dict | None = None,
        auth: tuple[str, str] | None = None,
    ) -> Response:
        url = f"{settings.BASE_URL}/api/admin/users/{userid}/password"
        headers = {"Content-Type": "application/json"}
        response = requests.put(
            url,
            auth=auth or settings.BASIC_AUTH,
            json=payload or change_password,
            headers=headers,
            timeout=10,
        )
        total_log_in_method(response)
        return response
