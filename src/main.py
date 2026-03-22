from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from tests.context import TestContext
from tests.resource_manager import prepare_session_resources, safe_cleanup


def context_to_dict(context: TestContext) -> dict:
    return {
        "organization": {
            "org_id": context.organizations.org_id,
            "org_name": context.organizations.org_name,
        },
        "dashboard": {
            "folder_uid": context.dashboards.folder_uid,
            "dashboard_uid": context.dashboards.dashboard_uid,
            "title": context.dashboards.title,
        },
        "users": {
            "existing_user_id": context.users.existing_user_id,
            "low_access_user_id": context.users.low_access_user_id,
            "organizations_user_id": context.users.organizations_user_id,
        },
    }


def dict_to_context(payload: dict) -> TestContext:
    context = TestContext()

    organization = payload.get("organization", {})
    dashboard = payload.get("dashboard", {})
    users = payload.get("users", {})

    context.organizations.org_id = organization.get("org_id")
    context.organizations.org_name = organization.get("org_name")

    context.dashboards.folder_uid = dashboard.get("folder_uid")
    context.dashboards.dashboard_uid = dashboard.get("dashboard_uid")
    context.dashboards.title = dashboard.get("title") or context.dashboards.title

    context.users.existing_user_id = users.get("existing_user_id")
    context.users.low_access_user_id = users.get("low_access_user_id")
    context.users.organizations_user_id = users.get("organizations_user_id")

    return context


def write_json(data: dict, output: str | None) -> None:
    rendered = json.dumps(data, indent=2, ensure_ascii=False)

    if output:
        Path(output).write_text(rendered, encoding="utf-8")

    print(rendered)


def load_context_from_file(file_path: str) -> TestContext:
    payload = json.loads(Path(file_path).read_text(encoding="utf-8"))
    return dict_to_context(payload)


def prepare_resources(cleanup: bool = False) -> dict:
    context = TestContext()
    prepare_session_resources(context)
    prepared = context_to_dict(context)

    if cleanup:
        safe_cleanup(context)

    return prepared


def cleanup_resources(file_path: str) -> int:
    context = load_context_from_file(file_path)
    safe_cleanup(context)
    return 0


def run_tests(marker: str | None = None, keyword: str | None = None) -> int:
    args = ["tests", "-v", "-s", "--tb=short"]

    if marker:
        args.extend(["-m", marker])

    if keyword:
        args.extend(["-k", keyword])

    return pytest.main(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="testing_xuexi CLI")
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

    prepare_parser = subparsers.add_parser(
        "prepare",
        help="Prepare base API test data and print created ids",
    )
    prepare_parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Clean created resources after printing ids",
    )
    prepare_parser.add_argument(
        "--output",
        help="Optional path to save prepared resource ids as JSON",
    )

    cleanup_parser = subparsers.add_parser(
        "cleanup",
        help="Cleanup resources using a saved JSON file from the prepare command",
    )
    cleanup_parser.add_argument(
        "--from-file",
        required=True,
        help="Path to the JSON file produced by the prepare command",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run":
        return run_tests(marker=args.marker, keyword=args.keyword)

    if args.command == "prepare":
        prepared = prepare_resources(cleanup=args.cleanup)
        write_json(prepared, args.output)
        return 0

    if args.command == "cleanup":
        return cleanup_resources(args.from_file)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
