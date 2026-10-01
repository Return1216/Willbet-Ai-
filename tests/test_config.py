from pathlib import Path


def test_settings_defaults_and_environment(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-test")
    monkeypatch.setenv("EMBEDDING_API_KEY", "embedding-test")

    from app.config import load_settings

    settings = load_settings(Path(r"C:\Users\Lyy\Desktop\RAG_AGENT"))

    assert settings.deepseek_api_key == "deepseek-test"
    assert settings.embedding_api_key == "embedding-test"
    assert settings.documents_dir == Path(r"C:\Users\Lyy\Desktop\RAG_AGENT\documents")
    assert settings.chroma_dir == Path(r"C:\Users\Lyy\Desktop\RAG_AGENT\storage\chroma")
    assert settings.router_confidence_threshold == 0.75
