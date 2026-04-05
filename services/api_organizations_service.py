from __future__ import annotations

import logging

from requests import Response

import config.settings as settings
from data.organizations_data import add_in_organizations_body, get_test_organization_body
from helpers.decorators import api_error_handler, retry
from services.http_client import HttpClient
from services.utils import safe_json, total_log_in_method


class ApiOrganizationsService:
    client = HttpClient(settings.GRAFANA_BASE_URL, auth=settings.BASIC_AUTH)

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def create_new_organization(
        body: dict | None = None,
        auth: tuple[str, str] | None = None,
    ) -> tuple[Response, int | None]:
        response = ApiOrganizationsService.client.request(
            "POST",
            "/api/orgs",
            auth=auth or settings.BASIC_AUTH,
            json=body or get_test_organization_body(),
            headers={"Content-Type": "application/json"},
        )
        total_log_in_method(response)
        return response, safe_json(response).get("orgId")

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def add_user_in_organization(
        org_id: int,
        body: dict | None = None,
        auth: tuple[str, str] | None = None,
    ) -> tuple[Response, int | None]:
        response = ApiOrganizationsService.client.request(
            "POST",
            f"/api/orgs/{org_id}/users",
            auth=auth or settings.BASIC_AUTH,
            json=body or add_in_organizations_body,
            headers={"Content-Type": "application/json"},
        )
        total_log_in_method(response)
        return response, safe_json(response).get("userId")

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def get_organizations_by_id(org_id: int, auth: tuple[str, str] | None = None) -> Response:
        response = ApiOrganizationsService.client.request(
            "GET",
            f"/api/orgs/{org_id}",
            auth=auth or settings.BASIC_AUTH,
        )
        total_log_in_method(response)
        return response

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def get_users_in_organization(org_id: int, auth: tuple[str, str] | None = None) -> Response:
        response = ApiOrganizationsService.client.request(
            "GET",
            f"/api/orgs/{org_id}/users",
            auth=auth or settings.BASIC_AUTH,
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
    ) -> Response:
        response = ApiOrganizationsService.client.request(
            "PATCH",
            f"/api/orgs/{org_id}/users/{user_id}",
            auth=auth or settings.BASIC_AUTH,
            json={"role": role},
            headers={"Content-Type": "application/json"},
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
    ) -> Response | None:
        if userid is None:
            raise ValueError("userid must be provided")
        response = ApiOrganizationsService.client.request(
            "DELETE",
            f"/api/orgs/{orgid}/users/{userid}",
            auth=auth or settings.BASIC_AUTH,
        )
        total_log_in_method(response)
        if response.status_code == 404:
            logging.warning("User %s already removed from org %s", userid, orgid)
            return None
        return response

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def delete_organization(org_id: int, auth: tuple[str, str] | None = None) -> Response | None:
        response = ApiOrganizationsService.client.request(
            "DELETE",
            f"/api/orgs/{org_id}",
            auth=auth or settings.BASIC_AUTH,
        )
        total_log_in_method(response)
        if response.status_code == 404:
            logging.warning("Organization %s already deleted", org_id)
            return None
        return response
