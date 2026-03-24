import allure
import pytest

from helpers.schemas.organizations_schema import (
    AddUserInOrganizations,
    CreateOrganizationResponse,
    GetOrganizationsById,
    UpdateUserInOrg,
)
from services.api_organizations_service import ApiOrganizationsService


@allure.title("Create organization successfully")
@pytest.mark.PositiveOrganizations
@pytest.mark.smoke
def test_create_organization_success(session_context):
    response = ApiOrganizationsService.get_organization_by_id(session_context.org_id)
    assert response.status_code == 200

    data = GetOrganizationsById(**response.json())
    assert data.id == session_context.org_id
    assert data.name == session_context.organizations.org_name


@allure.title("Add user to organization successfully")
@pytest.mark.PositiveOrganizations
def test_add_user_in_organization(session_context):
    response = ApiOrganizationsService.add_user_in_organization(
        org_id=session_context.org_id,
        user_id=session_context.organizations_user_id,
        role="Viewer",
    )
    assert response.status_code in (200, 409)

    if response.status_code == 200:
        data = AddUserInOrganizations(**response.json())
        assert data.userId == session_context.organizations_user_id


@allure.title("Update user role in organization successfully")
@pytest.mark.PositiveOrganizations
def test_update_user_in_org(session_context):
    add_response = ApiOrganizationsService.add_user_in_organization(
        org_id=session_context.org_id,
        user_id=session_context.organizations_user_id,
        role="Viewer",
    )
    assert add_response.status_code in (200, 409)

    response = ApiOrganizationsService.update_user_role_in_organization(
        org_id=session_context.org_id,
        user_id=session_context.organizations_user_id,
        role="Editor",
    )
    assert response.status_code == 200

    data = UpdateUserInOrg(**response.json())
    assert data.message


@allure.title("Get organization by id successfully")
@pytest.mark.PositiveOrganizations
def test_get_organization_by_id(session_context):
    response = ApiOrganizationsService.get_organization_by_id(session_context.org_id)
    assert response.status_code == 200

    data = GetOrganizationsById(**response.json())
    assert data.id == session_context.org_id
    assert data.name == session_context.organizations.org_name
