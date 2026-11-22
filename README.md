# AI Study Assistant MVP

A learning-focused project for building a document-grounded study assistant in small, explainable milestones.

## Current milestone

The backend currently includes secure account routes, SQLAlchemy records for students, documents, page-aware chunks, conversations, and messages, plus PDF upload, extraction, and owner-scoped library endpoints. RAG chat and the browser interface are next.

## Local setup with Python

1. Use Python 3.10 or newer.
2. Copy `.env.example` to `.env` if one does not already exist. Keep real secrets only in `.env`; never put them in `.env.example` or commit them.
3. Create a virtual environment and install the app:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -e ".[dev]"
   ```

4. Start the API:

   ```powershell
   python -m uvicorn app.main:app --reload
   ```

5. Open `http://127.0.0.1:8000/docs`. `/health` checks the API process; `/ready` checks the configured database.

Local development defaults to SQLite, so no database server is required. Set `DATABASE_URL` to a PostgreSQL URL when a PostgreSQL server is available. PostgreSQL remains the planned database for multi-user deployment. `GEMINI_API_KEY` is not used by this milestone; add a newly generated key to your ignored `.env` only when Gemini integration is implemented. Set a unique `JWT_SECRET` before deployment and enable secure cookies behind HTTPS. Never put secrets in source code, `.env.example`, Git history, or a packaged executable.

PDF uploads are limited to 15 MB by default. Text is extracted page by page; scanned PDFs without an OCR text layer are rejected with a clear message. Original files and page-aware chunks are stored per user, and uploaded PDFs are excluded from Git.

## Design notes

- PostgreSQL will hold structured application data for the multi-user version. SQLite is used only to make local development straightforward.
- `/health` and `/ready` answer different operational questions: a running process may still be unable to reach its database.
- The database URL is configurable so credentials are not hard-coded in application modules.

## Current limitations

There are no database models or migrations yet, and no authentication, upload, PDF extraction, embeddings, LLM calls, or UI. This is a development foundation, not a production deployment.
