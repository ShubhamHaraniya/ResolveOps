# M4 — Full RAG Knowledge & Policy Engine (Context & Decisions)

> **Phase / Milestone:** M4  
> **Status:** READY FOR PLANNING & EXECUTION  
> **Created:** 2026-10-08  
> **Predecessor Milestones:** M1 (Foundation), M2 (Governance), M3 (Frontend)  
> **Downstream Consumers:** Researcher, Planner (`/gsd-plan-phase M4`), Implementation Agents

---

## 1. Executive Summary & Objective

Milestone M4 elevates ResolveOps from a lightweight keyword-based policy lookup into a **production-grade, dual-mode Hybrid RAG pipeline** fulfilling Sections 9–17 and Section 46 of the ResolveOps specification.

RAG serves as the **deterministic policy grounding layer** that answers:
> *"What does Northwind Cloud's policy say about this customer request?"*

It is **NOT** the final authorization mechanism (which remains the Policy Gateway's responsibility), but provides verified evidence and citations to Groq's planning model and the human approval interface.

---

## 2. Locked Implementation Decisions

### 2.1 Embedding Engine & Model
- **Engine:** `fastembed` (using ONNX Runtime).
- **Model:** `BAAI/bge-m3` (multilingual, 1024-dim, 8192 token context window, optimized for dense representation).
- **Fallback / Lightweight Mode:** FastEmbed ONNX runs entirely on CPU without requiring PyTorch, CUDA, or large weight downloads. If offline or in constrained environments, a deterministic fallback ensures test suites and offline demos never crash.
- **Privacy Guarantee:** Document indexing and embedding happens 100% locally. Policy documents are never transmitted to cloud LLMs or third-party vector endpoints.

### 2.2 Vector Database (Qdrant) Architecture
- **Dual-Mode Client:**
  1. **Primary Mode:** Connects to remote Qdrant via HTTP (`http://localhost:6333` or `QDRANT_URL`).
  2. **Embedded Fallback Mode:** When Qdrant HTTP is unreachable (e.g., local dev without Docker running), automatically falls back to an embedded/in-memory Qdrant instance (`QdrantClient(":memory:")` or local SQLite/disk storage in `data/qdrant`).
- **Collection Name:** `resolveops_policies` (vector size 1024, Cosine distance).
- **Payload Schema:**
  ```json
  {
    "chunk_id": "refund-v3-section-2-4",
    "document_id": "refund-policy-v3",
    "title": "Northwind Cloud Customer Refund Policy",
    "version": 3,
    "section": "Refund Limits & Authority",
    "subsection": "Support Agent Thresholds",
    "effective_date": "2026-01-01",
    "status": "active",
    "content": "Refunds under $50 require support-agent approval..."
  }
  ```

### 2.3 Hybrid Retrieval & Candidate Fusion
- **Two-Stage Retrieval:**
  1. **Dense Retrieval:** Qdrant similarity search retrieves top 15 chunks based on semantic embeddings.
  2. **Lexical Retrieval:** BM25 (`rank_bm25`) retrieves top 15 chunks based on exact token matches (critical for monetary values like `$50`, time windows like `30 days`, role strings like `viewer`, `member`, and ticket/rule codes like `REF-001`).
- **Fusion Algorithm:** **Reciprocal Rank Fusion (RRF)** with standard smoothing constant $k = 60$:
  $$RRF(d) = \sum_{m \in \{dense, bm25\}} \frac{1}{k + rank_m(d)}$$
- Fused pool: Top 15–20 candidates passed to the reranking stage.

### 2.4 Reranker
- **Engine:** `flashrank` (lightweight, zero-PyTorch, ultra-fast CPU neural reranker).
- **Model:** `ms-marco-TinyBERT-L-2-v2` or `rank-T5-flan`.
- **Output:** Top 3–5 highest-relevance chunks with normalized scores between 0.0 and 1.0.

### 2.5 Policy Conflict Resolution & Contradictory Pairs
- **Contradictory Pair Test Case:**
  - `refund-policy-v2` (deprecated): Refunds under $100 require approval.
  - `refund-policy-v3` (active): Refunds under $50 require approval.
- **Precedence Rules:**
  1. Metadata filtering automatically favors `status: active` documents.
  2. Deprecated documents are indexed to allow historical traceability and conflict testing.
  3. When both active and deprecated policies match a query with high relevance, the pipeline attaches:
     ```json
     {
       "conflict_detected": true,
       "active_policy": "refund-policy-v3",
       "superseded_policy": "refund-policy-v2",
       "conflict_summary": "v3 supersedes v2 (effective 2026-01-01). v3 lowers approval threshold from $100 to $50."
     }
     ```
  4. LangGraph and UI flag the conflict prominently so human reviewers see why v3 was selected.

---

## 3. Policy Document Inventory (18 Documents)

To fulfill Spec Section 10 (15–25 documents), the following comprehensive policy corpus will be created in `rag/documents/`:

1. `refund-policy-v1.md` (Deprecated, v1, $200 threshold, 60-day window)
2. `refund-policy-v2.md` (Deprecated, v2, $100 threshold, 45-day window)
3. `refund-policy-v3.md` (Active, v3, $50 threshold, 30-day window, rule REF-001)
4. `plan-policy.md` (Active, Starter/Pro/Enterprise tiers, monthly/annual billing terms)
5. `proration-policy.md` (Active, mid-cycle seat additions and tier upgrades pro-rata calculations)
6. `seat-policy.md` (Active, seat limits per plan: Starter max 5, Pro max 50, Enterprise custom)
7. `access-policy.md` (Active, viewer and member roles allowed; admin/prod-admin strictly forbidden)
8. `mfa-policy.md` (Active, self-service reset vs agent-assisted photo ID verification)
9. `escalation-policy.md` (Active, refunds > $500 to Finance, security anomalies to SecOps)
10. `tone-guidelines.md` (Active, professional, empathetic, no unapproved commitments)
11. `billing-policy.md` (Active, Net 30, payment methods, dunning & retry schedule)
12. `invoice-policy.md` (Active, invoice re-issuance, tax-exempt entity requirements)
13. `strategic-account-policy.md` (Active, accounts ARR > $50k require CS lead sign-off, no auto-writes)
14. `legal-hold-policy.md` (Active, accounts under legal hold: all write operations strictly frozen)
15. `credit-policy.md` (Active, service availability SLA credits capped at 1 month invoice value)
16. `chargeback-policy.md` (Active, chargeback procedures; automated agent has no chargeback tool)
17. `data-privacy-policy.md` (Active, GDPR/CCPA erasure requests routed to DPO; agent has no delete tool)
18. `security-incident-policy.md` (Active, prompt injection / credential leaks trigger instant lockdown)

---

## 4. Chunking & Ingestion Strategy

- **Document Format:** Markdown with YAML frontmatter header.
- **Chunking Method:** **Section-Aware Chunking** (splitting on Markdown H2 `##` and H3 `###` headers).
- **Metadata Inheritance:** Each chunk preserves:
  - `chunk_id`: `{doc_slug}-{section_slug}`
  - `document_id`: Document filename slug
  - `title`: Document title from frontmatter
  - `section`: Heading level 2 title
  - `subsection`: Heading level 3 title (if present)
  - `version`: Version integer
  - `effective_date`: ISO date string
  - `status`: `active` or `deprecated`
  - `source`: Relative file path
- **Clipping / Overlap:** Clean boundaries around paragraphs, avoiding mid-sentence cuts.

---

## 5. Directory & Module Structure

```text
rag/
├── documents/                # 18 Markdown policy files with YAML frontmatter
│   ├── refund-policy-v1.md
│   ├── refund-policy-v2.md
│   ├── refund-policy-v3.md
│   └── ... (15 more files)
├── ingestion/
│   ├── __init__.py
│   ├── chunker.py           # Section-aware markdown parser and metadata extractor
│   └── indexer.py           # Vectorizes chunks and seeds Qdrant + BM25 index
├── embeddings/
│   ├── __init__.py
│   └── embedder.py          # FastEmbed bge-m3 wrapper with local CPU support
├── retrieval/
│   ├── __init__.py
│   ├── dense.py             # Qdrant vector retrieval
│   ├── bm25.py              # BM25 lexical retriever
│   └── hybrid.py            # RRF fusion orchestrator
└── reranking/
    ├── __init__.py
    └── reranker.py          # FlashRank reranker to top 3-5 chunks

services/
└── mcp_kb/
    ├── __init__.py
    └── server.py            # MCP server exposing search_policy tool
```

---

## 6. Integration Points

1. **LangGraph Node (`backend/app/graph/nodes/gather_context.py`):**
   - Replace the legacy `_rag_search` stub with an async call to `rag.retrieval.hybrid.search_policies(query, category)`.
   - Populates `context.rag_results` with verified citations and conflict flags.
2. **Planner Prompt (`backend/app/llm/prompts.py`):**
   - Renders policy chunks with title, section, version, and status.
   - If conflict detected, instructs Groq to adhere to the active policy version and highlight the superseded rule.
3. **Frontend UI (`frontend/app/knowledge-base/page.tsx` & `/tickets/[id]`):**
   - Ticket detail center/right column displays active policy citations with expandable source details and conflict badges.
   - Knowledge base directory page dynamically lists all 18 documents with live status and section breakdown.

---

## 7. Definition of Done for M4

- [ ] All 18 policy documents created with standard YAML frontmatter in `rag/documents/`.
- [ ] Section-aware chunker produces valid chunks preserving all metadata fields.
- [ ] FastEmbed embedding pipeline initializes `BAAI/bge-m3` without PyTorch dependency.
- [ ] Dual-mode Qdrant integration functions smoothly with or without Docker.
- [ ] BM25 indexer correctly matches exact terms (`$50`, `30 days`, `viewer`, `REF-001`).
- [ ] RRF hybrid merger + FlashRank reranks candidates to top 3–5 chunks.
- [ ] Policy conflict test case (`refund-policy-v2` vs `refund-policy-v3`) cleanly detects conflict and prioritizes v3.
- [ ] Unit tests for chunker, embedder, retriever, reranker, and conflict detector passing (100%).
- [ ] End-to-end integration with LangGraph `gather_context` verified.
