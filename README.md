改编至https://github.com/ImeryakovS/PythonTests.git

下面开始按文件给你。

---

## 1. `config/settings.py`

**为什么这样改**

原文件把 `BASIC_AUTH` 写死成了 `("admin","admin")`，README 也明确提醒要手动改这个值。这种写法本地能跑，但不适合 CI、Docker、团队协作。现在把它改成优先读环境变量，没传的时候才回退默认值。这样你本地还能直接跑，CI 里也能走 secrets。当前仓库的硬编码和 README 说明都能证明这里需要改。([GitHub][4])

```python
import os

BASE_DIR = os.environ.get(
    "GITHUB_WORKSPACE",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
)
DATA_DIR = os.path.join(BASE_DIR, "data")

DB_PATH = os.environ.get("GRAFANA_DB_PATH")
if not DB_PATH:
    TESTS_ROOT = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.abspath(
        os.path.join(TESTS_ROOT, "..", "..", "Mygrafana", "Mygrafana", "data", "grafana.db")
    )

USERS_PATH = os.path.join(DATA_DIR, "users.json")
DASHBOARDS_PATH = os.path.join(DATA_DIR, "dashboards.json")
ORGANIZATIONS_PATH = os.path.join(DATA_DIR, "organizations.json")

USERS_TEMPLATE_PATH = os.path.join(DATA_DIR, "users.template.json")
DASHBOARDS_TEMPLATE_PATH = os.path.join(DATA_DIR, "dashboards.template.json")
ORGANIZATIONS_TEMPLATE_PATH = os.path.join(DATA_DIR, "organizations.template.json")

BASE_URL = os.getenv("GRAFANA_BASE_URL", "http://localhost:3000")

GRAFANA_ADMIN_USER = os.getenv("GRAFANA_ADMIN_USER", "admin")
GRAFANA_ADMIN_PASSWORD = os.getenv("GRAFANA_ADMIN_PASSWORD", "admin")
BASIC_AUTH = (GRAFANA_ADMIN_USER, GRAFANA_ADMIN_PASSWORD)

LOW_ACCESS = (
    os.getenv("GRAFANA_LOW_ACCESS_USER", "LowAccess"),
    os.getenv("GRAFANA_LOW_ACCESS_PASSWORD", "test"),
)
```

---

## 2. `data/users_credentials.py`

**为什么这样改**

原文件里 `credentials` 只在模块导入时随机一次，这意味着多条正向测试可能共享同一个随机用户。如果你某个测试先删了它，后面另一个测试继续用它，就会出顺序依赖。现在我保留原来的固定数据 `existing_credentials / low_access_credentials / organizations_user`，但新增 `make_random_credentials()`，让正向用户用例每次自己生成独立用户。当前文件确实就是一次性随机。([GitHub][5])

```python
import random


def make_random_credentials(prefix: str = "Sergey") -> dict:
    rand = random.randint(1000, 9999)
    return {
        "name": f"{prefix}{rand}",
        "email": f"{prefix}{rand}@test.ru",
        "login": f"{prefix}{rand}",
        "password": "password123",
    }


credentials = make_random_credentials("Sergey")

existing_credentials = {
    "name": "SergeySergey",
    "email": "SergeySergey@test.ru",
    "login": "SergeySergey",
    "password": "test123",
}

low_access_credentials = {
    "name": "LowAccess",
    "email": "LowAccess@test.ru",
    "login": "LowAccess",
    "password": "test",
}

organizations_user = {
    "name": "Organization",
    "email": "Organization@test.ru",
    "login": "Organization",
    "password": "test",
}

change_password = {
    "password": "testPassword",
}
```

---

## 3. `helpers/schemas/user_schema.py` 新增

**为什么这样改**

你要求补 schema，这里就是完整补齐。当前测试里已经在导入用户相关 schema，但仓库缺文件。这里把“创建用户 / 改密码 / 删用户 / 已存在用户 / bad request / 403 / 404”都补齐。当前测试文件的导入能证明缺口真实存在；而 `User created / User password updated / User deleted` 这些 message 值来自 Grafana 官方文档。([GitHub][6])

```python
from pydantic import BaseModel


class CreateUserSchema(BaseModel):
    id: int
    message: str = "User created"


class ChangeUserPassword(BaseModel):
    message: str = "User password updated"


class DeleteUserSchema(BaseModel):
    message: str = "User deleted"


class CreateExistingUserSchema(BaseModel):
    message: str
    status: str | None = None


class CreateBadRequestSchema(BaseModel):
    message: str


class GetDashboardWithLowAccessSchema(BaseModel):
    message: str


class Get404DashboardSchema(BaseModel):
    message: str
```

---

## 4. `helpers/schemas/organizations_schema.py` 新增

**为什么这样改**

同理，这个文件也是当前测试已经在导入，但仓库缺失。这里把“创建组织 / 给组织加用户 / 查组织 / 改组织用户角色”补齐。组织相关 message 和返回结构参考的是 Grafana 官方 Organization HTTP API 示例。([GitHub][2])

```python
from pydantic import BaseModel


class OrganizationAddressSchema(BaseModel):
    address1: str = ""
    address2: str = ""
    city: str = ""
    zipCode: str = ""
    state: str = ""
    country: str = ""


class CreateOrganizationSchema(BaseModel):
    orgId: int | str
    message: str = "Organization created"


class AddUserInOrganizations(BaseModel):
    message: str = "User added to organization"
    userId: int


class GetOrganizationsById(BaseModel):
    id: int
    name: str
    address: OrganizationAddressSchema


class UpdateUserInOrg(BaseModel):
    message: str = "Organization user updated"
```

