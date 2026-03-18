"""
Customer Support Agent — Chainlit UI (WAT Layer 1: Workflow)

Handles: session init, message routing, file upload, auth.
Delegates all agent reasoning to agent.py.
"""

import os
import json
from pathlib import Path
from io import BytesIO

import chainlit as cl
from dotenv import load_dotenv

load_dotenv()

from agent import handle_message, CFG

# ─── Auth ─────────────────────────────────────────────────────────────────────
# Password-protect the agent. Set APP_PASSWORD in env vars on Render.

@cl.password_auth_callback
def auth_callback(username: str, password: str):
    app_password = os.getenv("APP_PASSWORD", "")
    if not app_password:
        # No password set — open access (fine for demo/testing)
        return cl.User(identifier=username or "user", metadata={"role": "user"})
    if password == app_password:
        return cl.User(identifier=username or "user", metadata={"role": "user"})
    return None


# ─── Session start ────────────────────────────────────────────────────────────

@cl.on_chat_start
async def on_start():
    cl.user_session.set("history", [])
    cl.user_session.set("run_count", 0)

    await cl.Message(content=CFG.get("greeting", "Hello! How can I help you today?")).send()


# ─── Message handler ──────────────────────────────────────────────────────────

@cl.on_message
async def on_message(message: cl.Message):
    history = cl.user_session.get("history", [])
    run_count = cl.user_session.get("run_count", 0)

    # Free tier limit check
    monthly_limit = CFG.get("free_tier_limits", {}).get("runs_per_month", 50)
    if run_count >= monthly_limit:
        upgrade_cta = CFG.get("upgrade_cta", "Please contact us to upgrade.")
        lang = CFG.get("language", "en")
        if lang == "de":
            limit_msg = f"Sie haben Ihr monatliches Kontingent von {monthly_limit} Anfragen erreicht. {upgrade_cta}"
        else:
            limit_msg = f"You've reached your monthly limit of {monthly_limit} interactions. {upgrade_cta}"
        await cl.Message(content=limit_msg).send()
        return

    # Handle file uploads
    content = message.content
    if message.elements:
        for el in message.elements:
            path = getattr(el, "path", None)
            if path:
                try:
                    text = _extract_text(el.name, Path(path).read_bytes())
                    if text:
                        content += f"\n\n[Uploaded file: {el.name}]\n{text}"
                except Exception:
                    pass

    # Show thinking indicator
    thinking = cl.Message(content="")
    await thinking.send()

    # Run agent
    response = handle_message(content, history)

    # Update message in place
    thinking.content = response
    await thinking.update()

    # Update session state
    history.append({"role": "user", "content": content})
    history.append({"role": "assistant", "content": response})
    cl.user_session.set("history", history)
    cl.user_session.set("run_count", run_count + 1)


# ─── File text extraction ─────────────────────────────────────────────────────

def _extract_text(filename: str, file_bytes: bytes) -> str | None:
    name = filename.lower()
    try:
        if name.endswith(".txt"):
            return file_bytes.decode("utf-8")
        if name.endswith(".pdf"):
            from pypdf import PdfReader
            reader = PdfReader(BytesIO(file_bytes))
            pages = [p.extract_text() for p in reader.pages if p.extract_text()]
            return "\n".join(pages) or None
        if name.endswith(".docx"):
            from docx import Document
            doc = Document(BytesIO(file_bytes))
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            return text or None
    except Exception:
        return None
    return None
