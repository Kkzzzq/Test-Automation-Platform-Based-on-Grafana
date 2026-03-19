import allure
import pytest

from data.users_credentials import make_random_credentials
from helpers.schemas.user_schema import ChangeUserPassword, CreateUserSchema, DeleteUserSchema
from services.api_users_service import ApiUsersService
from services.db_service import DBService
from services.utils import assert_json_response, validate_status_code_and_body

pytestmark = pytest.mark.usefixtures("session_resources")


@allure.title("Test create API user")
@allure.description("This test attempt create new user with credentials")
@allure.tag("APIUsersService", "Positive")
@allure.id("create_user")
@pytest.mark.PositiveApi
def test_create_user():
    payload = make_random_credentials("CreateUser")
    response, user_id = ApiUsersService.create_api_user(payload)
    validate_status_code_and_body(response, CreateUserSchema, 200)
    assert_json_response(response)

    db_user = DBService.find_user_by_email(payload["email"])
    assert db_user is not None
    assert db_user[0] == payload["login"]
    assert db_user[1] == payload["email"]
    assert db_user[2] == payload["name"]
    assert ApiUsersService.find_user_by_login(payload["login"]) == user_id

    ApiUsersService.delete_api_user(user_id)


@allure.title("Test change API user password")
@allure.description("This test attempt change password for last created user")
@allure.tag("APIUsersService", "Positive")
@allure.id("change_user_password")
@pytest.mark.PositiveApi
def test_change_user_password():
    payload = make_random_credentials("ChangePassword")
    create_response, user_id = ApiUsersService.create_api_user(payload)
    validate_status_code_and_body(create_response, CreateUserSchema, 200)

    response = ApiUsersService.change_user_password(userid=user_id)
    validate_status_code_and_body(response, ChangeUserPassword, 200)
    assert_json_response(response)

    ApiUsersService.delete_api_user(user_id)


@allure.title("Test delete API user")
@allure.description("This test attempt delete last created user")
@allure.tag("APIUsersService", "Positive")
@allure.id("delete_user")
@pytest.mark.PositiveApi
def test_delete_user():
    payload = make_random_credentials("DeleteUser")
    create_response, user_id = ApiUsersService.create_api_user(payload)
    validate_status_code_and_body(create_response, CreateUserSchema, 200)

    response = ApiUsersService.delete_api_user(userid=user_id)
    validate_status_code_and_body(response, DeleteUserSchema, 200)
    assert_json_response(response)

    db_user = DBService.find_user_by_email(payload["email"])
    assert db_user is None
