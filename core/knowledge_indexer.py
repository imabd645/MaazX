"""
Knowledge Base indexer using ChromaDB and Gemini Embeddings.
Handles parsing and embedding external documents like PDFs and Word Docs.
"""

import os
import uuid

# ── Environment hardening for Chroma / Pydantic settings ─────
# Some systems define lowercase env vars like `gemini_api_key` or
# `deepseek_api_key`. Chroma's Pydantic Settings class does not
# expect these and will crash with "extra_forbidden" errors.
# We defensively remove them before importing chromadb.
for _var in ("gemini_api_key", "deepseek_api_key"):
    os.environ.pop(_var, None)

import chromadb
import google.generativeai as genai

def _get_knowledge_collection():
    """Get or create the separate ChromaDB collection for external knowledge."""
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".chroma")
    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_or_create_collection(name="knowledge_index")
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

def extract_text_from_file(filepath: str) -> str:
    """Extract text from a .txt, .md, .pdf, or .docx file."""
    ext = os.path.splitext(filepath)[1].lower()
    
    if ext in [".txt", ".md", ".csv", ".py", ".js", ".html", ".css", ".json"]:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
            
    elif ext == ".pdf":
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(filepath)
            text = ""
            for page in doc:
                text += page.get_text() + "\n"
            return text
        except ImportError:
            return "Error: PyMuPDF (fitz) is not installed. Cannot read PDF."
        except Exception as e:
            return f"Error reading PDF: {e}"
            
    elif ext == ".docx":
        try:
            import docx
            doc = docx.Document(filepath)
            return "\n".join([para.text for para in doc.paragraphs])
        except ImportError:
            return "Error: python-docx is not installed. Cannot read DOCX."
        except Exception as e:
            return f"Error reading DOCX: {e}"
            
    else:
        return f"Warning: Unsupported file type '{ext}' for text extraction."

def index_document(filepath: str) -> dict:
    """Read a document, embed it, and store it in Chroma."""
    from config import GEMINI_API_KEY
    if not GEMINI_API_KEY:
        return {"status": "error", "error": "GEMINI_API_KEY config not found."}

    content = extract_text_from_file(filepath)
    if not content.strip() or content.startswith("Error") or content.startswith("Warning"):
        return {"status": "error", "error": f"Failed to extract content: {content}"}

    chunks = _chunk_text(content)
    if not chunks:
        return {"status": "error", "error": "File was empty or could not be chunked."}

    # Generate embeddings
    try:
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=chunks,
            task_type="retrieval_document"
        )
        embeddings = result['embedding']
    except Exception as e:
        return {"status": "error", "error": f"Failed embedding API call: {e}"}

    collection = _get_knowledge_collection()
    
    # Check if we already indexed this exact file name and remove it to prevent duplicates
    filename = os.path.basename(filepath)
    try:
        existing = collection.get(where={"filename": filename})
        if existing and existing['ids']:
            collection.delete(ids=existing['ids'])
    except Exception:
        pass

    # Insert into ChromaDB
    try:
        # Use UUID + index for unique IDs
        base_id = str(uuid.uuid4())[:8]
        ids = [f"{filename}_{base_id}_{j}" for j in range(len(chunks))]
        metadatas = [{"filename": filename, "filepath": filepath, "chunk_index": j} for j in range(len(chunks))]
        
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas
        )
        return {"status": "success", "chunks_indexed": len(chunks), "filename": filename}
    except Exception as e:
        return {"status": "error", "error": f"Failed to save to database: {e}"}

def delete_document(filename: str) -> bool:
    """Delete all chunks associated with a specific filename."""
    try:
        collection = _get_knowledge_collection()
        existing = collection.get(where={"filename": filename})
        if existing and existing['ids']:
            collection.delete(ids=existing['ids'])
            return True
        return False
    except Exception:
        return False

def query_knowledge(query: str, n_results: int = 5) -> list:
    """Search the knowledge database based on a text query."""
    try:
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=query,
            task_type="retrieval_query"
        )
        query_embedding = result['embedding']

        collection = _get_knowledge_collection()
        
        # If collection is empty, this throws an error
        try:
            if collection.count() == 0:
                return []
        except Exception:
            return []
            
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, collection.count())
        )

        matches = []
        if results['documents'] and results['documents'][0]:
            for i in range(len(results['documents'][0])):
                matches.append({
                    "content": results['documents'][0][i],
                    "filename": results['metadatas'][0][i]["filename"]
                })
        return matches
    except Exception as e:
        print(f"Knowledge query error: {e}")
        return []
