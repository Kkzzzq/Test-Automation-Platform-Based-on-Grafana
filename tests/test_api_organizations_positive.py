import allure
import pytest

from data.users_credentials import organizations_user
from helpers.schemas.organizations_schema import (
    AddUserInOrganizations,
    GetOrganizationsById,
    UpdateUserInOrg,
)
from services.api_organizations_service import ApiOrganizationsService
from services.utils import assert_json_response, validate_status_code_and_body

pytestmark = pytest.mark.usefixtures("session_resources")


@allure.title("Test add new user in organization")
@allure.description("This test attempt to add new user in organization")
@allure.tag("ApiOrganizationsService", "Positive")
@allure.id("add_user_in_organization")
@pytest.mark.PositiveApi
def test_add_user_in_organization(test_context):
    response, user_id = ApiOrganizationsService.add_user_in_organization(
        org_id=test_context.organizations.org_id,
        body={"loginOrEmail": organizations_user["login"], "role": "Editor"},
    )
    validate_status_code_and_body(response, AddUserInOrganizations, 200)
    assert_json_response(response)
    assert user_id == test_context.users.organizations_user_id


@allure.title("Test get organizations by id")
@allure.description("This test attempt get organizations by id")
@allure.tag("ApiOrganizationsService", "Positive")
@allure.id("get_organizations_by_id")
@pytest.mark.PositiveApi
def test_get_organizations_by_id(test_context):
    response = ApiOrganizationsService.get_organizations_by_id(test_context.organizations.org_id)
    validate_status_code_and_body(response, GetOrganizationsById, 200)
    assert_json_response(response)
    assert response.json()["name"] == test_context.organizations.org_name


@allure.title("Test update user permissions in org")
@allure.description("This test attempt update user permissions in org")
@allure.tag("ApiOrganizationsService", "Positive")
@allure.id("update_user_in_org")
@pytest.mark.PositiveApi
def test_update_user_in_org(test_context):
    response = ApiOrganizationsService.update_user_in_org(
        org_id=test_context.organizations.org_id,
        user_id=test_context.users.organizations_user_id,
        role="Admin",
    )
    validate_status_code_and_body(response, UpdateUserInOrg, 200)
    assert_json_response(response)

    users_response = ApiOrganizationsService.get_users_in_organization(
        test_context.organizations.org_id
    )
    assert users_response.status_code == 200
    target_user = next(
        user
        for user in users_response.json()
        if user["userId"] == test_context.users.organizations_user_id
    )
    assert target_user["role"] == "Admin"
