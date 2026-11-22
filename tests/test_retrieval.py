from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.models import Document, DocumentChunk, User
from app.services.retrieval import rank_bm25, retrieve_chunks


def test_bm25_ranks_matching_text_and_ignores_unmatched_text() -> None:
    scores = rank_bm25(
        "mitochondria energy",
        ["Mitochondria produce energy in cells", "The history of ancient Rome"],
    )

    assert scores[0] > scores[1]
    assert scores[1] == 0


def test_retrieval_filters_by_owner_and_keeps_page_citations() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        first = User(email="reader1@example.com", password_hash="hash")
        second = User(email="reader2@example.com", password_hash="hash")
        first_document = Document(
            owner=first, original_filename="biology.pdf", storage_name="one.pdf", size_bytes=5, page_count=1, status="ready"
        )
        second_document = Document(
            owner=second, original_filename="other.pdf", storage_name="two.pdf", size_bytes=5, page_count=1, status="ready"
        )
        first_document.chunks.append(
            DocumentChunk(page_number=7, chunk_index=0, content="Mitochondria convert nutrients into usable cellular energy.")
        )
        second_document.chunks.append(
            DocumentChunk(page_number=2, chunk_index=0, content="Mitochondria and energy are explained here too.")
        )
        db.add_all([first, second])
        db.commit()

        results = retrieve_chunks(db, owner_id=first.id, question="How do mitochondria make energy?")
        assert len(results) == 1
        assert results[0].filename == "biology.pdf"
        assert results[0].page_number == 7
        assert retrieve_chunks(db, owner_id=first.id, question="ancient Rome") == []

    engine.dispose()