---

## 5. `helpers/decorators.py`

**为什么这样改**

原来的 `retry` 是“任何异常都重试”，作者自己在文件尾注释里也写了“可以只处理网络和 5xx 错误”。这意味着现在的实现其实会把 400/401/403 这种明显的业务错误也当成可重试问题，策略太粗。这里改成只重试：

* `Timeout`
* `ConnectionError`
* 显式 `HTTPError` 且状态码是 5xx
* 或者返回对象本身 status code 是 5xx

原文件和注释都说明这里本来就该收紧。([GitHub][7])

```python
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
```

---

## 6. `helpers/cleanup.py`

**为什么这样改**

这个文件不用大改，但因为 `ApiUsersService.find_user_by_login()` 和 `delete_api_user()` 的签名已经变了，这里顺手同步一下。逻辑还是一样：按 login 找 user，再删。只是现在 service 不再依赖 JSON 状态文件。当前根目录 `conftest.py` 正是通过这个 helper 清理用户。([GitHub][8])

```python
import inspect
import logging

from services.api_users_service import ApiUsersService


def delete_user_by_login(user_data: dict):
    user_id = ApiUsersService.find_user_by_login(user_data["login"])
    if user_id is not None:
        ApiUsersService.delete_api_user(user_id)
        logging.info(
            f'Function: {inspect.currentframe().f_code.co_name}, {user_data["login"]} is deleted'
        )
```

---

## 7. `services/utils.py`

**为什么这样改**

原文件里最核心的问题不是断言，而是它承担了太多“JSON 状态文件读写”职责。这里我把 `write_value_in_json / read_value_in_json / extract_value_in_object / log_get_id` 这一类状态耦合逻辑删掉了，只保留“响应断言”和“日志”。你问“删了什么、移去哪了”——答案是：**状态不再存 JSON 文件，统一移到 `tests/context.py` 和 `tests/conftest.py` 的 fixture 生命周期里了**。当前文件本来就把验证逻辑和 JSON 文件状态混在一起。([GitHub][9])

```python
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
```

---

## 8. `services/db_service.py`

**为什么这样改**

这里基本是保留原逻辑，只补了一个 `find_user_by_login()`。因为在去掉 JSON 状态文件之后，很多地方需要根据 login 直接查 DB 或查 API 做二次验证。原仓库现在只有 `find_user_by_email()`。([GitHub][10])

```python
import logging
import sqlite3
from datetime import datetime

from config.settings import DB_PATH
from helpers.decorators import db_error_handler


class DBService:
    @staticmethod
    @db_error_handler
    def connect():
        conn = sqlite3.connect(DB_PATH)
        logging.info(f"Connected to {DB_PATH}")
        return conn

    @staticmethod
    @db_error_handler
    def create_user(
        login,
        email,
        name,
        password,
        version=0,
        org_id=1,
        is_admin=0,
        created=0,
        updated=0,
    ):
        created = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with DBService.connect() as connection:
            connection.execute(
                "INSERT INTO user (login, email, name, password, version, org_id, is_admin, created, updated) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (login, email, name, password, version, org_id, is_admin, created, updated),
            )
            logging.info(
                f"Created user {login} with parameters "
                f"{email, name, password, version, org_id, is_admin, created, updated}"
            )

    @staticmethod
    @db_error_handler
    def find_user_by_email(email):
        with DBService.connect() as connection:
            cursor = connection.execute(
                "SELECT login, email, name FROM user WHERE email = ?",
                (email,),
            )
            logging.info(f"Found user {email} with parameters {email}")
            return cursor.fetchone()

    @staticmethod
    @db_error_handler
    def find_user_by_login(login):
        with DBService.connect() as connection:
            cursor = connection.execute(
                "SELECT id, login, email, name FROM user WHERE login = ?",
                (login,),
            )
            logging.info(f"Found user by login {login}")
            return cursor.fetchone()

    @staticmethod
    @db_error_handler
    def delete_user_by_login(login):
        with DBService.connect() as connection:
            connection.execute("DELETE FROM user WHERE login = ?", (login,))
            logging.info(f"Deleted user {login}")
```

---

## 9. `services/api_users_service.py`

**为什么这样改**

原文件最核心的问题是：service 一边调 API，一边偷偷写 `users.json`，然后 `change_user_password()` / `delete_api_user()` 还默认去 `users.json` 里找 `userId`。这就是典型的“service 管状态”，职责太重。现在改成：

* `create_api_user()` 返回 `(response, user_id)`
* `change_user_password(userid=...)`
* `delete_api_user(userid=...)`
* `create_bad_request(payload=...)`
* `find_user_by_login(login=...)`

也就是说，**状态从 service 里挪出去了**，由测试或 fixture 显式传入。原文件目前确实就是读写 JSON 的。([GitHub][11])

