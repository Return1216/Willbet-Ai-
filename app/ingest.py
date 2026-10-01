"""手动重建本地文档索引的命令入口。"""

from __future__ import annotations

from .config import load_settings
from .retrieval import build_index, iter_documents


def main() -> None:
    """扫描 documents 并把切分后的文本写入 Chroma。"""

    settings = load_settings()
    # 空目录不需要远程 Embedding 客户端，也不会破坏已有索引。
    if any(iter_documents(settings.documents_dir)):
        from openai import OpenAI

        client = OpenAI(api_key=settings.require_embedding_key(), base_url=settings.embedding_base_url)
    else:
        client = None
    count = build_index(settings, client)
    print(f"indexed {count} chunks")


if __name__ == "__main__":
    main()
