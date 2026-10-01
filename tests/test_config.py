"""配置默认值和环境变量读取测试。"""

from pathlib import Path


def test_settings_defaults_and_environment(monkeypatch):
    """验证环境变量覆盖本地配置，并保持文档和索引路径位于项目内。"""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-test")
    monkeypatch.setenv("EMBEDDING_API_KEY", "embedding-test")

    from app.config import load_settings

    settings = load_settings(Path(__file__).resolve().parents[1])

    assert settings.deepseek_api_key == "deepseek-test"
    assert settings.embedding_api_key == "embedding-test"
    assert settings.documents_dir == (Path(__file__).resolve().parents[1] / "documents")
    assert settings.chroma_dir == (Path(__file__).resolve().parents[1] / "storage" / "chroma")
    assert settings.router_confidence_threshold == 0.75
