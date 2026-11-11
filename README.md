# chaotic-atlas-admin

## Backend setup

1. Install the dependencies with `python -m pip install -r backend/requirements.txt`.
2. Copy `backend/.env.example` to `backend/.env` and replace `SESSION_SECRET` with a random value. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
3. Set the Discord OAuth values and allowed user IDs in `backend/config.yaml`.
4. Start the server from the repository root with `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`.

The backend refuses to start when `SESSION_SECRET` is missing or shorter than 32 characters. Keep `backend/.env` private; it is ignored by Git.