```python
import logging

import requests
from requests import Response

import config.settings as settings
from data.users_credentials import change_password
from helpers.decorators import api_error_handler, retry
from services.utils import total_log_in_method


class ApiUsersService:
    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def create_api_user(credentials: dict, auth: tuple[str, str] | None = None) -> tuple[Response, int | None]:
        url = f"{settings.BASE_URL}/api/admin/users"
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            url,
            auth=auth or settings.BASIC_AUTH,
            json=credentials,
            headers=headers,
            timeout=10,
        )
        total_log_in_method(response)
        return response, response.json().get("id")

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def find_user_by_login(login: str, auth: tuple[str, str] | None = None) -> int | None:
        url = f"{settings.BASE_URL}/api/users/lookup?loginOrEmail={login}"
        headers = {"Content-Type": "application/json"}
        response = requests.get(
            url,
            auth=auth or settings.BASIC_AUTH,
            headers=headers,
            timeout=10,
        )
        total_log_in_method(response)
        return response.json().get("id")

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def delete_api_user(userid: int, auth: tuple[str, str] | None = None) -> Response | None:
        url = f"{settings.BASE_URL}/api/admin/users/{userid}"
        response = requests.delete(
            url,
            auth=auth or settings.BASIC_AUTH,
            timeout=10,
        )
        total_log_in_method(response)
        if response.status_code == 404:
            logging.warning(f"User {userid} already deleted. Skipping deletion")
            return None
        return response

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def create_bad_request(payload: dict | None = None, auth: tuple[str, str] | None = None) -> Response:
        url = f"{settings.BASE_URL}/api/admin/users"
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            url,
            auth=auth or settings.BASIC_AUTH,
            json=payload or {},
            headers=headers,
            timeout=10,
        )
        total_log_in_method(response)
        return response

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def change_user_password(
        userid: int,
        payload: dict | None = None,
        auth: tuple[str, str] | None = None,
    ) -> Response:
        url = f"{settings.BASE_URL}/api/admin/users/{userid}/password"
        headers = {"Content-Type": "application/json"}
        response = requests.put(
            url,
            auth=auth or settings.BASIC_AUTH,
            json=payload or change_password,
            headers=headers,
            timeout=10,
        )
        total_log_in_method(response)
        return response
```

---

## 10. `services/api_organizations_service.py`

**为什么这样改**

原文件和 users service 一样，问题是依赖 `organizations.json` 和 `users.json` 取 id。现在全部改成显式参数：

* `create_new_organization()` 返回 `(response, org_id)`
* `add_user_in_organization(org_id=...)`
* `get_organizations_by_id(org_id=...)`
* `get_users_in_organization(org_id=...)`
* `update_user_in_org(org_id=..., user_id=..., role=...)`
* `delete_organization(org_id=...)`

也就是说，service 不再去猜“当前组织是谁”，而是调用者明确告诉它。当前文件原本就是大量 `read_value_in_json(...)`。([GitHub][12])

```python
import logging

import requests

import config.settings as settings
from data.organizations_data import add_in_organizations_body, test_organizations_body
from helpers.decorators import api_error_handler, retry
from services.utils import total_log_in_method


class ApiOrganizationsService:
    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def create_new_organization(
        body: dict | None = None,
        auth: tuple[str, str] | None = None,
    ):
        url = f"{settings.BASE_URL}/api/orgs"
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            url,
            auth=auth or settings.BASIC_AUTH,
            json=body or test_organizations_body,
            headers=headers,
            timeout=10,
        )
        total_log_in_method(response)
        return response, response.json().get("orgId")

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def add_user_in_organization(
        org_id: int,
        body: dict | None = None,
        auth: tuple[str, str] | None = None,
    ):
        url = f"{settings.BASE_URL}/api/orgs/{org_id}/users"
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            url,
            auth=auth or settings.BASIC_AUTH,
            json=body or add_in_organizations_body,
            headers=headers,
            timeout=10,
        )
        total_log_in_method(response)
        return response, response.json().get("userId")

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def get_organizations_by_id(org_id: int, auth: tuple[str, str] | None = None):
        url = f"{settings.BASE_URL}/api/orgs/{org_id}"
        response = requests.get(
            url,
            auth=auth or settings.BASIC_AUTH,
            timeout=10,
        )
        total_log_in_method(response)
        return response

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def get_users_in_organization(org_id: int, auth: tuple[str, str] | None = None):
        url = f"{settings.BASE_URL}/api/orgs/{org_id}/users"
        response = requests.get(
            url,
            auth=auth or settings.BASIC_AUTH,
            timeout=10,
        )
        total_log_in_method(response)
        return response

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def update_user_in_org(
        org_id: int,
        user_id: int,
        role: str = "Admin",
        auth: tuple[str, str] | None = None,
    ):
        body = {"role": role}
        url = f"{settings.BASE_URL}/api/orgs/{org_id}/users/{user_id}"
        response = requests.patch(
            url,
            auth=auth or settings.BASIC_AUTH,
            json=body,
            timeout=10,
        )
        total_log_in_method(response)
        return response

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def delete_user_from_org(
        orgid: int = 1,
        userid: int | None = None,
        auth: tuple[str, str] | None = None,
    ):
        if userid is None:
            raise ValueError("userid must be provided")

        url = f"{settings.BASE_URL}/api/orgs/{orgid}/users/{userid}"
        response = requests.delete(
            url,
            auth=auth or settings.BASIC_AUTH,
            timeout=10,
        )
        total_log_in_method(response)

        if response.status_code == 404:
            logging.warning(f"User {userid} already deleted from org. Skipping deletion")
            return None
        return response

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def delete_organization(org_id: int, auth: tuple[str, str] | None = None):
        url = f"{settings.BASE_URL}/api/orgs/{org_id}"
        response = requests.delete(
            url,
            auth=auth or settings.BASIC_AUTH,
            timeout=10,
        )
        total_log_in_method(response)

        if response.status_code == 404:
            logging.warning(f"Organization {org_id} already deleted")
            return None
        return response
```

---

## 11. `services/api_dashboards_service.py`

**为什么这样改**

这个文件原来也是完全靠 `dashboards.json` 传 `folderUid` 和 `dashboardUid`。还额外拆了 `get_dashboard_with_incorrect_auth()`、`get_dashboard_with_low_level_access()`、`get_404_dashboard()` 三个其实只是参数不同的函数。这里把它们统一成：

