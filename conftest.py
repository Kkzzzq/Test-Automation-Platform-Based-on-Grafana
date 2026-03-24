from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config.settings as settings


def pytest_sessionstart(session):
    results_dir = Path(settings.ALLURE_RESULTS_DIR)
    results_dir.mkdir(parents=True, exist_ok=True)

    env_lines = [
        f"GRAFANA_BASE_URL={settings.GRAFANA_BASE_URL}",
        f"DASHBOARD_HUB_BASE_URL={settings.DASHBOARD_HUB_BASE_URL}",
        f"MYSQL_HOST={settings.MYSQL_HOST}",
        f"REDIS_HOST={settings.REDIS_HOST}",
        "STACK=Grafana + Dashboard Hub + MySQL + Redis + Prometheus",
    ]
    (results_dir / "environment.properties").write_text("\n".join(env_lines), encoding="utf-8")
