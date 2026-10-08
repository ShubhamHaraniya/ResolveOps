"""
Section-Aware Markdown Chunker for ResolveOps RAG Policy Engine.
Splits documents on Markdown H2 and H3 header boundaries while preserving
YAML frontmatter metadata and hierarchical document context.
"""
from dataclasses import dataclass, asdict
from pathlib import Path
import re
from typing import Optional
import yaml


@dataclass
class PolicyChunk:
    chunk_id: str
    document_id: str
    title: str
    version: int
    section: str
    subsection: Optional[str]
    effective_date: str
    status: str  # "active" | "deprecated"
    content: str
    source_file: str
    owner: str = "policy@northwindcloud.com"
    superseded_by: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


def _slugify(text: str) -> str:
    """Normalize text into an alphanumeric identifier slug."""
    clean = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "-", clean).strip("-")


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter and markdown body."""
    frontmatter = {}
    body = content

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            raw_fm = parts[1].strip()
            body = parts[2].strip()
            try:
                frontmatter = yaml.safe_load(raw_fm) or {}
            except Exception:
                frontmatter = {}

    return frontmatter, body


def chunk_document(file_path: Path) -> list[PolicyChunk]:
    """
    Parse a single markdown policy file into section-aware PolicyChunk objects.
    """
    raw_text = file_path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(raw_text)

    doc_id = frontmatter.get("document_id", file_path.stem)
    title = frontmatter.get("title", doc_id.replace("-", " ").title())
    version = int(frontmatter.get("version", 1))
    status = frontmatter.get("status", "active")
    effective_date = str(frontmatter.get("effective_date", "2025-01-01"))
    owner = frontmatter.get("owner", "policy@northwindcloud.com")
    superseded_by = frontmatter.get("superseded_by")

    chunks: list[PolicyChunk] = []

    # Split lines and parse H1, H2, H3
    lines = body.splitlines()
    current_section = "Overview"
    current_subsection: Optional[str] = None
    current_content_lines: list[str] = []
    chunk_counter = 1

    def flush_chunk():
        nonlocal chunk_counter, current_content_lines
        content_text = "\n".join(current_content_lines).strip()
        if len(content_text) >= 40:  # Skip trivial headings without content
            sec_slug = _slugify(current_section)
            sub_slug = f"-{_slugify(current_subsection)}" if current_subsection else ""
            chunk_id = f"{doc_id}-{sec_slug}{sub_slug}-{chunk_counter}"

            # Format enriched content for high-precision embedding & retrieval
            enriched_content = (
                f"Policy: {title} (v{version}, status: {status})\n"
                f"Section: {current_section}"
                + (f" > {current_subsection}" if current_subsection else "")
                + f"\n\n{content_text}"
            )

            chunks.append(
                PolicyChunk(
                    chunk_id=chunk_id,
                    document_id=doc_id,
                    title=title,
                    version=version,
                    section=current_section,
                    subsection=current_subsection,
                    effective_date=effective_date,
                    status=status,
                    content=enriched_content,
                    source_file=file_path.name,
                    owner=owner,
                    superseded_by=superseded_by,
                )
            )
            chunk_counter += 1
        current_content_lines = []

    for line in lines:
        # Check for H2 header
        h2_match = re.match(r"^##\s+(.+)$", line)
        if h2_match:
            flush_chunk()
            current_section = h2_match.group(1).strip()
            current_subsection = None
            continue

        # Check for H3 header
        h3_match = re.match(r"^###\s+(.+)$", line)
        if h3_match:
            flush_chunk()
            current_subsection = h3_match.group(1).strip()
            continue

        # Ignore standalone H1 title lines from body since title is in frontmatter
        if line.startswith("# "):
            continue

        current_content_lines.append(line)

    flush_chunk()

    # Fallback if document had no H2/H3 headers
    if not chunks and body.strip():
        chunks.append(
            PolicyChunk(
                chunk_id=f"{doc_id}-overview-1",
                document_id=doc_id,
                title=title,
                version=version,
                section="Overview",
                subsection=None,
                effective_date=effective_date,
                status=status,
                content=f"Policy: {title} (v{version})\n\n{body.strip()}",
                source_file=file_path.name,
                owner=owner,
                superseded_by=superseded_by,
            )
        )

    return chunks


def chunk_all_documents(docs_dir: Path) -> list[PolicyChunk]:
    """Parse all markdown documents in the specified directory."""
    all_chunks: list[PolicyChunk] = []
    for md_file in sorted(docs_dir.glob("*.md")):
        doc_chunks = chunk_document(md_file)
        all_chunks.extend(doc_chunks)
    return all_chunks