* `get_dashboard(dashboard_uid, auth=None)`
* `delete_dashboard(dashboard_uid, auth=None)`
* `delete_folder_for_dashboard(folder_uid, auth=None)`

这样你第 4 条参数化也就顺势做了，不用每种错误认证都写一个新 service 方法。原文件里现在确实把这些场景拆成了多个重复函数。([GitHub][13])

```python
import logging

import requests

import config.settings as settings
import data.dashboards_data as data
from helpers.decorators import api_error_handler, retry
from services.utils import total_log_in_method


class ApiDashboardsService:
    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def create_folder(body: dict | None = None, auth: tuple[str, str] | None = None):
        url = f"{settings.BASE_URL}/api/folders"
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            url,
            auth=auth or settings.BASIC_AUTH,
            json=body or data.body_for_create_folder,
            headers=headers,
            timeout=10,
        )
        total_log_in_method(response)
        return response, response.json().get("uid")

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def create_dashboard(
        folder_uid: str,
        body: dict | None = None,
        auth: tuple[str, str] | None = None,
    ):
        url = f"{settings.BASE_URL}/api/dashboards/db"
        headers = {"Content-Type": "application/json"}
        payload = body or data.get_body_for_create_dashboard(folder_uid)
        response = requests.post(
            url,
            auth=auth or settings.BASIC_AUTH,
            json=payload,
            headers=headers,
            timeout=10,
        )
        total_log_in_method(response)
        return response, response.json().get("uid")

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def get_dashboard(dashboard_uid: str, auth: tuple[str, str] | None = None):
        url = f"{settings.BASE_URL}/api/dashboards/uid/{dashboard_uid}"
        headers = {"Content-Type": "application/json"}
        response = requests.get(
            url,
            auth=auth or settings.BASIC_AUTH,
            headers=headers,
            timeout=10,
        )
        total_log_in_method(response)
        return response

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def delete_dashboard(dashboard_uid: str, auth: tuple[str, str] | None = None):
        url = f"{settings.BASE_URL}/api/dashboards/uid/{dashboard_uid}"
        headers = {"Content-Type": "application/json"}
        response = requests.delete(
            url,
            auth=auth or settings.BASIC_AUTH,
            headers=headers,
            timeout=10,
        )
        total_log_in_method(response)

        if response.status_code == 404:
            logging.warning(f"Dashboard {dashboard_uid} already deleted")
            return None
        return response

    @staticmethod
    @api_error_handler
    @retry(attempts=3)
    def delete_folder_for_dashboard(folder_uid: str, auth: tuple[str, str] | None = None):
        url = f"{settings.BASE_URL}/api/folders/{folder_uid}"
        headers = {"Content-Type": "application/json"}
        response = requests.delete(
            url,
            auth=auth or settings.BASIC_AUTH,
            headers=headers,
            timeout=10,
        )
        total_log_in_method(response)

        if response.status_code == 404:
            logging.warning(f"Folder {folder_uid} already deleted")
            return None
        return response
```

---

## 12. `tests/context.py` 新增

**为什么这样改**

这就是“JSON 状态文件被挪去哪里了”的核心答案。所有会话级共享状态，都放进这里的 `TestContext`。这样 service 不用知道“当前的用户是谁”，测试也不用去磁盘读 JSON。你可以把它理解成“本项目自己的小型共享上下文对象”。这一步就是你第 5 条的核心。([GitHub][1])

```python
from dataclasses import dataclass, field


@dataclass
class UserContext:
    created_user_id: int | None = None
    existing_user_id: int | None = None
    low_access_user_id: int | None = None
    organizations_user_id: int | None = None


@dataclass
class DashboardContext:
    folder_uid: str | None = None
    dashboard_uid: str | None = None
    title: str = "Dashboard for API"


@dataclass
class OrganizationContext:
    org_id: int | None = None
    org_name: str | None = None


@dataclass
class TestContext:
    users: UserContext = field(default_factory=UserContext)
    dashboards: DashboardContext = field(default_factory=DashboardContext)
    organizations: OrganizationContext = field(default_factory=OrganizationContext)
```

---

## 13. `tests/conftest.py`

**为什么这样改**

这个文件是整个重构里最关键的地方。

原文件有两个问题：

1. 有两个同名 `create_dashboards_jsons`，后者会覆盖前者。
2. 它负责创建资源，但不负责把这些资源结构化管理，只是隐式依赖 service 写 JSON。([GitHub][14])

现在我把它改成两层：

* 第一层，保留你点名要求的 `create_dashboards_json`、`create_organizations_json` 名字，只做模板文件复制，保持兼容。
* 第二层，新增 `test_context` 和 `session_resources`，真正的共享状态都在这里管理。
* teardown `_safe_cleanup()` 也放到这里。

也就是说，**删掉的不是“准备数据”这件事，而是“靠 JSON 文件传递状态”这件事**。资源准备和资源清理都还在，只是搬到了 fixture 生命周期里。([GitHub][14])

