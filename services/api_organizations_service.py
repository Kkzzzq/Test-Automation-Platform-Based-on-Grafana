import logging

import requests

import config.settings as settings
from data.organizations_data import add_in_organizations_body, test_organizations_body
from helpers.decorators import api_error_handler, retry
from services.utils import total_log_in_method


class ApiOrganizationsService:
    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def create_new_organization(
        body: dict | None = None,
        auth: tuple[str, str] | None = None,
    ):
        url = f"{settings.BASE_URL}/api/orgs"
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            url,
            auth=auth or settings.BASIC_AUTH,
            json=body or test_organizations_body,
            headers=headers,
            timeout=10,
        )
        total_log_in_method(response)
        return response, response.json().get("orgId")

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def add_user_in_organization(
        org_id: int,
        body: dict | None = None,
        auth: tuple[str, str] | None = None,
    ):
        url = f"{settings.BASE_URL}/api/orgs/{org_id}/users"
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            url,
            auth=auth or settings.BASIC_AUTH,
            json=body or add_in_organizations_body,
            headers=headers,
            timeout=10,
        )
        total_log_in_method(response)
        return response, response.json().get("userId")

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def get_organizations_by_id(org_id: int, auth: tuple[str, str] | None = None):
        url = f"{settings.BASE_URL}/api/orgs/{org_id}"
        response = requests.get(
            url,
            auth=auth or settings.BASIC_AUTH,
            timeout=10,
        )
        total_log_in_method(response)
        return response

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def get_users_in_organization(org_id: int, auth: tuple[str, str] | None = None):
        url = f"{settings.BASE_URL}/api/orgs/{org_id}/users"
        response = requests.get(
            url,
            auth=auth or settings.BASIC_AUTH,
            timeout=10,
        )
        total_log_in_method(response)
        return response

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def update_user_in_org(
        org_id: int,
        user_id: int,
        role: str = "Admin",
        auth: tuple[str, str] | None = None,
    ):
        body = {"role": role}
        url = f"{settings.BASE_URL}/api/orgs/{org_id}/users/{user_id}"
        response = requests.patch(
            url,
            auth=auth or settings.BASIC_AUTH,
            json=body,
            timeout=10,
        )
        total_log_in_method(response)
        return response

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def delete_user_from_org(
        orgid: int = 1,
        userid: int | None = None,
        auth: tuple[str, str] | None = None,
    ):
        if userid is None:
            raise ValueError("userid must be provided")

        url = f"{settings.BASE_URL}/api/orgs/{orgid}/users/{userid}"
        response = requests.delete(
            url,
            auth=auth or settings.BASIC_AUTH,
            timeout=10,
        )
        total_log_in_method(response)

        if response.status_code == 404:
            logging.warning(f"User {userid} already deleted from org. Skipping deletion")
            return None
        return response

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def delete_organization(org_id: int, auth: tuple[str, str] | None = None):
        url = f"{settings.BASE_URL}/api/orgs/{org_id}"
        response = requests.delete(
            url,
            auth=auth or settings.BASIC_AUTH,
            timeout=10,
        )
        total_log_in_method(response)

        if response.status_code == 404:
            logging.warning(f"Organization {org_id} already deleted")
            return None
        return response
