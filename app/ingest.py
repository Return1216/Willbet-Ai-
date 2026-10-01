from __future__ import annotations

from .config import load_settings
from .retrieval import build_index, iter_documents


def main() -> None:
    settings = load_settings()
    if any(iter_documents(settings.documents_dir)):
        from openai import OpenAI

        client = OpenAI(api_key=settings.require_embedding_key(), base_url=settings.embedding_base_url)
    else:
        client = None
    count = build_index(settings, client)
    print(f"indexed {count} chunks")


if __name__ == "__main__":
    main()
