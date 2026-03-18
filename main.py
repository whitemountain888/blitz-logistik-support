"""
Customer Support Agent — FastAPI Backend (WAT Layer 1: Workflow)
"""

import os
import json
from pathlib import Path

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from agent import handle_message, CFG

app = FastAPI(title=CFG.get("company_name", "Support Agent"))

FRONTEND_DIR = Path(__file__).parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

APP_PASSWORD = os.getenv("APP_PASSWORD", "")


def _is_authed(request: Request) -> bool:
    if not APP_PASSWORD:
        return True
    return request.cookies.get("auth_token") == APP_PASSWORD


# ─── Health + Pages ───────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def home():
    html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    html = html.replace("{{COMPANY_NAME}}", CFG.get("company_name", "Support"))
    html = html.replace("{{PERSONA_NAME}}", CFG.get("persona_name", "Assistant"))
    html = html.replace("{{GREETING}}", CFG.get("greeting", "Hello! How can I help?"))
    html = html.replace("{{LANGUAGE}}", CFG.get("language", "en"))
    html = html.replace("{{HAS_PASSWORD}}", "true" if APP_PASSWORD else "false")
    return html


# ─── Auth ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    password: str


@app.post("/api/auth/login")
async def login(body: LoginRequest, response: Response):
    if APP_PASSWORD and body.password != APP_PASSWORD:
        raise HTTPException(status_code=401, detail="Incorrect password")
    response.set_cookie("auth_token", APP_PASSWORD or "open", httponly=True, max_age=86400 * 30)
    return {"ok": True}


# ─── Config (public values the frontend needs) ────────────────────────────────

@app.get("/api/config")
async def config():
    return {
        "company_name": CFG.get("company_name", ""),
        "persona_name": CFG.get("persona_name", ""),
        "greeting": CFG.get("greeting", ""),
        "language": CFG.get("language", "en"),
    }


# ─── Chat ─────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


@app.post("/api/chat")
async def chat(body: ChatRequest, request: Request):
    if not _is_authed(request):
        raise HTTPException(status_code=401, detail="Not authenticated")

    monthly_limit = CFG.get("free_tier_limits", {}).get("runs_per_month", 50)
    run_count = int(request.cookies.get("run_count", "0"))

    if run_count >= monthly_limit:
        cta = CFG.get("upgrade_cta", "Please contact us to upgrade.")
        lang = CFG.get("language", "en")
        msg = (
            f"Sie haben Ihr monatliches Kontingent von {monthly_limit} Anfragen erreicht. {cta}"
            if lang == "de"
            else f"You've reached your monthly limit of {monthly_limit} interactions. {cta}"
        )
        return JSONResponse({"response": msg, "limit_reached": True})

    response_text = handle_message(body.message, body.history)

    resp = JSONResponse({"response": response_text, "limit_reached": False})
    resp.set_cookie("run_count", str(run_count + 1), max_age=86400 * 30)
    return resp
