from pathlib import Path
import pickle
import re
from typing import List, Dict, Any

from pypdf import PdfReader


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
SOURCE_DOCS_DIR = DATA_DIR / "source_docs"
INDEX_FILE = DATA_DIR / "knowledge_index.pkl"


def normalize_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


def split_into_chunks(text: str, chunk_size: int = 1200, overlap: int = 150) -> List[str]:
    text = normalize_text(text)
    if not text:
        return []

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        start = end - overlap

    return chunks


def extract_text_from_pdf(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    pages = []

    for page in reader.pages:
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""
        if page_text.strip():
            pages.append(page_text)

    return "\n".join(pages)


def build_index() -> Dict[str, Any]:
    SOURCE_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(SOURCE_DOCS_DIR.glob("*.pdf"))

    documents = []
    chunks = []

    for pdf_file in pdf_files:
        text = extract_text_from_pdf(pdf_file)
        text = normalize_text(text)

        documents.append(
            {
                "source_file": pdf_file.name,
                "text_length": len(text),
            }
        )

        for idx, chunk in enumerate(split_into_chunks(text)):
            chunks.append(
                {
                    "source_file": pdf_file.name,
                    "chunk_id": idx,
                    "text": chunk,
                }
            )

    index_data = {
        "indexed": True,
        "source_files": [f.name for f in pdf_files],
        "documents": documents,
        "chunks": chunks,
    }

    with open(INDEX_FILE, "wb") as f:
        pickle.dump(index_data, f)

    return {
        "indexed": True,
        "documents": len(documents),
        "chunks": len(chunks),
        "index_file": str(INDEX_FILE),
    }


def load_index() -> Dict[str, Any]:
    if not INDEX_FILE.exists():
        return {
            "indexed": False,
            "source_files": [],
            "documents": [],
            "chunks": [],
        }

    with open(INDEX_FILE, "rb") as f:
        return pickle.load(f)


def get_knowledge_status() -> Dict[str, Any]:
    pdf_files = sorted(SOURCE_DOCS_DIR.glob("*.pdf"))

    if not INDEX_FILE.exists():
        return {
            "indexed": False,
            "source_pdf_count": len(pdf_files),
            "source_files": [f.name for f in pdf_files],
            "index_file": str(INDEX_FILE),
        }

    index_data = load_index()

    return {
        "indexed": index_data.get("indexed", False),
        "source_pdf_count": len(pdf_files),
        "source_files": [f.name for f in pdf_files],
        "index_file": str(INDEX_FILE),
    }


def score_chunk(query: str, chunk_text: str) -> int:
    query_tokens = set(tokenize(query))
    chunk_tokens = set(tokenize(chunk_text))

    if not query_tokens or not chunk_tokens:
        return 0

    return len(query_tokens.intersection(chunk_tokens))


def get_knowledge_snippets(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    index_data = load_index()

    if not index_data.get("indexed"):
        return []

    chunks = index_data.get("chunks", [])
    scored = []

    for chunk in chunks:
        text = chunk.get("text", "")
        score = score_chunk(query, text)
        if score > 0:
            scored.append(
                {
                    "source_file": chunk.get("source_file", "unknown"),
                    "chunk_id": chunk.get("chunk_id", 0),
                    "text": text,
                    "score": score,
                }
            )

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def search_relevant_chunks(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Compatibility function for quiz route.
    Returns the same kind of scored chunk list, with a slightly larger default top_k.
    """
    return get_knowledge_snippets(query=query, top_k=top_k)