```python
import logging
import os
import shutil

import allure
import pytest

from config import settings
from data.organizations_data import test_organizations_body
from data.users_credentials import existing_credentials, low_access_credentials, organizations_user
from helpers.schemas.organizations_schema import CreateOrganizationSchema
from services.api_dashboards_service import ApiDashboardsService
from services.api_organizations_service import ApiOrganizationsService
from services.api_users_service import ApiUsersService
from services.utils import validate_status_code_and_body
from tests.context import TestContext


@pytest.fixture(scope="session", autouse=True)
@allure.title("Creating users.json from template")
def create_users_json():
    if not os.path.exists(settings.USERS_PATH):
        shutil.copy(settings.USERS_TEMPLATE_PATH, settings.USERS_PATH)
        logging.info("Creating users.json")


@pytest.fixture(scope="session", autouse=True)
@allure.title("Creating dashboards.json from template")
def create_dashboards_json():
    if not os.path.exists(settings.DASHBOARDS_PATH):
        shutil.copy(settings.DASHBOARDS_TEMPLATE_PATH, settings.DASHBOARDS_PATH)
        logging.info("Creating dashboards.json")


@pytest.fixture(scope="session", autouse=True)
@allure.title("Creating organizations.json from template")
def create_organizations_json():
    if not os.path.exists(settings.ORGANIZATIONS_PATH):
        shutil.copy(settings.ORGANIZATIONS_TEMPLATE_PATH, settings.ORGANIZATIONS_PATH)
        logging.info("Creating organizations.json")


@pytest.fixture(scope="session")
def test_context() -> TestContext:
    return TestContext()


@pytest.fixture(scope="session")
def session_resources(test_context: TestContext):
    response, org_id = ApiOrganizationsService.create_new_organization()
    validate_status_code_and_body(response, CreateOrganizationSchema, 200)
    test_context.organizations.org_id = int(org_id)
    test_context.organizations.org_name = test_organizations_body["name"]

    response, folder_uid = ApiDashboardsService.create_folder()
    assert response.status_code == 200
    test_context.dashboards.folder_uid = folder_uid

    response, dashboard_uid = ApiDashboardsService.create_dashboard(folder_uid=folder_uid)
    assert response.status_code == 200
    test_context.dashboards.dashboard_uid = dashboard_uid

    response, low_access_user_id = ApiUsersService.create_api_user(low_access_credentials)
    assert response.status_code == 200
    test_context.users.low_access_user_id = low_access_user_id
    ApiOrganizationsService.delete_user_from_org(userid=low_access_user_id)

    response, org_user_id = ApiUsersService.create_api_user(organizations_user)
    assert response.status_code == 200
    test_context.users.organizations_user_id = org_user_id

    response, existing_user_id = ApiUsersService.create_api_user(existing_credentials)
    assert response.status_code == 200
    test_context.users.existing_user_id = existing_user_id

    yield test_context

    _safe_cleanup(test_context)


def _safe_cleanup(test_context: TestContext) -> None:
    for user_id in [
        test_context.users.created_user_id,
        test_context.users.existing_user_id,
        test_context.users.low_access_user_id,
        test_context.users.organizations_user_id,
    ]:
        try:
            if user_id:
                ApiUsersService.delete_api_user(user_id)
        except Exception as exc:
            logging.warning(f"Cleanup user {user_id} failed: {exc}")

    try:
        if test_context.dashboards.dashboard_uid:
            ApiDashboardsService.delete_dashboard(test_context.dashboards.dashboard_uid)
    except Exception as exc:
        logging.warning(f"Cleanup dashboard failed: {exc}")

    try:
        if test_context.dashboards.folder_uid:
            ApiDashboardsService.delete_folder_for_dashboard(test_context.dashboards.folder_uid)
    except Exception as exc:
        logging.warning(f"Cleanup folder failed: {exc}")

    try:
        if test_context.organizations.org_id:
            ApiOrganizationsService.delete_organization(test_context.organizations.org_id)
    except Exception as exc:
        logging.warning(f"Cleanup organization failed: {exc}")
```

---

## 14. `tests/test_api_users_positive.py`

**为什么这样改**

原文件的问题不是“断言不够”这么简单，而是三条正向用例可能共享同一个 `credentials` 用户，存在顺序耦合。现在改成每个测试自己生成一个用户、自己清理自己的用户，测试就独立了。当前正向文件确实依赖单个 `credentials`。([GitHub][5])

另外这里也补了更真实的断言：

* 校验 `Content-Type`
* 反查 DB
* 再通过 API 查 login 对应的 user_id

```python
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
```

---

## 15. `tests/test_api_users_negative.py`

**为什么这样改**

你第 4 条要求参数化，这里就是完整落地。原来 bad request 只有一种；现在把多种无效 payload 都参数化了。当前负向文件确实就是单一场景。([GitHub][6])

```python
import allure
import pytest

from data.users_credentials import existing_credentials
from helpers.schemas.user_schema import CreateBadRequestSchema, CreateExistingUserSchema
from services.api_users_service import ApiUsersService
from services.utils import assert_json_response, validate_status_code_and_body

pytestmark = pytest.mark.usefixtures("session_resources")

BAD_REQUEST_CASES = [
    pytest.param({}, 400, id="empty-body"),
    pytest.param({"name": "OnlyName"}, 400, id="name-only"),
    pytest.param({"email": "broken-email"}, 400, id="invalid-email-only"),
]


@allure.title("Test create existing user")
@allure.description("This test attempts to create a user that already exists")
@allure.tag("APIUsersService", "Negative")
@allure.id("create_existing_user")
@pytest.mark.NegativeApi
def test_create_existing_user():
    response, _ = ApiUsersService.create_api_user(existing_credentials)
    validate_status_code_and_body(response, CreateExistingUserSchema, 412)
    assert_json_response(response)


@allure.title("Test create bad request")
@allure.description("This test sends invalid payloads for user creation")
@allure.tag("APIUsersService", "Negative")
@allure.id("create_bad_request")
@pytest.mark.NegativeApi
@pytest.mark.parametrize("payload, expected_status", BAD_REQUEST_CASES)
def test_create_bad_request(payload, expected_status):
    response = ApiUsersService.create_bad_request(payload=payload)
    validate_status_code_and_body(response, CreateBadRequestSchema, expected_status)
    assert_json_response(response)
```

