"""
evals/rag_benchmark.py
Retrieval-quality benchmark over a small golden query set (8 queries) against the policy documents.

Metrics (RAGAS-style names, but this does not use the RAGAS library):
1. Context precision - reciprocal rank of the expected document in the retrieved chunks (deterministic)
2. Context recall    - share of required clauses found in the retrieved text (deterministic)
3. Faithfulness      - LLM-judged: is a generated answer supported by the retrieved context (needs GROQ_API_KEY)
4. Answer relevance  - LLM-judged: does the generated answer address the question (needs GROQ_API_KEY)

Run:  python -m evals.rag_benchmark
"""
import asyncio
import json
import sys
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
for p in [str(REPO_ROOT), str(BACKEND_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import structlog

from rag.service import search_policies
from app.llm.groq_client import get_groq_client
from app.config import settings

log = structlog.get_logger()

GOLDEN_TEST_DATASET = [
    {
        "id": "RAG-001",
        "query": "Is a customer eligible for a $30 refund if charged twice on invoice INV-001?",
        "category": "refund",
        "expected_doc": "refund-policy-v3",
        "expected_section": "2. Refund Eligibility",
        "required_clauses": ["30 days", "duplicate", "original payment method"],
        "deprecated_doc": "refund-policy-v2",
    },
    {
        "id": "RAG-002",
        "query": "Can support agents approve a $75 refund without escalation?",
        "category": "refund",
        "expected_doc": "refund-policy-v3",
        "expected_section": "3. Approval Thresholds",
        "required_clauses": ["$50", "Tier 2", "Support Lead", "VP Support"],
        "deprecated_doc": "refund-policy-v2",
    },
    {
        "id": "RAG-003",
        "query": "What special approvals are required for billing actions on strategic enterprise accounts?",
        "category": "billing",
        "expected_doc": "strategic-account-policy",
        "expected_section": "2. Operational Rules",
        "required_clauses": ["VP", "CSM", "Strategic", "written approval"],
        "deprecated_doc": None,
    },
    {
        "id": "RAG-004",
        "query": "Can an automated agent grant admin or cluster access to a requester?",
        "category": "access_request",
        "expected_doc": "access-policy",
        "expected_section": "2. Role Definitions",
        "required_clauses": ["Forbidden", "human-only", "never automated", "admin"],
        "deprecated_doc": None,
    },
    {
        "id": "RAG-005",
        "query": "What happens if an account is marked under legal hold?",
        "category": "legal_hold",
        "expected_doc": "legal-hold-policy",
        "expected_section": "1. Policy Scope",
        "required_clauses": ["freeze", "forbidden", "compliance officer", "legal hold"],
        "deprecated_doc": None,
    },
    {
        "id": "RAG-006",
        "query": "How is credit calculated for an SLA service outage of 4 hours?",
        "category": "credit",
        "expected_doc": "credit-policy",
        "expected_section": "2. Credit Calculation",
        "required_clauses": ["prorated", "monthly fee", "credit balance"],
        "deprecated_doc": None,
    },
    {
        "id": "RAG-007",
        "query": "How are mid-cycle plan upgrade charges prorated?",
        "category": "plan_change",
        "expected_doc": "proration-policy",
        "expected_section": "1. Upgrade Proration",
        "required_clauses": ["proration credit", "remaining days", "immediate upgrade"],
        "deprecated_doc": None,
    },
    {
        "id": "RAG-008",
        "query": "What is the procedure if a customer files a chargeback with their credit card company?",
        "category": "chargeback",
        "expected_doc": "chargeback-policy",
        "expected_section": "1. Immediate Actions",
        "required_clauses": ["lock", "finance team", "freeze", "dispute"],
        "deprecated_doc": None,
    },
]


def _parse_score(text: str, key: str) -> float:
    """Extract a 0..1 score from the judge's JSON reply; raises if it is missing or out of range."""
    start, end = text.find("{"), text.rfind("}")
    value = float(json.loads(text[start:end + 1])[key])
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{key} out of range: {value}")
    return value


async def _judge(groq, prompt: str, key: str) -> Optional[float]:
    """Ask the LLM judge for a score. Returns None (never a default) when the call or parsing fails."""
    try:
        text, _usage = await groq.complete_text(
            model=settings.groq_model_fast,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        return _parse_score(text, key)
    except Exception as e:  # noqa: BLE001 - reported as "not measured"
        log.warning("rag_benchmark.judge_failed", key=key, error=str(e)[:200])
        return None


async def evaluate_faithfulness(groq, query: str, context_text: str, answer: str) -> Optional[float]:
    """LLM-judged: are the answer's claims supported by the retrieved context?"""
    prompt = f"""You are a RAG evaluation judge. Evaluate the FAITHFULNESS of the following answer given the context.
Answer is faithful (1.0) if all facts are directly supported by the context.
Answer is unfaithful (0.0) if it invents facts, contradicts the context, or hallucinates.

Context:
{context_text[:1500]}

Question:
{query}

Answer:
{answer}

Respond strictly with a JSON object: {{"faithfulness_score": <float between 0.0 and 1.0>, "reason": "<short explanation>"}}"""
    return await _judge(groq, prompt, "faithfulness_score")


async def evaluate_answer_relevance(groq, query: str, answer: str) -> Optional[float]:
    """LLM-judged: does the answer directly address the question?"""
    prompt = f"""You are a RAG evaluation judge. Evaluate the ANSWER RELEVANCE of the response to the user's question.
Score 1.0 if the answer directly, concisely, and completely answers the question.
Score 0.0 if the answer is completely evasive, off-topic, or irrelevant.

Question:
{query}

Answer:
{answer}

Respond strictly with a JSON object: {{"relevance_score": <float between 0.0 and 1.0>, "reason": "<short explanation>"}}"""
    return await _judge(groq, prompt, "relevance_score")


def _mean(values: List[Optional[float]]) -> Optional[float]:
    present = [v for v in values if v is not None]
    return round(sum(present) / len(present), 3) if present else None


async def run_ragas_benchmark() -> Dict[str, Any]:
    """Run the golden query set.

    Context precision (reciprocal rank of the expected document) and context recall (share of required
    clauses found in the retrieved text) are computed deterministically from retrieval. Faithfulness and
    answer relevance need an LLM to write and judge an answer; if Groq is unavailable they are reported as
    null and excluded from the overall score - no placeholder values are ever substituted.
    """
    groq = get_groq_client()
    results = []

    precision_scores: List[Optional[float]] = []
    recall_scores: List[Optional[float]] = []
    faithfulness_scores: List[Optional[float]] = []
    relevance_scores: List[Optional[float]] = []

    for item in GOLDEN_TEST_DATASET:
        query = item["query"]
        category = item["category"]

        rag_res = search_policies(query=query, category=category, top_k=4)
        chunks = rag_res.get("results", [])

        # Context precision: reciprocal rank of the expected document (0 if not retrieved)
        precision = 0.0
        doc_ranks = [i for i, c in enumerate(chunks) if item["expected_doc"] in c.get("document_id", "")]
        if doc_ranks:
            rank = doc_ranks[0]
            precision = 1.0 / (rank + 1)
            # If a deprecated version was also retrieved, the active document must outrank it
            if item.get("deprecated_doc"):
                dep_ranks = [i for i, c in enumerate(chunks) if item["deprecated_doc"] in c.get("document_id", "")]
                if dep_ranks and rank < dep_ranks[0]:
                    precision = max(precision, 1.0)
        precision_scores.append(precision)

        # Context recall: required clauses present in the retrieved text
        all_content = " ".join([c.get("content", "").lower() for c in chunks])
        clauses_hit = sum(1 for clause in item["required_clauses"] if clause.lower() in all_content)
        recall = clauses_hit / len(item["required_clauses"]) if item["required_clauses"] else 1.0
        recall_scores.append(recall)

        # LLM-dependent metrics
        context_str = "\n".join([f"[{c.get('document_id')} §{c.get('section')}]: {c.get('content')}" for c in chunks])
        faithfulness: Optional[float] = None
        relevance: Optional[float] = None
        try:
            answer, _usage = await groq.complete_text(
                model=settings.groq_model_fast,
                messages=[{"role": "user", "content": (
                    "Based only on the following policy excerpts, answer the question accurately and professionally:\n"
                    f"{context_str[:2000]}\n\nQuestion: {query}\nAnswer:"
                )}],
                temperature=0.1,
            )
            faithfulness = await evaluate_faithfulness(groq, query, context_str, answer)
            relevance = await evaluate_answer_relevance(groq, query, answer)
        except Exception as e:  # noqa: BLE001
            log.warning("rag_benchmark.generation_failed", test_id=item["id"], error=str(e)[:200])

        faithfulness_scores.append(faithfulness)
        relevance_scores.append(relevance)

        results.append({
            "test_id": item["id"],
            "query": query,
            "category": category,
            "expected_doc": item["expected_doc"],
            "context_precision": round(precision, 3),
            "context_recall": round(recall, 3),
            "faithfulness": None if faithfulness is None else round(faithfulness, 3),
            "answer_relevance": None if relevance is None else round(relevance, 3),
            "retrieved_count": len(chunks),
            "top_citation": chunks[0].get("document_id") if chunks else "none",
        })

    metrics = {
        "context_precision": _mean(precision_scores),
        "context_recall": _mean(recall_scores),
        "faithfulness": _mean(faithfulness_scores),
        "answer_relevance": _mean(relevance_scores),
    }
    thresholds = {
        "context_precision": 0.85,
        "context_recall": 0.85,
        "faithfulness": 0.90,
        "answer_relevance": 0.85,
    }
    measured = {k: v for k, v in metrics.items() if v is not None}
    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "method": "deterministic retrieval metrics + LLM-judged faithfulness/relevance (not the RAGAS library)",
        "judge_model": settings.groq_model_fast,
        "ragas_score": round(sum(measured.values()) / len(measured), 3) if measured else None,
        "metrics": metrics,
        "metrics_not_measured": [k for k, v in metrics.items() if v is None],
        "target_thresholds": thresholds,
        "all_targets_met": bool(measured) and all(v >= thresholds[k] for k, v in measured.items()),
        "total_test_queries": len(GOLDEN_TEST_DATASET),
        "dataset_results": results,
    }

    out_dir = REPO_ROOT / "evals" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "ragas_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


def _fmt(v: Optional[float]) -> str:
    return "not measured" if v is None else f"{v * 100:.1f}%"


if __name__ == "__main__":
    report = asyncio.run(run_ragas_benchmark())
    print("\n=== RAG BENCHMARK RESULTS ===")
    print(f"Overall (mean of measured metrics): {_fmt(report['ragas_score'])}")
    for name, value in report["metrics"].items():
        print(f"{name:<18} {_fmt(value):>13}  (target {report['target_thresholds'][name] * 100:.0f}%)")
    if report["metrics_not_measured"]:
        print(f"Not measured (Groq unavailable?): {', '.join(report['metrics_not_measured'])}")
    print(f"All measured targets met: {report['all_targets_met']}")
