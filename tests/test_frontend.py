"""前端静态页面和聊天浮窗资源的接口检查。"""

from pathlib import Path

from fastapi.testclient import TestClient

from app.catalog import load_catalog
from app.chat import AssistantDependencies
from app.config import load_settings
from app.main import create_app


def make_app():
    """只验证静态页面时，不创建任何远程模型客户端。"""
    root = Path(__file__).resolve().parents[1]
    settings = load_settings(root)
    deps = AssistantDependencies(
        settings=settings,
        catalog=load_catalog(settings.catalog_path),
        router_client=None,
        answer_client=None,
    )
    return create_app(deps)


def test_root_serves_widget_and_health_survives():
    """根路径返回浮窗页面，健康检查仍保持可用。"""
    with TestClient(make_app()) as client:
        page = client.get("/")
        health = client.get("/health")

    assert page.status_code == 200
    assert page.headers["content-type"].startswith("text/html")
    assert "WillBet AI" in page.text
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
