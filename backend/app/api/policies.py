"""
backend/app/api/policies.py
Interactive Policy Document Management and Live Vector Ingestion API.
Manages markdown policy documents in rag/documents/, allows live editing,
and triggers real-time Qdrant + BM25 re-indexing.
"""
import re
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import structlog

from rag.ingestion.indexer import index_all_policy_chunks
import rag.retrieval.bm25 as bm25_module

log = structlog.get_logger()
router = APIRouter()

DOCS_DIR = Path(__file__).resolve().parents[3] / "rag" / "documents"
_DOC_ID = re.compile(r"^[a-z0-9][a-z0-9\-]*$")


def _policy_path(doc_id: str) -> Path:
    """Resolve a policy id to a file inside DOCS_DIR (rejects anything but lowercase slugs)."""
    stem = doc_id[:-3] if doc_id.endswith(".md") else doc_id
    if not _DOC_ID.match(stem):
        raise HTTPException(status_code=400, detail="Invalid policy id")
    return DOCS_DIR / f"{stem}.md"


class PolicyCreateUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, description="Human readable policy title")
    content: str = Field(..., description="Markdown content of the policy")
    version: Optional[str] = Field("v1.0", description="Policy version string")
    status: Optional[str] = Field("active", description="active or deprecated")


def _parse_frontmatter_or_title(content: str, filename: str) -> tuple[str, str, str]:
    """Extract title, version, and status from markdown headers/content."""
    lines = content.splitlines()
    title = filename.replace(".md", "").replace("-", " ").title()
    version = "v1.0"
    status = "active"

    if "deprecated" in filename.lower() or "v2" in filename.lower() or "v1" in filename.lower():
        if "v3" not in filename.lower():
            status = "deprecated"

    for line in lines[:10]:
        if line.startswith("# "):
            title = line.replace("# ", "").strip()
        elif "version:" in line.lower():
            match = re.search(r"version:\s*([^\s,]+)", line, re.IGNORECASE)
            if match:
                version = match.group(1)
        elif "status:" in line.lower():
            match = re.search(r"status:\s*([^\s,]+)", line, re.IGNORECASE)
            if match:
                status = match.group(1).lower()

    # Extract version from filename if not found (e.g. refund-policy-v3 -> v3.0)
    v_match = re.search(r"-v(\d+)", filename)
    if v_match and version == "v1.0":
        version = f"v{v_match.group(1)}.0"

    return title, version, status


@router.get("/policies")
async def list_policies():
    """List all indexed markdown policy documents from rag/documents/."""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    docs = []

    for file_path in sorted(DOCS_DIR.glob("*.md")):
        if file_path.name.startswith("."):
            continue
        try:
            content = file_path.read_text(encoding="utf-8")
            title, version, status = _parse_frontmatter_or_title(content, file_path.name)
            stat = file_path.stat()
            docs.append({
                "id": file_path.stem,
                "filename": file_path.name,
                "name": title,
                "version": version,
                "status": status,
                "size_bytes": stat.st_size,
                "updated_at": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
                "snippet": content[:240].strip() + ("..." if len(content) > 240 else ""),
            })
        except Exception as e:
            log.warning("policy.read_failed", file=file_path.name, error=str(e))

    return {"policies": docs, "total": len(docs)}


@router.get("/policies/{doc_id}")
async def get_policy(doc_id: str):
    """Retrieve full raw markdown and metadata for a specific policy."""
    file_path = _policy_path(doc_id)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Policy '{doc_id}' not found")

    content = file_path.read_text(encoding="utf-8")
    title, version, status = _parse_frontmatter_or_title(content, file_path.name)
    stat = file_path.stat()

    return {
        "id": file_path.stem,
        "filename": file_path.name,
        "name": title,
        "version": version,
        "status": status,
        "content": content,
        "size_bytes": stat.st_size,
        "updated_at": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
    }


@router.post("/policies", status_code=201)
async def create_policy(req: PolicyCreateUpdateRequest):
    """Create a new policy document in rag/documents/ and re-index vector store."""
    name_clean = (req.name or "custom-policy").lower().strip()
    safe_id = re.sub(r"[^a-z0-9\-]", "-", name_clean).strip("-") or "custom-policy"
    filename = f"{safe_id}.md"
    file_path = _policy_path(safe_id)

    if file_path.exists():
        raise HTTPException(status_code=400, detail=f"Policy '{filename}' already exists. Use PUT to update.")

    file_path.write_text(req.content, encoding="utf-8")
    log.info("policy.created", filename=filename)

    # Trigger reindex
    try:
        bm25_module._bm25_index = None
        bm25_module._bm25_chunks = []
        client, chunks = index_all_policy_chunks(docs_dir=DOCS_DIR, force_reindex=True)
        chunks_count = len(chunks)
    except Exception as e:
        log.error("policy.reindex_after_create_failed", error=str(e))
        chunks_count = 0

    return {
        "message": f"Policy '{filename}' created and re-indexed successfully",
        "id": safe_id,
        "filename": filename,
        "chunks_indexed": chunks_count,
    }


@router.put("/policies/{doc_id}")
async def update_policy(doc_id: str, req: PolicyCreateUpdateRequest):
    """Update existing markdown policy content and refresh vector embeddings."""
    file_path = _policy_path(doc_id)
    safe_name = file_path.name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Policy '{doc_id}' not found")

    file_path.write_text(req.content, encoding="utf-8")
    log.info("policy.updated", filename=safe_name)

    # Trigger reindex
    try:
        bm25_module._bm25_index = None
        bm25_module._bm25_chunks = []
        client, chunks = index_all_policy_chunks(docs_dir=DOCS_DIR, force_reindex=True)
        chunks_count = len(chunks)
    except Exception as e:
        log.error("policy.reindex_after_update_failed", error=str(e))
        chunks_count = 0

    return {
        "message": f"Policy '{safe_name}' updated and re-indexed successfully",
        "id": file_path.stem,
        "filename": safe_name,
        "chunks_indexed": chunks_count,
    }


@router.post("/policies/reindex")
async def trigger_reindex():
    """Force re-chunking and re-indexing of all policy documents into Qdrant & BM25."""
    try:
        bm25_module._bm25_index = None
        bm25_module._bm25_chunks = []
        client, chunks = index_all_policy_chunks(docs_dir=DOCS_DIR, force_reindex=True)
        return {
            "status": "success",
            "message": f"Successfully re-indexed {len(chunks)} chunks across all policy documents into Qdrant & BM25.",
            "total_chunks": len(chunks),
        }
    except Exception as e:
        log.error("policy.reindex_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Re-indexing failed: {str(e)}")
