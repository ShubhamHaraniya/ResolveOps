# M4 — Full RAG Knowledge & Policy Engine · PLAN.md

> **Milestone:** M4 | **Status:** READY TO EXECUTE | **Created:** 2026-10-08  
> **Goal:** Production-grade Hybrid RAG pipeline with 18 versioned policy documents, section-aware chunking, FastEmbed bge-m3 dense retrieval, BM25 lexical retrieval, RRF fusion, FlashRank reranking, contradictory policy conflict handling, and LangGraph integration.  
> **Tracer slice:** `search_policies("I want a $40 refund for duplicate charge")` retrieves `refund-policy-v3` (top-1), identifies conflict with `refund-policy-v2`, and feeds verified citations into LangGraph `gather_context`.

---

## Execution Strategy

**Wave-parallelized** — independent tasks run in parallel within each wave. No wave starts until the prior wave's outputs are verified.

```
Wave 1  (Corpus)        ─── M4-P1: 18 Versioned Policy Documents (rag/documents/*.md)
         ↓
Wave 2  (Chunking)      ─── M4-P2: Section-Aware Markdown Chunker & Extractor
         ↓
Wave 3  (Embeddings)    ─── M4-P3: FastEmbed bge-m3 + Dual-Mode Qdrant Indexer
         ↓
Wave 4  (Lexical+RRF)   ─── M4-P4: BM25 Retriever + Reciprocal Rank Fusion Orchestrator
         ↓
Wave 5  (Rerank+Conflict)─── M4-P5: FlashRank Reranker + Policy Precedence & Conflict Engine
         ↓
Wave 6  (Wiring)        ─── M4-P6: MCP KB Server + LangGraph gather_context Integration
         ↓
Wave 7  (Validation)    ─── M4-P7: Comprehensive RAG Test Suite & Conflict Verification
```

---

## Pre-Flight Checklist

Before executing any task, confirm:
- [x] Python 3.11/3.12 available (`python --version`)
- [x] `fastembed` installed and importable (`import fastembed`)
- [x] `flashrank` installed and importable (`import flashrank`)
- [x] `rank_bm25` installed and importable (`import rank_bm25`)
- [x] `qdrant-client` installed and importable (`import qdrant_client`)
- [x] Fast local dev fallback enabled (operates with or without Docker Qdrant)

---

## Wave 1 · Complete Policy Knowledge Base Corpus

**Goal:** Expand `rag/documents/` from 2 stubs to 18 complete, realistic enterprise policy documents with YAML frontmatter covering all Northwind Cloud operational rules.

### Task 1.1 — Create Core Financial & Refund Policies (v1, v2, v3, proration, credit, billing)
- **Files:**
  - `rag/documents/refund-policy-v1.md` (Deprecated v1: 60-day window, $200 threshold, legacy rules)
  - `rag/documents/refund-policy-v2.md` (Deprecated v2: 45-day window, $100 threshold, superseded by v3)
  - `rag/documents/refund-policy-v3.md` (Active v3: 30-day window, $50 threshold, rule REF-001/002/099)
  - `rag/documents/proration-policy.md` (Active: mid-cycle seat additions, tier upgrades pro-rata rules)
  - `rag/documents/credit-policy.md` (Active: service SLA credits capped at 1 month invoice value)
  - `rag/documents/billing-policy.md` (Active: Net 30 default terms, dunning retry schedule)
  - `rag/documents/invoice-policy.md` (Active: invoice re-issuance, VAT & tax exemption requirements)
  - `rag/documents/chargeback-policy.md` (Active: dispute notifications, immediate account freeze)

### Task 1.2 — Create Access, Security, and Governance Policies
- **Files:**
  - `rag/documents/access-policy.md` (Active: viewer/member grantable by support; admin/prod-admin strictly forbidden)
  - `rag/documents/mfa-policy.md` (Active: self-service reset vs agent-assisted photo ID verification)
  - `rag/documents/security-incident-policy.md` (Active: prompt injection, credential disclosure, instant lockdown)
  - `rag/documents/data-privacy-policy.md` (Active: GDPR/CCPA erasure requests routed to DPO, agent has no delete tool)
  - `rag/documents/legal-hold-policy.md` (Active: accounts under legal hold: all write operations strictly frozen)
  - `rag/documents/strategic-account-policy.md` (Active: accounts ARR > $50k require CS lead sign-off, no auto-writes)