---

## 16. `tests/test_api_organizations_positive.py`

**为什么这样改**

原文件其实已经有组织相关的正向思路，但它依赖 service 从 JSON 里读 org_id 和 user_id。现在全部改为显式从 `test_context` 拿。这样“当前组织是谁”“当前组织用户是谁”都很清楚。当前文件也确实已经在导入组织 schema。([GitHub][2])

这里还补了你第 8 条要求的“权限变更后二次验证”：`PATCH` 改完角色以后，再调用一次 `get_users_in_organization()` 反查 role 是否真的变成 `Admin`。官方文档也有这个接口和返回结构。([Grafana Labs][15])

```python
import allure
import pytest

from data.users_credentials import organizations_user
from helpers.schemas.organizations_schema import (
    AddUserInOrganizations,
    GetOrganizationsById,
    UpdateUserInOrg,
)
from services.api_organizations_service import ApiOrganizationsService
from services.utils import assert_json_response, validate_status_code_and_body

pytestmark = pytest.mark.usefixtures("session_resources")


@allure.title("Test add new user in organization")
@allure.description("This test attempt to add new user in organization")
@allure.tag("ApiOrganizationsService", "Positive")
@allure.id("add_user_in_organization")
@pytest.mark.PositiveApi
def test_add_user_in_organization(test_context):
    response, user_id = ApiOrganizationsService.add_user_in_organization(
        org_id=test_context.organizations.org_id,
        body={"loginOrEmail": organizations_user["login"], "role": "Editor"},
    )
    validate_status_code_and_body(response, AddUserInOrganizations, 200)
    assert_json_response(response)
    assert user_id == test_context.users.organizations_user_id


@allure.title("Test get organizations by id")
@allure.description("This test attempt get organizations by id")
@allure.tag("ApiOrganizationsService", "Positive")
@allure.id("get_organizations_by_id")
@pytest.mark.PositiveApi
def test_get_organizations_by_id(test_context):
    response = ApiOrganizationsService.get_organizations_by_id(test_context.organizations.org_id)
    validate_status_code_and_body(response, GetOrganizationsById, 200)
    assert_json_response(response)
    assert response.json()["name"] == test_context.organizations.org_name


@allure.title("Test update user permissions in org")
@allure.description("This test attempt update user permissions in org")
@allure.tag("ApiOrganizationsService", "Positive")
@allure.id("update_user_in_org")
@pytest.mark.PositiveApi
def test_update_user_in_org(test_context):
    response = ApiOrganizationsService.update_user_in_org(
        org_id=test_context.organizations.org_id,
        user_id=test_context.users.organizations_user_id,
        role="Admin",
    )
    validate_status_code_and_body(response, UpdateUserInOrg, 200)
    assert_json_response(response)

    users_response = ApiOrganizationsService.get_users_in_organization(
        test_context.organizations.org_id
    )
    assert users_response.status_code == 200
    target_user = next(
        user
        for user in users_response.json()
        if user["userId"] == test_context.users.organizations_user_id
    )
    assert target_user["role"] == "Admin"
```

---

## 17. `tests/test_api_dashboards_positive.py`

**为什么这样改**

原文件只做了最基础的 schema 校验。这里补了你第 8 条提到的“更真实断言”：

* `Content-Type`
* dashboard title
* `meta.folderUid`

当前 dashboard schema 里 title 默认值就是 `"Dashboard for API"`，数据文件里 dashboard body 也确实是这个 title。([GitHub][16])

```python
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
```

---

## 18. `tests/test_api_dashboards_negative.py`

**为什么这样改**

这部分是参数化收益最大的地方。原文件把“错误认证”“低权限”“404”分成不同测试，但 service 里还有额外的重复函数。现在 service 统一，测试层做参数化：

* 多组错误 Basic Auth
* 多种不存在的 uid 后缀
* 低权限单独保留

当前原文件确实已经有这些负向场景，只是没有参数化。([GitHub][17])

