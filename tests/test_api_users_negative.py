import allure
import pytest

from data.users_credentials import existing_credentials
from helpers.schemas.user_schema import CreateBadRequestSchema, CreateExistingUserSchema
from services.api_users_service import ApiUsersService
from services.utils import assert_json_response, validate_status_code_and_body

pytestmark = pytest.mark.usefixtures("session_resources")

BAD_REQUEST_CASES = [
    pytest.param({}, 400, id="empty-body"),
    pytest.param({"name": "OnlyName"}, 400, id="name-only"),
    pytest.param({"email": "broken-email"}, 400, id="invalid-email-only"),
]


@allure.title("Test create existing user")
@allure.description("This test attempts to create a user that already exists")
@allure.tag("APIUsersService", "Negative")
@allure.id("create_existing_user")
@pytest.mark.NegativeApi
def test_create_existing_user():
    response, _ = ApiUsersService.create_api_user(existing_credentials)
    validate_status_code_and_body(response, CreateExistingUserSchema, 412)
    assert_json_response(response)


@allure.title("Test create bad request")
@allure.description("This test sends invalid payloads for user creation")
@allure.tag("APIUsersService", "Negative")
@allure.id("create_bad_request")
@pytest.mark.NegativeApi
@pytest.mark.parametrize("payload, expected_status", BAD_REQUEST_CASES)
def test_create_bad_request(payload, expected_status):
    response = ApiUsersService.create_bad_request(payload=payload)
    validate_status_code_and_body(response, CreateBadRequestSchema, expected_status)
    assert_json_response(response)
