"""
Customer Support Agent — Core Logic (WAT Layer 2)

Uses raw Anthropic SDK with tool_use. No LangChain/LangGraph — lightweight and fast.
Tool loop: Claude decides → calls tool → gets result → responds.
"""

import os
import json
from pathlib import Path

import anthropic

# ─── Config ───────────────────────────────────────────────────────────────────

CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config() -> dict:
    raw = CONFIG_PATH.read_text(encoding="utf-8")
    return json.loads(raw)


CFG = load_config()

os.environ.setdefault("COMPANY_NAME", CFG.get("company_name", ""))
os.environ.setdefault("PERSONA_NAME", CFG.get("persona_name", ""))
os.environ.setdefault("LANGUAGE", CFG.get("language", "en"))
os.environ.setdefault("ESCALATION_EMAIL", CFG.get("escalation_email", ""))

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env automatically

# ─── Tools (schema only — execution in tools/) ────────────────────────────────

TOOLS = [
    {
        "name": "faq_lookup",
        "description": "Search the company FAQ knowledge base for an answer to a customer question. Always call this before answering factual questions about the company.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The customer's question to look up."}
            },
            "required": ["query"]
        }
    },
    {
        "name": "escalate_to_human",
        "description": "Escalate a customer issue to a human agent. Use when: FAQ has no answer, customer is angry/frustrated, issue involves billing or complaints.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_issue": {"type": "string", "description": "One-sentence summary of the issue."},
                "customer_message": {"type": "string", "description": "The customer's exact last message."},
                "urgency": {"type": "string", "enum": ["normal", "urgent"], "description": "Use 'urgent' for angry customers or billing issues."}
            },
            "required": ["customer_issue", "customer_message"]
        }
    }
]

# ─── System Prompt ────────────────────────────────────────────────────────────

TONE_MAP = {
    "formal_german": "Formal and professional. Always use 'Sie' form in German.",
    "professional": "Professional, clear, and helpful.",
    "friendly": "Warm and friendly while staying professional.",
}

LANG_MAP = {
    "de": "Always respond in German (Deutsch). Use natural, professional German.",
    "en": "Always respond in English. Use natural, professional English.",
}


def build_system_prompt() -> str:
    tone = TONE_MAP.get(CFG.get("tone", "professional"), "Be professional and helpful.")
    lang = LANG_MAP.get(CFG.get("language", "en"), LANG_MAP["en"])
    limit = CFG.get("free_tier_limits", {}).get("runs_per_month", 50)
    cta = CFG.get("upgrade_cta", "")
    company = CFG["company_name"]
    persona = CFG["persona_name"]

    return f"""You are {persona}, the AI customer support assistant for {company}.

TONE: {tone}
LANGUAGE: {lang}

TOOLS:
- faq_lookup: ALWAYS call this first before answering any factual question about {company}
- escalate_to_human: use when FAQ has no answer, customer is upset, or issue involves billing/complaints

RULES:
- Never invent information not in the FAQ — escalate instead
- Keep responses concise — customers want fast answers
- Free plan limit: {limit} interactions/month
- If customer asks for premium features: {cta}

You represent {company}. Be helpful, stay on topic."""


SYSTEM_PROMPT = build_system_prompt()


# ─── Tool execution ───────────────────────────────────────────────────────────

def _execute_tool(name: str, inputs: dict) -> str:
    if name == "faq_lookup":
        from tools.faq_lookup import faq_lookup
        return faq_lookup.invoke(inputs)
    if name == "escalate_to_human":
        from tools.escalation import escalate_to_human
        return escalate_to_human.invoke(inputs)
    return f"Unknown tool: {name}"


# ─── Message handling ─────────────────────────────────────────────────────────

def handle_message(user_text: str, history: list[dict]) -> str:
    """
    Process one user message through Claude with tool calling.

    Args:
        user_text: Current message from the user.
        history: List of {role, content} dicts from the session.

    Returns:
        Assistant response string.
    """
    messages = []
    for msg in history:
        role = msg.get("role")
        content = msg.get("content", "")
        if role in ("user", "assistant"):
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": user_text})

    try:
        for _ in range(5):  # max 5 tool rounds
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if hasattr(block, "text"):
                        return block.text
                return ""

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = _execute_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
                continue

            break

        return "I was unable to process your request. Please try again."

    except Exception as e:
        print(f"Agent error: {e}")
        lang = CFG.get("language", "en")
        if lang == "de":
            return "Entschuldigung, ich hatte ein technisches Problem. Bitte versuchen Sie es erneut."
        return "I encountered a technical issue. Please try again."
