from io import BytesIO
from types import SimpleNamespace

from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

from app.services.pdf_processing import extract_pdf_chunks


def make_pdf() -> bytes:
    output = BytesIO()
    pdf = canvas.Canvas(output)
    pdf.drawString(48, 720, "Mitochondria produce energy for the cell.")
    pdf.showPage()
    pdf.drawString(48, 720, "Chloroplasts capture light energy for photosynthesis.")
    pdf.save()
    return output.getvalue()


def test_pdf_extraction_preserves_page_numbers() -> None:
    page_count, chunks = extract_pdf_chunks(make_pdf())

    assert page_count == 2
    assert chunks[0][0] == 1
    assert "Mitochondria" in chunks[0][2]
    assert chunks[1][0] == 2
    assert "Chloroplasts" in chunks[1][2]


def test_upload_lists_and_isolates_documents(client: TestClient, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.documents.get_settings",
        lambda: SimpleNamespace(upload_dir=str(tmp_path / "uploads"), max_upload_mb=15),
    )
    assert client.post(
        "/api/auth/register",
        json={"email": "first@example.com", "password": "a-good-password"},
    ).status_code == 201

    uploaded = client.post(
        "/api/documents",
        files={"file": ("cell-biology.pdf", make_pdf(), "application/pdf")},
    )
    assert uploaded.status_code == 201
    document_id = uploaded.json()["id"]
    assert uploaded.json()["page_count"] == 2
    assert uploaded.json()["status"] == "ready"
    assert len(client.get("/api/documents").json()) == 1

    client.post("/api/auth/logout")
    assert client.post(
        "/api/auth/register",
        json={"email": "second@example.com", "password": "another-password"},
    ).status_code == 201
    assert client.get("/api/documents").json() == []
    assert client.delete(f"/api/documents/{document_id}").status_code == 404


def test_upload_rejects_non_pdf_and_unreadable_pdf(client: TestClient) -> None:
    client.post("/api/auth/register", json={"email": "pdf@example.com", "password": "a-good-password"})
    wrong_type = client.post("/api/documents", files={"file": ("notes.txt", b"text", "text/plain")})
    invalid_pdf = client.post("/api/documents", files={"file": ("broken.pdf", b"not pdf", "application/pdf")})

    assert wrong_type.status_code == 415
    assert invalid_pdf.status_code == 422
