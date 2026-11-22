import math
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document, DocumentChunk

TOKEN_PATTERN = re.compile(r"[a-z0-9]+", re.IGNORECASE)


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: int
    document_id: int
    filename: str
    page_number: int
    content: str
    score: float


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


def rank_bm25(query: str, documents: list[str], k1: float = 1.5, b: float = 0.75) -> list[float]:
    """Score documents with BM25, a compact lexical retrieval baseline."""
    query_terms = set(tokenize(query))
    tokenized = [tokenize(document) for document in documents]
    count = len(tokenized)
    if not query_terms or not count:
        return [0.0] * count

    average_length = sum(map(len, tokenized)) / count or 1.0
    document_frequency: dict[str, int] = {}
    term_frequencies: list[dict[str, int]] = []
    for terms in tokenized:
        frequencies: dict[str, int] = {}
        for term in terms:
            frequencies[term] = frequencies.get(term, 0) + 1
        term_frequencies.append(frequencies)
        for term in frequencies:
            document_frequency[term] = document_frequency.get(term, 0) + 1

    scores: list[float] = []
    for frequencies, terms in zip(term_frequencies, tokenized):
        score = 0.0
        length = len(terms)
        for term in query_terms:
            frequency = frequencies.get(term, 0)
            if frequency == 0:
                continue
            inverse_document_frequency = math.log(
                1 + (count - document_frequency[term] + 0.5) / (document_frequency[term] + 0.5)
            )
            denominator = frequency + k1 * (1 - b + b * length / average_length)
            score += inverse_document_frequency * frequency * (k1 + 1) / denominator
        scores.append(score)
    return scores


def retrieve_chunks(
    db: Session,
    *,
    owner_id: int,
    question: str,
    document_id: int | None = None,
    limit: int = 4,
) -> list[RetrievedChunk]:
    """Retrieve relevant page chunks, always filtering by server-authenticated owner."""
    statement = (
        select(DocumentChunk, Document)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(Document.owner_id == owner_id, Document.status == "ready")
    )
    if document_id is not None:
        statement = statement.where(Document.id == document_id)

    rows = db.execute(statement).all()
    if not rows:
        return []
    scores = rank_bm25(question, [chunk.content for chunk, _ in rows])
    ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)
    results: list[RetrievedChunk] = []
    for row_index, score in ranked:
        if score <= 0:
            break
        chunk, document = rows[row_index]
        results.append(
            RetrievedChunk(
                chunk_id=chunk.id,
                document_id=document.id,
                filename=document.original_filename,
                page_number=chunk.page_number,
                content=chunk.content,
                score=score,
            )
        )
        if len(results) >= limit:
            break
    return results
