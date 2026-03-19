import logging
import sqlite3
import time
import traceback
from functools import wraps

import requests


def api_error_handler(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.HTTPError as e:
            logging.error(f"[{func.__name__}]: HTTPError: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logging.error(f"[{func.__name__}]: RequestException: {e}")
            raise
        except Exception as e:
            logging.error(f"[{func.__name__}]: Unexpected error: {e}\n{traceback.format_exc()}")
            raise

    return wrapper


def db_error_handler(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except sqlite3.OperationalError as e:
            logging.error(f"[{func.__name__}]({args},{kwargs}): OperationalError: {e}")
            raise
        except sqlite3.IntegrityError as e:
            logging.error(f"[{func.__name__}]({args},{kwargs}): IntegrityError: {e}")
            raise
        except sqlite3.ProgrammingError as e:
            logging.error(f"[{func.__name__}]({args},{kwargs}): ProgrammingError: {e}")
            raise
        except sqlite3.DatabaseError as e:
            logging.error(f"[{func.__name__}]({args},{kwargs}): DatabaseError: {e}")
            raise
        except sqlite3.Error as e:
            logging.error(f"[{func.__name__}]({args},{kwargs}): Error: {e}")
            raise
        except Exception as e:
            logging.error(f"[{func.__name__}]({args},{kwargs}): Unexpected error: {e}\n{traceback.format_exc()}")
            raise

    return wrapper


def retry(
    attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    retry_on_statuses: tuple[int, ...] = (500, 502, 503, 504),
):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for attempt in range(1, attempts + 1):
                try:
                    result = func(*args, **kwargs)
                    response = result[0] if isinstance(result, tuple) else result

                    if hasattr(response, "status_code") and response.status_code in retry_on_statuses:
                        logging.warning(
                            f"[{func.__name__}] got retryable status {response.status_code} "
                            f"(attempt {attempt}/{attempts})"
                        )
                        if attempt == attempts:
                            return result
                        time.sleep(current_delay)
                        current_delay *= backoff
                        continue

                    return result

                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
                    last_exception = exc
                    logging.warning(
                        f"[{func.__name__}] retryable network error: {exc} "
                        f"(attempt {attempt}/{attempts})"
                    )
                    if attempt == attempts:
                        raise
                    time.sleep(current_delay)
                    current_delay *= backoff

                except requests.exceptions.HTTPError as exc:
                    last_exception = exc
                    status_code = exc.response.status_code if exc.response is not None else None
                    if status_code in retry_on_statuses:
                        logging.warning(
                            f"[{func.__name__}] retryable HTTP error: {status_code} "
                            f"(attempt {attempt}/{attempts})"
                        )
                        if attempt == attempts:
                            raise
                        time.sleep(current_delay)
                        current_delay *= backoff
                        continue
                    raise

            if last_exception:
                raise last_exception

        return wrapper

    return decorator
