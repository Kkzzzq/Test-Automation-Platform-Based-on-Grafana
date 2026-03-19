import logging
import os
import shutil

import allure
import pytest

from config import settings
from data.organizations_data import test_organizations_body
from data.users_credentials import existing_credentials, low_access_credentials, organizations_user
from helpers.schemas.organizations_schema import CreateOrganizationSchema
from services.api_dashboards_service import ApiDashboardsService
from services.api_organizations_service import ApiOrganizationsService
from services.api_users_service import ApiUsersService
from services.utils import validate_status_code_and_body
from tests.context import TestContext


@pytest.fixture(scope="session", autouse=True)
@allure.title("Creating users.json from template")
def create_users_json():
    if not os.path.exists(settings.USERS_PATH):
        shutil.copy(settings.USERS_TEMPLATE_PATH, settings.USERS_PATH)
        logging.info("Creating users.json")


@pytest.fixture(scope="session", autouse=True)
@allure.title("Creating dashboards.json from template")
def create_dashboards_json():
    if not os.path.exists(settings.DASHBOARDS_PATH):
        shutil.copy(settings.DASHBOARDS_TEMPLATE_PATH, settings.DASHBOARDS_PATH)
        logging.info("Creating dashboards.json")


@pytest.fixture(scope="session", autouse=True)
@allure.title("Creating organizations.json from template")
def create_organizations_json():
    if not os.path.exists(settings.ORGANIZATIONS_PATH):
        shutil.copy(settings.ORGANIZATIONS_TEMPLATE_PATH, settings.ORGANIZATIONS_PATH)
        logging.info("Creating organizations.json")


@pytest.fixture(scope="session")
def test_context() -> TestContext:
    return TestContext()


@pytest.fixture(scope="session")
def session_resources(test_context: TestContext):
    response, org_id = ApiOrganizationsService.create_new_organization()
    validate_status_code_and_body(response, CreateOrganizationSchema, 200)
    test_context.organizations.org_id = int(org_id)
    test_context.organizations.org_name = test_organizations_body["name"]

    response, folder_uid = ApiDashboardsService.create_folder()
    assert response.status_code == 200
    test_context.dashboards.folder_uid = folder_uid

    response, dashboard_uid = ApiDashboardsService.create_dashboard(folder_uid=folder_uid)
    assert response.status_code == 200
    test_context.dashboards.dashboard_uid = dashboard_uid

    response, low_access_user_id = ApiUsersService.create_api_user(low_access_credentials)
    assert response.status_code == 200
    test_context.users.low_access_user_id = low_access_user_id
    ApiOrganizationsService.delete_user_from_org(userid=low_access_user_id)

    response, org_user_id = ApiUsersService.create_api_user(organizations_user)
    assert response.status_code == 200
    test_context.users.organizations_user_id = org_user_id

    response, existing_user_id = ApiUsersService.create_api_user(existing_credentials)
    assert response.status_code == 200
    test_context.users.existing_user_id = existing_user_id

    yield test_context

    _safe_cleanup(test_context)


def _safe_cleanup(test_context: TestContext) -> None:
    for user_id in [
        test_context.users.created_user_id,
        test_context.users.existing_user_id,
        test_context.users.low_access_user_id,
        test_context.users.organizations_user_id,
    ]:
        try:
            if user_id:
                ApiUsersService.delete_api_user(user_id)
        except Exception as exc:
            logging.warning(f"Cleanup user {user_id} failed: {exc}")

    try:
        if test_context.dashboards.dashboard_uid:
            ApiDashboardsService.delete_dashboard(test_context.dashboards.dashboard_uid)
    except Exception as exc:
        logging.warning(f"Cleanup dashboard failed: {exc}")

    try:
        if test_context.dashboards.folder_uid:
            ApiDashboardsService.delete_folder_for_dashboard(test_context.dashboards.folder_uid)
    except Exception as exc:
        logging.warning(f"Cleanup folder failed: {exc}")

    try:
        if test_context.organizations.org_id:
            ApiOrganizationsService.delete_organization(test_context.organizations.org_id)
    except Exception as exc:
        logging.warning(f"Cleanup organization failed: {exc}")
