from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# 唯一运行标准：只支持 Docker Compose
DB_PATH = "/var/lib/grafana/grafana.db"
BASE_URL = "http://grafana:3000"

# 固定管理员账号
GRAFANA_ADMIN_USER = "admin"
GRAFANA_ADMIN_PASSWORD = "admin"
BASIC_AUTH = (GRAFANA_ADMIN_USER, GRAFANA_ADMIN_PASSWORD)

# 固定低权限账号
GRAFANA_LOW_ACCESS_USER = "LowAccess"
GRAFANA_LOW_ACCESS_PASSWORD = "test"
LOW_ACCESS = (GRAFANA_LOW_ACCESS_USER, GRAFANA_LOW_ACCESS_PASSWORD)

USERS_PATH = str(DATA_DIR / "users.json")
DASHBOARDS_PATH = str(DATA_DIR / "dashboards.json")
ORGANIZATIONS_PATH = str(DATA_DIR / "organizations.json")

USERS_TEMPLATE_PATH = str(DATA_DIR / "users.template.json")
DASHBOARDS_TEMPLATE_PATH = str(DATA_DIR / "dashboards.template.json")
ORGANIZATIONS_TEMPLATE_PATH = str(DATA_DIR / "organizations.template.json")

ALLURE_RESULTS_DIR = "allure-results"
