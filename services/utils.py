import inspect
import logging

from pydantic import ValidationError


def safe_response_body(response):
    try:
        return response.json()
    except ValueError:
        return response.text


def assert_json_response(response):
    content_type = response.headers.get("Content-Type", "")
    assert "application/json" in content_type, (
        f'Expected JSON response, got Content-Type="{content_type}"'
    )


def validate_status_code_and_body(response, schema, status_code, path: list[str] | None = None):
    data = response.json()

    if path:
        for key in path:
            data = data[key]

    try:
        validated = schema.model_validate(data)
    except ValidationError as e:
        logging.error(f"Error in validation Schema: {e}")
        raise AssertionError(f"Response = {data}, but schema validation failed") from e

    assert response.status_code == status_code, (
        f"Expected status code {status_code}, got {response.status_code} - "
        f"{response.json().get('message', '')}"
    )

    for field, value in validated.model_dump().items():
        assert data.get(field) == value, (
            f'Value in "{field}" is unexpected. '
            f"Expected: {value}, got receive: {data.get(field)}"
        )

    logging.info(
        f"Function: {inspect.currentframe().f_code.co_name} successfully validated; "
        f"response: {data}"
    )


def total_log_in_method(response):
    logging.info(
        f"Status={response.status_code}, body={safe_response_body(response)}, url={response.url}"
    )
