from __future__ import annotations

import pytest

from tests.context import TestContext
from tests.resource_manager import (
    ensure_runtime_data_files,
    prepare_session_resources,
    safe_cleanup,
)


@pytest.fixture(scope="session", autouse=True)
def runtime_data_files():
    ensure_runtime_data_files()


@pytest.fixture(scope="session")
def test_context() -> TestContext:
    return TestContext()


@pytest.fixture(scope="session")
def session_resources(test_context: TestContext):
    prepare_session_resources(test_context)
    try:
        yield test_context
    finally:
        safe_cleanup(test_context)
