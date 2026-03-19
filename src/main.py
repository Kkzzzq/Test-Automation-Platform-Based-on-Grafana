import argparse
import json

import pytest

from data.users_credentials import organizations_user
from services.api_dashboards_service import ApiDashboardsService
from services.api_organizations_service import ApiOrganizationsService
from services.api_users_service import ApiUsersService


def prepare_resources() -> dict:
    prepared = {}

    org_response, org_id = ApiOrganizationsService.create_new_organization()
    prepared["organization"] = {
        "status_code": org_response.status_code,
        "org_id": org_id,
    }

    folder_response, folder_uid = ApiDashboardsService.create_folder()
    prepared["folder"] = {
        "status_code": folder_response.status_code,
        "folder_uid": folder_uid,
    }

    dashboard_response, dashboard_uid = ApiDashboardsService.create_dashboard(folder_uid=folder_uid)
    prepared["dashboard"] = {
        "status_code": dashboard_response.status_code,
        "dashboard_uid": dashboard_uid,
    }

    user_response, user_id = ApiUsersService.create_api_user(organizations_user)
    prepared["organization_user"] = {
        "status_code": user_response.status_code,
        "user_id": user_id,
        "login": organizations_user["login"],
    }

    add_response, added_user_id = ApiOrganizationsService.add_user_in_organization(
        org_id=int(org_id),
        body={"loginOrEmail": organizations_user["login"], "role": "Editor"},
    )
    prepared["org_membership"] = {
        "status_code": add_response.status_code,
        "user_id": added_user_id,
    }

    return prepared


def run_tests(marker: str | None = None, keyword: str | None = None) -> int:
    args = ["tests", "-v", "-s", "--tb=short"]

    if marker:
        args.extend(["-m", marker])

    if keyword:
        args.extend(["-k", keyword])

    return pytest.main(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PythonTests CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run pytest suites")
    run_parser.add_argument(
        "--marker",
        help="pytest marker, e.g. PositiveApi / NegativeApi / sql / NegativeDashboard",
    )
    run_parser.add_argument(
        "--keyword",
        help="pytest -k expression",
    )

    subparsers.add_parser("prepare", help="Prepare base API test data and print created ids")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run":
        return run_tests(marker=args.marker, keyword=args.keyword)

    if args.command == "prepare":
        prepared = prepare_resources()
        print(json.dumps(prepared, indent=2, ensure_ascii=False))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
