import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List, Sequence


SUPPORTED_EXTENSIONS = {".txt", ".md"}


@dataclass
class DocumentChunk:
    source: str
    chunk_id: int
    text: str


@dataclass
class IndexedChunk:
    chunk: DocumentChunk
    embedding: List[float]


@dataclass
class SearchResult:
    chunk: DocumentChunk
    score: float


class SimpleTextEmbedder:
    """
    Lightweight deterministic embedder for tests and demo-safe local retrieval.

    Live RAG can inject an OpenAI embedding function. This class keeps unit tests
    free from external API calls while still exercising vector search behavior.
    """

    def __init__(self):
        self.vocabulary = {}

    def embed(self, texts: Sequence[str]) -> List[List[float]]:
        tokenized_texts = [tokenize(text) for text in texts]

        for tokens in tokenized_texts:
            for token in tokens:
                if token not in self.vocabulary:
                    self.vocabulary[token] = len(self.vocabulary)

        vectors = []
        for tokens in tokenized_texts:
            vector = [0.0] * len(self.vocabulary)
            for token in tokens:
                vector[self.vocabulary[token]] += 1.0
            vectors.append(vector)

        return vectors


def tokenize(text: str) -> List[str]:
    return re.findall(r"[A-Za-z0-9가-힣]+", text.lower())


def load_documents(data_dir: str | Path) -> List[tuple[str, str]]:
    path = Path(data_dir)
    if not path.exists():
        return []

    documents = []
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            documents.append((str(file_path.relative_to(path)), file_path.read_text(encoding="utf-8")))

    return documents


def chunk_text(text: str, *, chunk_size: int = 900, overlap: int = 150) -> List[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []

    chunks = []
    start = 0
    while start < len(cleaned):
        end = min(start + chunk_size, len(cleaned))
        chunks.append(cleaned[start:end].strip())

        if end == len(cleaned):
            break

        start = max(0, end - overlap)

    return chunks


def create_chunks(documents: Iterable[tuple[str, str]], *, chunk_size: int = 900, overlap: int = 150) -> List[DocumentChunk]:
    chunks = []
    for source, text in documents:
        for index, chunk in enumerate(chunk_text(text, chunk_size=chunk_size, overlap=overlap), start=1):
            chunks.append(DocumentChunk(source=source, chunk_id=index, text=chunk))
    return chunks


def build_index(chunks: Sequence[DocumentChunk], embed_texts: Callable[[Sequence[str]], List[List[float]]]) -> List[IndexedChunk]:
    if not chunks:
        return []

    embeddings = embed_texts([chunk.text for chunk in chunks])
    return [IndexedChunk(chunk=chunk, embedding=embedding) for chunk, embedding in zip(chunks, embeddings)]


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    size = max(len(left), len(right))
    if size == 0:
        return 0.0

    dot = 0.0
    left_norm = 0.0
    right_norm = 0.0

    for index in range(size):
        left_value = left[index] if index < len(left) else 0.0
        right_value = right[index] if index < len(right) else 0.0
        dot += left_value * right_value
        left_norm += left_value * left_value
        right_norm += right_value * right_value

    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0

    return dot / (math.sqrt(left_norm) * math.sqrt(right_norm))


def search_index(
    query: str,
    index: Sequence[IndexedChunk],
    embed_texts: Callable[[Sequence[str]], List[List[float]]],
    *,
    top_k: int = 3,
) -> List[SearchResult]:
    if not query.strip() or not index:
        return []

    query_embedding = embed_texts([query])[0]
    scored_results = [
        SearchResult(chunk=item.chunk, score=cosine_similarity(query_embedding, item.embedding))
        for item in index
    ]

    scored_results.sort(key=lambda result: result.score, reverse=True)
    return scored_results[:top_k]


def retrieve(
    query: str,
    data_dir: str | Path,
    embed_texts: Callable[[Sequence[str]], List[List[float]]],
    *,
    top_k: int = 3,
    chunk_size: int = 900,
    overlap: int = 150,
) -> List[SearchResult]:
    documents = load_documents(data_dir)
    chunks = create_chunks(documents, chunk_size=chunk_size, overlap=overlap)
    index = build_index(chunks, embed_texts)
    return search_index(query, index, embed_texts, top_k=top_k)


def format_citations(results: Sequence[SearchResult]) -> str:
    if not results:
        return "Sources: No matching local documents found."

    lines = ["Sources:"]
    seen = set()
    for result in results:
        key = (result.chunk.source, result.chunk.chunk_id)
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"- {result.chunk.source}#chunk-{result.chunk.chunk_id}")

    return "\n".join(lines)
