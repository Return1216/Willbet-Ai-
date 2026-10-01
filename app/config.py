"""应用配置。

已有环境变量优先于项目根目录的 `.env`；加载配置本身不校验远程凭证。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional during bootstrap
    load_dotenv = None


@dataclass(frozen=True)
class Settings:
    """运行时配置和各类本地路径。"""

    root_dir: Path
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str
    embedding_api_key: str
    embedding_base_url: str
    embedding_model: str
    embedding_dimension: int
    documents_dir: Path
    chroma_dir: Path
    catalog_path: Path
    router_confidence_threshold: float = 0.75
    retrieval_min_score: float = 0.25
    embedding_batch_size: int = 10
    cors_origins: tuple[str, ...] = ("http://localhost", "http://127.0.0.1")

    def require_deepseek_key(self) -> str:
        """供调用方检查 DeepSeek Key 是否为空，不验证远程认证是否成功。"""

        if not self.deepseek_api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is required for answer generation")
        return self.deepseek_api_key

    def require_embedding_key(self) -> str:
        """供索引入口检查 Embedding Key 是否为空，不验证远程认证是否成功。"""

        if not self.embedding_api_key:
            raise RuntimeError("EMBEDDING_API_KEY is required for document indexing or retrieval")
        return self.embedding_api_key


def load_settings(root_dir: Path | None = None) -> Settings:
    """加载配置，不在导入阶段访问任何远程服务。"""

    root = Path(root_dir or Path(__file__).resolve().parents[1]).resolve()
    if load_dotenv is not None:
        load_dotenv(root / ".env")

    def env(name: str, default: str = "") -> str:
        """读取配置字符串，去除复制粘贴时可能带入的首尾空白。"""
        return os.getenv(name, default).strip()

    # 导入 app 后，文档、索引和目录文件的位置不随工作目录变化。
    return Settings(
        root_dir=root,
        deepseek_api_key=env("DEEPSEEK_API_KEY"),
        deepseek_base_url=env("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        deepseek_model=env("DEEPSEEK_MODEL", "deepseek-flash"),
        embedding_api_key=env("EMBEDDING_API_KEY"),
        embedding_base_url=env("EMBEDDING_BASE_URL", "https://maas.qianwenaiapi.com/compatible-mode/v1"),
        embedding_model=env("EMBEDDING_MODEL", "text-embedding-v3"),
        embedding_dimension=int(env("EMBEDDING_DIMENSION", "1024")),
        documents_dir=root / "documents",
        chroma_dir=root / "storage" / "chroma",
        catalog_path=root / "catalog" / "intent-tree-v1.json",
        router_confidence_threshold=float(env("ROUTER_CONFIDENCE_THRESHOLD", "0.75")),
        retrieval_min_score=float(env("RETRIEVAL_MIN_SCORE", "0.25")),
        embedding_batch_size=int(env("EMBEDDING_BATCH_SIZE", "10")),
        cors_origins=tuple(filter(None, (item.strip() for item in env("CORS_ORIGINS", "http://localhost:4173,http://127.0.0.1:4173,http://localhost:5173,http://127.0.0.1:5173").split(",")))),
    )
