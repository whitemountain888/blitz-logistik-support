"""
Customer Support Agent — WAT Layer 2 (Decision-Making)

LangGraph state machine:
  START → chat_node → [tool_node if tool call] → chat_node → END

Claude claude-sonnet-4-6 with tool calling:
  - faq_lookup: search FAQ knowledge base
  - escalate_to_human: forward complex/angry issues to human
"""

import os
import json
from pathlib import Path
from typing import Annotated

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict

from tools import TOOLS

# ─── Config ───────────────────────────────────────────────────────────────────

CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config() -> dict:
    try:
        raw = CONFIG_PATH.read_text(encoding="utf-8")
        return json.loads(raw)
    except Exception as e:
        raise RuntimeError(f"Failed to load config.json: {e}")


CFG = load_config()

# Expose key config values as env vars so tools can read them without importing CFG
os.environ.setdefault("COMPANY_NAME", CFG.get("company_name", ""))
os.environ.setdefault("PERSONA_NAME", CFG.get("persona_name", ""))
os.environ.setdefault("LANGUAGE", CFG.get("language", "en"))
os.environ.setdefault("ESCALATION_EMAIL", CFG.get("escalation_email", ""))


# ─── System Prompt ────────────────────────────────────────────────────────────

TONE_INSTRUCTIONS = {
    "formal_german": "Be formal, use 'Sie' form, professional German business tone.",
    "professional": "Be professional, clear, and helpful.",
    "friendly": "Be warm, friendly, and approachable while staying professional.",
}

LANGUAGE_INSTRUCTIONS = {
    "de": "Always respond in German. Use natural, professional German.",
    "en": "Always respond in English. Use natural, professional English.",
}


def build_system_prompt(cfg: dict) -> str:
    tone = TONE_INSTRUCTIONS.get(cfg.get("tone", "professional"), "Be professional and helpful.")
    lang = LANGUAGE_INSTRUCTIONS.get(cfg.get("language", "en"), LANGUAGE_INSTRUCTIONS["en"])
    limit = cfg.get("free_tier_limits", {}).get("runs_per_month", 50)
    upgrade_cta = cfg.get("upgrade_cta", "")

    return f"""You are {cfg['persona_name']}, the AI customer support assistant for {cfg['company_name']}.

## Your Job
Help customers resolve their questions and issues efficiently and professionally.

## Tone & Language
{tone}
{lang}

## Tools
You have two tools:
1. **faq_lookup** — always use this FIRST to search the company FAQ before answering
2. **escalate_to_human** — use this when:
   - The FAQ does not contain a satisfactory answer after you've searched
   - The customer is frustrated, angry, or upset
   - The issue involves billing, contracts, or formal complaints
   - You've tried to help and cannot resolve the issue

## Rules
- ALWAYS call faq_lookup before giving any factual answer about {cfg['company_name']}
- NEVER make up information that isn't in the FAQ — escalate instead
- Keep responses concise — customers want fast answers
- One question at a time — don't overwhelm with multiple questions
- This is the free plan: {limit} interactions/month limit applies
- If the customer asks for features beyond the free plan: {upgrade_cta}

## Persona
You represent {cfg['company_name']}. Be helpful, stay on topic, protect the company's reputation."""


# ─── State ────────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


# ─── LLM + Graph ──────────────────────────────────────────────────────────────

def build_graph():
    llm = ChatAnthropic(
        model="claude-sonnet-4-6",
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        max_tokens=1024,
    ).bind_tools(TOOLS)

    system_prompt = build_system_prompt(CFG)

    def chat_node(state: AgentState):
        messages = [SystemMessage(content=system_prompt)] + state["messages"]
        response = llm.invoke(messages)
        return {"messages": [response]}

    graph = StateGraph(AgentState)
    graph.add_node("chat", chat_node)
    graph.add_node("tools", ToolNode(TOOLS))

    graph.add_edge(START, "chat")
    graph.add_conditional_edges("chat", tools_condition)
    graph.add_edge("tools", "chat")

    return graph.compile()


# Compile once at import time — reused across all Chainlit sessions
GRAPH = build_graph()


# ─── Public interface ─────────────────────────────────────────────────────────

def handle_message(user_text: str, history: list[dict]) -> str:
    """
    Process one user message through the agent graph.

    Args:
        user_text: The user's current message.
        history: List of {role, content} dicts from the session.

    Returns:
        The agent's response string.
    """
    messages = []
    for msg in history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))

    messages.append(HumanMessage(content=user_text))

    try:
        result = GRAPH.invoke({"messages": messages})
        last = result["messages"][-1]
        return last.content if hasattr(last, "content") else str(last)
    except Exception as e:
        print(f"Agent error: {e}")
        lang = CFG.get("language", "en")
        if lang == "de":
            return "Entschuldigung, ich hatte ein technisches Problem. Bitte versuchen Sie es erneut."
        return "I encountered a technical issue. Please try again."