```python
import allure
import pytest

from helpers.schemas.dashboards_schema import GetDashboardsWithIncorrectCredentialsSchema
from helpers.schemas.user_schema import Get404DashboardSchema, GetDashboardWithLowAccessSchema
from services.api_dashboards_service import ApiDashboardsService
from services.utils import assert_json_response, validate_status_code_and_body

pytestmark = pytest.mark.usefixtures("session_resources")

BAD_AUTH_CASES = [
    pytest.param(("admin2", "admin2"), id="wrong-user-and-password"),
    pytest.param(("admin", "wrong-password"), id="wrong-password"),
    pytest.param(("wrong-user", "admin"), id="wrong-user"),
]

BAD_UID_SUFFIXES = [
    pytest.param("-404", id="suffix-404"),
    pytest.param("-missing", id="suffix-missing"),
]


@allure.title("Test get dashboard with incorrect auth")
@allure.description("This test attempts to get dashboard with invalid basic auth")
@allure.tag("ApiDashboardsService", "Negative")
@allure.id("get_dashboard_with_incorrect_auth")
@pytest.mark.NegativeApi
@pytest.mark.parametrize("auth", BAD_AUTH_CASES)
def test_get_dashboard_with_incorrect_auth(auth, test_context):
    response = ApiDashboardsService.get_dashboard(
        dashboard_uid=test_context.dashboards.dashboard_uid,
        auth=auth,
    )
    validate_status_code_and_body(response, GetDashboardsWithIncorrectCredentialsSchema, 401)
    assert_json_response(response)


@allure.title("Test get dashboard from user with low access in the system")
@allure.description("This test attempts to get dashboard from low-access user")
@allure.tag("ApiDashboardsService", "Negative")
@allure.id("get_dashboard_with_low_level_access")
@pytest.mark.NegativeDashboard
def test_get_dashboard_with_low_level_access(test_context):
    response = ApiDashboardsService.get_dashboard(
        dashboard_uid=test_context.dashboards.dashboard_uid,
        auth=("LowAccess", "test"),
    )
    validate_status_code_and_body(response, GetDashboardWithLowAccessSchema, 403)
    assert_json_response(response)


@allure.title("Test get 404 dashboard")
@allure.description("This test attempts to get non-existing dashboard by uid")
@allure.tag("ApiDashboardsService", "Negative")
@allure.id("get_404_dashboard")
@pytest.mark.NegativeApi
@pytest.mark.parametrize("suffix", BAD_UID_SUFFIXES)
def test_get_404_dashboard(suffix, test_context):
    invalid_uid = f"{test_context.dashboards.dashboard_uid}{suffix}"
    response = ApiDashboardsService.get_dashboard(dashboard_uid=invalid_uid)
    validate_status_code_and_body(response, Get404DashboardSchema, 404)
    assert_json_response(response)
```

---

## 19. `conftest.py`（根目录）

**为什么这样改**

原根目录 `conftest.py` 做了三件事：

* 动态注册 marker
* 写 Allure 环境文件
* `pytest_sessionfinish()` 时全局清理

现在其中前两件要拆开看：

第一，marker 不该在代码里动态注册，应该统一放到 `pytest.ini`。当前根目录 `conftest.py` 的 `pytest_configure()` 正是在动态注册 `NegativeApi / PositiveApi`。([GitHub][8])

第二，cleanup 不该在根目录 `sessionfinish` 里靠 JSON 去做，因为真正的资源创建现在已经挪到 `tests/conftest.py` 的 `session_resources` fixture 里了，所以 cleanup 也应该跟着挪过去。这样资源生命周期才闭环。当前根目录 `conftest.py` 现在确实还是靠 `delete_user_by_login()` 和无参 `delete_dashboard()` 这类旧逻辑清理。([GitHub][8])

所以这个文件现在只保留写 Allure 环境信息。

```python
import os


def pytest_sessionstart(session):
    env_path = os.path.join(os.getcwd(), "allure-results", "environment.properties")
    os.makedirs(os.path.dirname(env_path), exist_ok=True)
    with open(env_path, "w", encoding="utf-8") as f:
        f.write("Python=3.11\n")
        f.write("BaseURL=http://grafana:3000\n")
        f.write("Runner=GitHub Actions\n")
```

---

## 20. `pytest.ini`

**为什么这样改**

当前 `pytest.ini` 里只注册了 `api/ui/smoke/regression`，但测试里实际使用的是 `PositiveApi / NegativeApi / NegativeDashboard / sql`。`sql` 在 `test_sql_users.py` 里已经存在，所以这里不是我新发明的，是把它统一注册进去。当前测试文件和 ini 都能证明这个不一致问题。([GitHub][18])

```ini
[pytest]
pythonpath = .
markers =
    PositiveApi: positive API scenarios
    NegativeApi: negative API scenarios
    NegativeDashboard: negative dashboard permission scenarios
    sql: sqlite validation tests
    api: generic API tests
    ui: generic UI tests
    smoke: smoke tests
    regression: regression tests

addopts = -v -s --tb=short --durations=5 --color=yes

log_cli = true
log_cli_level = INFO
log_cli_format = %(asctime)s [%(levelname)8s] %(message)s
log_cli_date_format = %Y-%m-%d %H:%M:%S
```

---

## 21. `src/main.py`

**为什么这样改**

你第 9 条要求把它改成 CLI。当前这个文件是空的，所以最适合一次性做完整。现在它支持两件事：

* `run`：按 marker 或关键字跑 pytest
* `prepare`：一键准备组织、folder、dashboard、organization user

当前 `src/main.py` 的确是空文件。([GitHub][19])

```python
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
```

---

## 22. `docker-compose.yml`

**为什么这样改**

你第 6 条说不要把管理员账号密码写死。这里除了 `settings.py` 要读环境变量，`docker-compose.yml` 也必须配合，不然容器里创建出来的 Grafana 还是老的默认值。另一个关键点是：Grafana 官方 Organization API 文档明确说，创建组织要允许 `GF_USERS_ALLOW_ORG_CREATE=true` 或等价配置，否则 `POST /api/orgs` 不工作。当前仓库 README 也说明本项目依赖 Docker 跑 Grafana 和测试。([GitHub][1])

```yaml
services:
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
    networks:
      - my-net
    environment:
      GF_SECURITY_ADMIN_USER: ${GRAFANA_ADMIN_USER:-admin}
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD:-admin}
      GF_USERS_ALLOW_ORG_CREATE: "true"

  test-runner:
    build:
      context: .
    volumes:
      - grafana-data:/var/lib/grafana
      - ./allure-results:/app/allure-results
      - ./allure-report:/app/allure-report
    networks:
      - my-net
    environment:
      GRAFANA_DB_PATH: /var/lib/grafana/grafana.db
      GRAFANA_BASE_URL: http://grafana:3000
      GRAFANA_ADMIN_USER: ${GRAFANA_ADMIN_USER:-admin}
      GRAFANA_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD:-admin}
      GRAFANA_LOW_ACCESS_USER: ${GRAFANA_LOW_ACCESS_USER:-LowAccess}
      GRAFANA_LOW_ACCESS_PASSWORD: ${GRAFANA_LOW_ACCESS_PASSWORD:-test}
    command: pytest /app/tests --alluredir=/app/allure-results

volumes:
  grafana-data:

networks:
  my-net:
```

