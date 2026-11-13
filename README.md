<!-- coderabbit-ai-generated:v1 -->

<!-- coderabbit-ai-generated-section:v1:2a087d0ceee79cb8439c6a8e78f1f543824d1c850965d3482079c3bf153c49a6 -->

# CMG ATLAS Admin Plugin

Administrative tools for the **Chaotic Minds Gaming (CMG)** ATLAS ecosystem.


## Backend setup

1. Install the dependencies with `python -m pip install -r backend/requirements.txt`.
2. Copy `backend/.env.example` to `backend/.env` and replace `SESSION_SECRET` with a random value. The example placeholder deliberately fails startup validation. Deployments using the previous published example value must replace it with a newly generated secret. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
3. Set `DISCORD_CLIENT_SECRET` in `backend/.env` (or the process environment). If migrating from YAML, move the secret out of `backend/config.yaml`. Keep real secrets out of tracked files. Set the non-secret Discord client ID, redirect URI, and allowed user IDs in `backend/config.yaml`.
4. Start the server from the repository root with `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`.

The backend refuses to start when `SESSION_SECRET` is missing or shorter than 32 characters, or when `DISCORD_CLIENT_SECRET` is empty. Keep `backend/.env` private; it is ignored by Git. Process environment values take precedence over the `.env` file.


<!-- /coderabbit-ai-generated:v1 -->