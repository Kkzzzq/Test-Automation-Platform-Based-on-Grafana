import os


def pytest_sessionstart(session):
    env_path = os.path.join(os.getcwd(), "allure-results", "environment.properties")
    os.makedirs(os.path.dirname(env_path), exist_ok=True)
    with open(env_path, "w", encoding="utf-8") as f:
        f.write("Python=3.11\n")
        f.write("BaseURL=http://grafana:3000\n")
        f.write("Runner=GitHub Actions\n")


