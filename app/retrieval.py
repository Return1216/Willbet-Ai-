from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator


@dataclass(frozen=True)
class SourceDocument:
    path: Path
    text: str


@dataclass(frozen=True)
class Chunk:
    id: str
    text: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class RetrievedChunk:
    content: str
    source: str
    chunk_id: str
    score: float | None
    metadata: dict[str, Any]


COLLECTION_NAME = "rag_agent_documents"
SUPPORTED_SUFFIXES = {".md", ".txt"}


def iter_documents(root: Path) -> Iterator[SourceDocument]:
    root = Path(root)
    if not root.exists():
        return
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
            yield SourceDocument(path=path, text=path.read_text(encoding="utf-8"))


def _split_long_paragraph(text: str, max_chars: int, overlap: int) -> Iterable[str]:
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        yield text[start:end].strip()
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)


def chunk_document(document: SourceDocument, max_chars: int = 1200, overlap: int = 150) -> list[Chunk]:
    if max_chars <= 0 or overlap < 0 or overlap >= max_chars:
        raise ValueError("max_chars must be positive and overlap must be smaller than max_chars")
    paragraphs = [part.strip() for part in document.text.replace("\r\n", "\n").split("\n\n") if part.strip()]
    pieces: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= max_chars:
            pieces.append(paragraph)
        else:
            pieces.extend(_split_long_paragraph(paragraph, max_chars, overlap))
    source = document.path.name
    return [
        Chunk(
            id=f"{source}:{index}",
            text=text,
            metadata={"source": source, "path": str(document.path), "chunk_index": index},
        )
        for index, text in enumerate(pieces)
    ]


def get_collection(settings: Any):
    import chromadb

    settings.chroma_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(settings.chroma_dir))
    return client.get_or_create_collection(COLLECTION_NAME, metadata={"hnsw:space": "cosine"})


def _embeddings(client: Any, settings: Any, texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    response = client.embeddings.create(model=settings.embedding_model, input=texts)
    data = sorted(response.data, key=lambda item: getattr(item, "index", 0))
    vectors = [list(item.embedding) for item in data]
    if any(len(vector) != settings.embedding_dimension for vector in vectors):
        raise ValueError(f"embedding dimension mismatch; expected {settings.embedding_dimension}")
    return vectors


def build_index(settings: Any, embedding_client: Any, max_chars: int = 1200, overlap: int = 150) -> int:
    documents = list(iter_documents(settings.documents_dir))
    chunks = [chunk for document in documents for chunk in chunk_document(document, max_chars, overlap)]
    import chromadb

    settings.chroma_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(settings.chroma_dir))
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.get_or_create_collection(COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
    if not chunks:
        return 0
    vectors = _embeddings(embedding_client, settings, [chunk.text for chunk in chunks])
    collection.add(
        ids=[chunk.id for chunk in chunks],
        documents=[chunk.text for chunk in chunks],
        embeddings=vectors,
        metadatas=[chunk.metadata for chunk in chunks],
    )
    return len(chunks)


def retrieve(question: str, settings: Any, embedding_client: Any, top_k: int = 20) -> list[RetrievedChunk]:
    collection = get_collection(settings)
    if collection.count() == 0:
        return []
    query_vector = _embeddings(embedding_client, settings, [question])[0]
    result = collection.query(query_embeddings=[query_vector], n_results=min(top_k, collection.count()))
    ids = (result.get("ids") or [[]])[0]
    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]
    output: list[RetrievedChunk] = []
    for index, chunk_id in enumerate(ids):
        metadata = metadatas[index] or {}
        distance = distances[index] if index < len(distances) else None
        output.append(
            RetrievedChunk(
                content=documents[index],
                source=str(metadata.get("source", "unknown")),
                chunk_id=str(chunk_id),
                score=None if distance is None else 1.0 - float(distance),
                metadata=metadata,
            )
        )
    return output
