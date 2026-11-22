from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database import Base
from app.models import Conversation, Document, DocumentChunk, Message, User


def test_study_data_relationships_persist_in_sqlite() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        user = User(email="student@example.com", password_hash="test-hash")
        document = Document(
            owner=user,
            original_filename="biology.pdf",
            storage_name="stored-1.pdf",
            size_bytes=1024,
            page_count=1,
            status="ready",
        )
        document.chunks.append(DocumentChunk(page_number=1, chunk_index=0, content="Cells contain DNA."))
        conversation = Conversation(owner=user, document=document, title="Biology review")
        conversation.messages.append(
            Message(role="assistant", content="Cells contain DNA.", citations=[{"page": 1}])
        )
        session.add(user)
        session.commit()

        saved_user = session.scalar(select(User).where(User.email == "student@example.com"))
        assert saved_user is not None
        assert saved_user.documents[0].chunks[0].content == "Cells contain DNA."
        assert saved_user.conversations[0].messages[0].citations == [{"page": 1}]

    engine.dispose()