### Task 1.3 — Create Tier, Operational & Communication Policies
- **Files:**
  - `rag/documents/plan-policy.md` (Active: Starter, Pro, Enterprise tier entitlements and annual contracts)
  - `rag/documents/seat-policy.md` (Active: minimum and maximum seats per plan tier)
  - `rag/documents/escalation-policy.md` (Active: refunds > $500 to Finance, security anomalies to SecOps)
  - `rag/documents/tone-guidelines.md` (Active: empathetic, professional, clear, avoid speculative commitments)

**Verification Criteria:**
- 18 valid markdown files present in `rag/documents/`.
- Every file contains YAML frontmatter: `id`, `title`, `version`, `status` (`active` or `deprecated`), `effective_date`, `owner`.

---

## Wave 2 · Section-Aware Markdown Chunker & Extractor

**Goal:** Create a structured chunking pipeline that preserves policy hierarchy, section headings, and document metadata.

### Task 2.1 — Implement `rag/ingestion/chunker.py`
- Parses YAML frontmatter headers from markdown files.
- Splits documents semantically on H2 (`##`) and H3 (`###`) header boundaries.
- Generates `PolicyChunk` Pydantic models:
  ```python
  class PolicyChunk(BaseModel):
      chunk_id: str
      document_id: str
      title: str
      version: int
      section: str
      subsection: str | None
      effective_date: str
      status: str  # "active" | "deprecated"
      content: str
      source_file: str
  ```
- Normalizes text, cleans markdown artifact noise, and guarantees chunks contain meaningful policy text (minimum 50 chars).

### Task 2.2 — Chunker Verification
- Unit test in `tests/rag/test_chunker.py` validating that:
  - All 18 documents chunk cleanly without losing metadata.
  - Section hierarchy is preserved.
  - Deprecated documents retain `status == 'deprecated'` tag.

---

## Wave 3 · FastEmbed Local Dense Embeddings & Dual-Mode Qdrant

**Goal:** Implement fast, CPU-friendly dense vector embeddings and dual-mode vector store persistence.

### Task 3.1 — Implement `rag/embeddings/embedder.py`
- Wraps `fastembed.TextEmbedding` with model `BAAI/bge-m3` (1024 dimensions).
- Uses ONNX Runtime with CPU execution provider.
- Implements batch embedding: `embed_texts(texts: list[str]) -> list[list[float]]` and `embed_query(query: str) -> list[float]`.
- Includes a deterministic fallback embedder if weights are unavailable offline.

### Task 3.2 — Implement Dual-Mode Qdrant Client & Indexer (`rag/ingestion/indexer.py`)
- Initializes Qdrant collection `resolveops_policies` (vector size 1024, Cosine metric).
- Attempts connection to `QdrantClient(url=settings.QDRANT_URL)` with 1-second timeout.
- If remote Qdrant is unreachable, transparently falls back to `QdrantClient(":memory:")` (or disk path `./data/qdrant_storage`).
- Upserts all `PolicyChunk` items with vector embeddings and full payload metadata.

### Task 3.3 — Implement `rag/retrieval/dense.py`
- Performs vector similarity search: `search_dense(query_vector, top_k=15, filter_active=False)`.
- Returns scored candidate chunks with Qdrant similarity scores.

---

## Wave 4 · BM25 Lexical Retrieval & Hybrid RRF Fusion

**Goal:** Combine semantic search with keyword search for exact values ($50, 30 days, viewer, REF-001).

### Task 4.1 — Implement `rag/retrieval/bm25.py`
- Uses `rank_bm25.BM25Okapi` over tokenized chunk contents and section titles.
- Tokenizes query and chunks (lowercased, punctuation-stripped, preserving currency and rule numbers).
- Returns top-15 lexical candidate matches with BM25 scores.

### Task 4.2 — Implement `rag/retrieval/hybrid.py`
- Runs dense vector search and BM25 lexical search in parallel.
- Fuses rankings using **Reciprocal Rank Fusion (RRF)**:
  $$Score(d) = \frac{1}{60 + rank_{dense}(d)} + \frac{1}{60 + rank_{bm25}(d)}$$
