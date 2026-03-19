import logging

import requests

import config.settings as settings
import data.dashboards_data as data
from helpers.decorators import api_error_handler, retry
from services.utils import total_log_in_method


class ApiDashboardsService:
    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def create_folder(body: dict | None = None, auth: tuple[str, str] | None = None):
        url = f"{settings.BASE_URL}/api/folders"
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            url,
            auth=auth or settings.BASIC_AUTH,
            json=body or data.body_for_create_folder,
            headers=headers,
            timeout=10,
        )
        total_log_in_method(response)
        return response, response.json().get("uid")

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def create_dashboard(
        folder_uid: str,
        body: dict | None = None,
        auth: tuple[str, str] | None = None,
    ):
        url = f"{settings.BASE_URL}/api/dashboards/db"
        headers = {"Content-Type": "application/json"}
        payload = body or data.get_body_for_create_dashboard(folder_uid)
        response = requests.post(
            url,
            auth=auth or settings.BASIC_AUTH,
            json=payload,
            headers=headers,
            timeout=10,
        )
        total_log_in_method(response)
        return response, response.json().get("uid")

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def get_dashboard(dashboard_uid: str, auth: tuple[str, str] | None = None):
        url = f"{settings.BASE_URL}/api/dashboards/uid/{dashboard_uid}"
        headers = {"Content-Type": "application/json"}
        response = requests.get(
            url,
            auth=auth or settings.BASIC_AUTH,
            headers=headers,
            timeout=10,
        )
        total_log_in_method(response)
        return response

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def delete_dashboard(dashboard_uid: str, auth: tuple[str, str] | None = None):
        url = f"{settings.BASE_URL}/api/dashboards/uid/{dashboard_uid}"
        headers = {"Content-Type": "application/json"}
        response = requests.delete(
            url,
            auth=auth or settings.BASIC_AUTH,
            headers=headers,
            timeout=10,
        )
        total_log_in_method(response)

        if response.status_code == 404:
            logging.warning(f"Dashboard {dashboard_uid} already deleted")
            return None
        return response

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def delete_folder_for_dashboard(folder_uid: str, auth: tuple[str, str] | None = None):
        url = f"{settings.BASE_URL}/api/folders/{folder_uid}"
        headers = {"Content-Type": "application/json"}
        response = requests.delete(
            url,
            auth=auth or settings.BASIC_AUTH,
            headers=headers,
            timeout=10,
        )
        total_log_in_method(response)

        if response.status_code == 404:
            logging.warning(f"Folder {folder_uid} already deleted")
            return None
        return response
