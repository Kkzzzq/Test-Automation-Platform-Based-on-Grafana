from __future__ import annotations

import logging
import time

from sqlalchemy.exc import OperationalError

from app.database import Base, engine
from app.models import ShareLink, Subscription  # noqa: F401


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

MAX_ATTEMPTS = 30
SLEEP_SECONDS = 2


def main() -> None:
    last_error: Exception | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Dashboard Hub database is ready; tables ensured.")
            return
        except OperationalError as exc:
            last_error = exc
            logger.warning(
                "Database not ready yet (attempt %s/%s): %s",
                attempt,
                MAX_ATTEMPTS,
                exc,
            )
            time.sleep(SLEEP_SECONDS)

    raise RuntimeError(
        f"Dashboard Hub database did not become ready after {MAX_ATTEMPTS} attempts"
    ) from last_error


if __name__ == "__main__":
    main()