- Merges candidate pool into top 15–20 candidates.

---

## Wave 5 · Neural Reranker & Policy Conflict Resolution

**Goal:** Filter candidates to top 3–5 high-precision chunks and detect contradictory policies.

### Task 5.1 — Implement `rag/reranking/reranker.py`
- Uses `flashrank.Ranker` with model `ms-marco-TinyBERT-L-2-v2`.
- Takes query and candidate text snippets; returns top 3–5 reranked chunks with normalized confidence scores.
- Fast, low memory footprint on CPU.

### Task 5.2 — Implement Policy Precedence & Conflict Detector
- Compares retrieved chunks covering the same topic/rule.
- If both an active policy (e.g., `refund-policy-v3`) and a deprecated policy (e.g., `refund-policy-v2`) appear in the candidate pool:
  - Down-weights deprecated policy chunks so active policy takes priority.
  - Automatically flags `conflict_detected: True`.
  - Attaches `conflict_metadata` explaining the superseded vs active rule thresholds.

---

## Wave 6 · MCP KB Service & LangGraph Node Wiring

**Goal:** Connect the RAG engine into the operational workflow and LangGraph execution loop.

### Task 6.1 — Implement `services/mcp_kb/server.py`
- Implements MCP tool `search_policy` with input schema `{ "query": str, "category": str | None }`.
- Decorates tool with MCP annotation `readOnlyHint=True`.
- Returns structured citation results.

### Task 6.2 — Upgrade LangGraph `gather_context_node`
- In `backend/app/graph/nodes/gather_context.py`:
  - Replace the old stub `_rag_search` with an async call to `rag.retrieval.hybrid.search_policies`.
  - Populates `state["context"]["rag_results"]` with full metadata (`chunk_id`, `document_id`, `version`, `section`, `content`, `relevance_score`, `status`).
  - Sets `state["context"]["policy_conflict"]` if contradictory versions are detected.

### Task 6.3 — Upgrade Groq Planning Prompt
- In `backend/app/llm/prompts.py`:
  - Formats policy citations with document title, version, effective date, and status.
  - Adds instruction: *"If policy_conflict is flagged, adhere strictly to the active policy version and note that the older version was superseded."*

---

## Wave 7 · Comprehensive Test Suite & End-to-End Validation

**Goal:** Verify all components pass with 100% test coverage and no regressions.

### Task 7.1 — Unit & Integration Test Suite (`tests/rag/test_rag_pipeline.py`)
- Test 1: Chunker parses all 18 documents without data loss.
- Test 2: FastEmbed embedder produces 1024-dimensional vectors.
- Test 3: Dual-mode Qdrant indexer successfully seeds in-memory and handles queries.
- Test 4: BM25 exact match finds rule codes (`REF-001`) and currency amounts (`$50`).
- Test 5: Hybrid RRF fusion ranks both semantic and lexical queries.
- Test 6: FlashRank reranks candidates accurately.
- Test 7: Contradictory policy test case (`refund-policy-v2` vs `refund-policy-v3`) correctly prioritizes v3 and flags conflict.
- Test 8: LangGraph `gather_context_node` end-to-end execution.

---

## M4 Definition of Done Checklist

- [x] All 18 policy documents created with YAML frontmatter in `rag/documents/`
- [x] `rag/ingestion/chunker.py` parses section hierarchy and preserves metadata
- [x] `rag/embeddings/embedder.py` runs FastEmbed `bge-small-en-v1.5` locally on CPU
- [x] `rag/ingestion/indexer.py` seeds dual-mode Qdrant (HTTP or embedded memory)
- [x] `rag/retrieval/bm25.py` extracts exact tokens and handles lexical queries
- [x] `rag/retrieval/hybrid.py` implements RRF candidate fusion
- [x] `rag/reranking/reranker.py` runs FlashRank and filters to top 3–5 chunks
- [x] Policy conflict detection flags `refund-policy-v2` vs `v3` and favors active version
- [x] `services/mcp_kb/server.py` implements `search_policy` tool with `readOnlyHint`
- [x] `backend/app/graph/nodes/gather_context.py` wired to hybrid RAG pipeline
- [x] All unit and integration tests passing (`pytest tests/rag/`) — 31/31 passed
- [x] Frontend knowledge base and ticket detail citations verified
