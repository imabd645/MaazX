"""
Codebase indexer using ChromaDB and Gemini Embeddings.
Provides the RAG capabilities for semantic code search.
"""

import os
import glob
import json
import uuid
from threading import Thread

# ── Environment hardening for Chroma / Pydantic settings ─────
# Some systems define lowercase env vars like `gemini_api_key` or
# `deepseek_api_key`. Chroma's Pydantic Settings class does not
# expect these and will crash with "extra_forbidden" errors.
# We defensively remove them before importing chromadb.
for _var in ("gemini_api_key", "deepseek_api_key"):
    os.environ.pop(_var, None)

import chromadb
import google.generativeai as genai

# Global vars for simple state tracking
INDEXING_STATUS = "idle"
INDEXING_PROGRESS = 0.0

def _get_collection():
    """Get or create the ChromaDB collection."""
    # We store the db in .chroma inside the package root
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".chroma")
    client = chromadb.PersistentClient(path=db_path)
    # create collection
    collection = client.get_or_create_collection(name="codebase_index")
    return collection

def _chunk_text(text: str, max_chars=1500, overlap=200):
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = start + max_chars
        chunks.append(text[start:end])
        start = end - overlap
    return chunks

def _embed_texts(texts: list[str]) -> list[list[float]]:
    """Get embeddings using Gemini API in batches."""
    from config import GEMINI_API_KEY
    if not GEMINI_API_KEY:
        return []

    # genai.embed_content takes a model name and list of texts
    try:
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=texts,
            task_type="retrieval_document"
        )
        return result['embedding']
    except Exception as e:
        print(f"Error embedding: {e}")
        return []

def _worker_index_repo(directory: str):
    """Background task to index a directory."""
    global INDEXING_STATUS, INDEXING_PROGRESS
    INDEXING_STATUS = "indexing"
    INDEXING_PROGRESS = 0.0

    try:
        collection = _get_collection()

        # Gather files
        file_paths = []
        for root, dirs, files in os.walk(directory):
            # easy exclusions
            if any(part.startswith('.') for part in root.split(os.sep)):
                continue
            if "__pycache__" in root or "node_modules" in root:
                continue

            for f in files:
                ext = os.path.splitext(f)[1].lower()
                # basic text/code extensions
                if ext in [".py", ".js", ".html", ".css", ".md", ".txt", ".json"]:
                    file_paths.append(os.path.join(root, f))

        total_files = len(file_paths)
        if total_files == 0:
            INDEXING_STATUS = "idle"
            return

        # We will delete the old collection contents to re-index fresh
        try:
            items = collection.get()
            if items['ids']:
                collection.delete(ids=items['ids'])
        except Exception:
            pass

        # Parse and encode
        for i, filepath in enumerate(file_paths):
            try:
                with open(filepath, "r", encoding="utf-8") as file:
                    content = file.read()

                # Basic chunking
                chunks = _chunk_text(content)
                if not chunks:
                    continue

                # Get embeddings
                # We do this one file at a time to stay under batch limits
                embeddings = _embed_texts(chunks)

                ids = [f"{filepath}_{j}" for j in range(len(chunks))]
                metadatas = [{"filepath": filepath, "chunk_index": j} for j in range(len(chunks))]

                if embeddings and len(embeddings) == len(chunks):
                    collection.add(
                        ids=ids,
                        embeddings=embeddings,
                        documents=chunks,
                        metadatas=metadatas
                    )
            except Exception as e:
                # ignore binary or unreadable files
                pass

            INDEXING_PROGRESS = round(((i + 1) / total_files) * 100, 1)

        INDEXING_STATUS = "idle"

    except Exception as e:
        print(f"Indexing failed: {e}")
        INDEXING_STATUS = f"error: {e}"

def start_indexing(directory: str):
    """Start the indexing job in a background thread."""
    global INDEXING_STATUS
    if INDEXING_STATUS == "indexing":
        return False
    t = Thread(target=_worker_index_repo, args=(directory,), daemon=True)
    t.start()
    return True

def get_indexing_status():
    """Return status data"""
    global INDEXING_STATUS, INDEXING_PROGRESS
    return {"status": INDEXING_STATUS, "progress": INDEXING_PROGRESS}

def semantic_search(query: str, n_results: int = 5):
    """Search the chroma database based on a text query."""
    try:
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=query,
            task_type="retrieval_query"
        )
        query_embedding = result['embedding']

        collection = _get_collection()
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )

        matches = []
        if results['documents'] and results['documents'][0]:
            for i in range(len(results['documents'][0])):
                matches.append({
                    "content": results['documents'][0][i],
                    "filepath": results['metadatas'][0][i]["filepath"]
                })
        return matches
    except Exception as e:
        return str(e)