---

## 23. `.github/workflows/ci.yml`

**为什么这样改**

你要第 6 条落地成 secrets，那 CI 也得配。不然本地读环境变量、CI 仍然空着，就没有意义。当前仓库 README 也明确说 CI/CD 是 GitHub Actions。([GitHub][1])

```yaml
name: Run PyTests
on:
  workflow_dispatch:

permissions:
  contents: write
  actions: read

jobs:
  run-tests:
    runs-on: ubuntu-latest
    env:
      GRAFANA_ADMIN_USER: ${{ secrets.GRAFANA_ADMIN_USER }}
      GRAFANA_ADMIN_PASSWORD: ${{ secrets.GRAFANA_ADMIN_PASSWORD }}
      GRAFANA_LOW_ACCESS_USER: ${{ secrets.GRAFANA_LOW_ACCESS_USER }}
      GRAFANA_LOW_ACCESS_PASSWORD: ${{ secrets.GRAFANA_LOW_ACCESS_PASSWORD }}

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Install docker compose
        run: |
          sudo curl -L "https://github.com/docker/compose/releases/download/v2.22.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
          sudo chmod +x /usr/local/bin/docker-compose

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: 3.11

      - name: Install Allure CLI
        run: |
          sudo apt update
          sudo apt install -y default-jre
          wget https://github.com/allure-framework/allure2/releases/download/2.27.0/allure-2.27.0.tgz
          tar -zxvf allure-2.27.0.tgz
          sudo mv allure-2.27.0 /opt/allure
          sudo ln -s /opt/allure/bin/allure /usr/bin/allure

      - name: Full cleanup (local volumes and reports)
        run: |
          docker-compose down -v --remove-orphans || true
          rm -rf allure-results allure-report gh-pages || true

      - name: Build test-runner container
        run: docker build -t test-runner .

      - name: Start Grafana
        run: docker-compose up -d grafana

      - name: Show Grafana container logs (after run)
        run: docker-compose logs grafana

      - name: Wait for Grafana to be ready
        id: grafana_check
        run: |
          docker ps
          docker inspect pythontests-grafana-1 --format='Status: {{.State.Status}}, ExitCode: {{.State.ExitCode}}, StartedAt: {{.State.StartedAt}}, FinishedAt: {{.State.FinishedAt}}'
          for i in {1..60}; do
            result=$(curl -s http://localhost:3000/api/health || true)
            if (( i % 10 == 0 )); then
              echo "--- Grafana logs ---"
              docker-compose logs --tail=20 grafana
            fi
            echo "Health check $i: $result"

            if echo "$result" | grep -q '"database": *"ok"'; then
              echo "✅ Grafana is ready!"
              break
            fi

            sleep 2
          done

          if ! echo "$result" | grep -q '"database": *"ok"'; then
            echo '❌ Grafana did not start in time!'
            echo "grafana_ready=false" >> $GITHUB_OUTPUT
            docker-compose logs grafana
            exit 1
          fi

          echo "✅ Grafana is ready!"
          echo "grafana_ready=true" >> $GITHUB_OUTPUT

      - name: Run tests
        id: tests
        run: docker-compose run --rm test-runner
        continue-on-error: true

      - name: Clean up containers
        run: docker-compose down -v --remove-orphans

      - name: Clone gh-pages branch
        if: always()
        run: |
          git clone --depth 1 --branch gh-pages https://x-access-token:${{ secrets.GITHUB_TOKEN }}@github.com/${{ github.repository }} gh-pages

      - name: Fix permissions on allure-results
        if: always()
        run: sudo chmod -R 777 allure-results

      - name: Restore history from previous report
        if: always()
        run: |
          if [ -d gh-pages/allure-report/history ]; then
            mkdir -p allure-results/history
            cp -r gh-pages/allure-report/history/* allure-results/history/
          fi

      - name: Fix permissions on allure-report
        if: always()
        run: sudo chmod -R 777 allure-report

      - name: Generate Allure report
        if: always()
        run: allure generate allure-results -o allure-report
        continue-on-error: true

      - name: Deploy Allure report to GitHub Pages
        if: steps.grafana_check.outputs.grafana_ready == 'true' && (steps.tests.outcome == 'success' || steps.tests.outcome == 'failure')
        run: |
          git config --global user.email "actions@github.com"
          git config --global user.name "GitHub Actions"

          cd gh-pages
          rm -rf allure-report
          cp -r ../allure-report ./allure-report
          touch .nojekyll

          git add .
          git commit -m "🚀 Update Allure report" || true
          git push origin gh-pages

      - name: Final clean up
        run: docker-compose down
```

---D

## 25. 最后的前因后果，再用最直白的话说一遍

这次完整修复，最核心的不是“补几个文件”，而是把项目从“**service + JSON 状态文件驱动**”改成“**service + fixture/context 驱动**”。

原来：

```python
service -> 写 users.json
test -> 读 users.json
sessionfinish -> 再根据 users.json 清理
```

现在：

```python
service -> 返回 response 和 id
fixture/context -> 保存共享状态
test -> 显式从 context 拿 id
fixture teardown -> 统一清理
```
