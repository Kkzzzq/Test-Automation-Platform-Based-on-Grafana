# testing_xuexi

这是整理后的可运行版本说明。目标不是“继续堆功能”，而是先把现有仓库收口成一套**结构自洽、命名一致、入口清楚、测试夹具统一**的集成测试工程。

## 技术栈

- Python 3.11
- Pytest + Allure
- Grafana HTTP API 自动化测试
- Dashboard Hub（FastAPI）
- Grafana SQLite 只读校验
- MySQL + Redis
- Docker Compose
- Prometheus + Locust

## 目录职责

```text
testing_xuexi/
├─ apps/dashboard_hub/          # Dashboard Hub 服务
├─ config/                      # 全局配置
├─ data/                        # 测试数据工厂
├─ helpers/                     # 装饰器、schema
├─ monitoring/                  # Prometheus 配置
├─ perf/                        # Locust 压测脚本
├─ services/                    # Grafana / Dashboard Hub / DB 客户端封装
├─ src/                         # CLI 入口
├─ tests/                       # fixture、上下文、测试用例
├─ docker-compose.yml           # 一键拉起完整环境
└─ .github/workflows/ci.yml     # CI
```

## 这次修复的重点

1. 补齐缺失的 `services/http_client.py` 与 `services/dashboard_hub_service.py`
2. 统一 `tests/conftest.py`、`tests/context.py`、`tests/resource_manager.py`
3. 修复 `data/*` 中函数名与调用方不一致的问题
4. 让 `src/main.py run` 真正执行 pytest，而不是只打印提示
5. 给 `services/utils.py` 补齐断言与 schema 校验工具
6. 将 `DBService` 明确为 **Grafana SQLite 只读仓储**，保留旧名字兼容已有测试
7. 删除不稳定的“低权限用户访问 dashboard 必然 403”假设，改为更稳定的负例
8. 将 SQL 测试改为“API 创建 + SQLite 验证”，不再直接写 Grafana 内部表

## 推荐运行方式

先清理环境：

```bash
docker compose down -v --remove-orphans
```

启动并执行测试：

```bash
docker compose up --build --exit-code-from test-runner
```

本地直接执行 smoke：

```bash
python -m src.main run --marker smoke
```

准备测试资源：

```bash
python -m src.main prepare
```

清理测试资源：

```bash
python -m src.main cleanup
```

## 服务地址

- Grafana: `http://localhost:3000`
- Dashboard Hub: `http://localhost:8000/docs`
- Prometheus: `http://localhost:9090`

## 说明

这份修复版优先解决的是**结构不一致、导入失败、fixture 不统一、CLI 失效、测试假设不稳定**这些问题。
如果你要继续扩展 Dashboard Hub 的业务测试，可以在现在这套基础上继续往 `services/dashboard_hub_service.py` 和 `tests/` 增量添加。
