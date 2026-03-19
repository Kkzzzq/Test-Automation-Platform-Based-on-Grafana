import allure
import pytest

from helpers.schemas.dashboards_schema import GetDashboardSchema
from services.api_dashboards_service import ApiDashboardsService
from services.utils import assert_json_response, validate_status_code_and_body

pytestmark = pytest.mark.usefixtures("session_resources")


@allure.title("Test get dashboard in folder")
@allure.description("This test attempt to get the dashboard in folder")
@allure.tag("ApiDashboardsService", "Positive")
@allure.id("get_dashboard")
@pytest.mark.PositiveApi
def test_get_dashboard(test_context):
    response = ApiDashboardsService.get_dashboard(test_context.dashboards.dashboard_uid)
    validate_status_code_and_body(response, GetDashboardSchema, 200, path=["dashboard"])
    assert_json_response(response)

    body = response.json()
    assert body["dashboard"]["title"] == test_context.dashboards.title
    assert body["meta"]["folderUid"] == test_context.dashboards.folder_uid
