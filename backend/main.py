import json
import os
import socket
from pathlib import Path

import httpx
import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from valve.source.a2s import NoResponseError, ServerQuerier

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

session_secret = os.environ.get("SESSION_SECRET", "")
if len(session_secret) < 32:
    raise RuntimeError("SESSION_SECRET must be set to a random value of at least 32 characters")

discord_client_secret = os.environ.get("DISCORD_CLIENT_SECRET", "").strip()
if not discord_client_secret:
    raise RuntimeError("DISCORD_CLIENT_SECRET must be set")

with (BASE_DIR / "config.yaml").open(encoding="utf-8") as config_file:
    config = yaml.safe_load(config_file)

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=session_secret)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DISCORD_API = "https://discord.com/api"
ALLOWED_USERS = config["discord"]["allowed_users"]


def is_admin(session):
    return session.get("user", {}).get("id") in ALLOWED_USERS


@app.get("/")
def home(request: Request):
    if not is_admin(request.session):
        return RedirectResponse("/login")
    return HTMLResponse(f"<h2>Welcome, {request.session['user']['username']}</h2><a href='/logout'>Logout</a>")


@app.get("/login")
def login():
    client_id = config["discord"]["client_id"]
    redirect_uri = config["discord"]["redirect_uri"]
    return RedirectResponse(
        f"{DISCORD_API}/oauth2/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope=identify"
    )


@app.get("/auth/callback")
async def auth_callback(code: str, request: Request):
    """Exchange a Discord code and store the authenticated user identity in the session."""
    data = {
        "client_id": config["discord"]["client_id"],
        "client_secret": discord_client_secret,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": config["discord"]["redirect_uri"],
    }
    async with httpx.AsyncClient() as client:
        token_response = await client.post(f"{DISCORD_API}/oauth2/token", data=data)
        token_response.raise_for_status()
        token = token_response.json().get("access_token")
        if not token:
            raise HTTPException(status_code=502, detail="Discord did not return an access token")

        user_response = await client.get(
            f"{DISCORD_API}/users/@me",
            headers={"Authorization": f"Bearer {token}"},
        )
        user_response.raise_for_status()
        user = user_response.json()
        request.session["user"] = {"id": user["id"], "username": user.get("username", "")}
    return RedirectResponse("/")


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login")


@app.get("/api/status")
def status(request: Request):
    if not is_admin(request.session):
        raise HTTPException(status_code=403)
    return {grid["id"]: is_port_open(grid["port"]) for grid in config["grids"]}


@app.get("/api/players")
def players(request: Request):
    """Return player details or a query error for each grid, restricted to admins."""
    if not is_admin(request.session):
        raise HTTPException(status_code=403)
    results = {}
    for grid in config["grids"]:
        try:
            with ServerQuerier(("127.0.0.1", grid["port"]), timeout=1) as server:
                info = server.info()
                player_info = server.players()
                results[grid["id"]] = {
                    "name": info["server_name"],
                    "map": info["map"],
                    "players": player_info["players"],
                    "max_players": info["max_players"],
                }
        except NoResponseError:
            results[grid["id"]] = {"error": "No response"}
        except Exception as error:
            results[grid["id"]] = {"error": str(error)}
    return results


def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.settimeout(0.5)
        return connection.connect_ex(("127.0.0.1", port)) == 0


@app.get("/api/leaderboard")
def leaderboard():
    leaderboard_path = BASE_DIR / "data" / "leaderboard.json"
    with leaderboard_path.open(encoding="utf-8") as leaderboard_file:
        return json.load(leaderboard_file)
