"""
FAQ Lookup Tool — Layer 3 (Execution only, no reasoning)

MVP: loads full faq.md into context. Claude extracts the relevant answer.
Production upgrade: swap return value for vector search over faq chunks.
"""

from pathlib import Path
from langchain_core.tools import tool

FAQ_PATH = Path(__file__).parent.parent / "faq.md"


@tool
def faq_lookup(query: str) -> str:
    """Search the company FAQ knowledge base for an answer to a customer question.

    Args:
        query: The customer's question or topic to look up.

    Returns:
        The FAQ content relevant to the query, or a not-found message.
    """
    try:
        content = FAQ_PATH.read_text(encoding="utf-8").strip()
        if not content:
            return "The FAQ database is currently empty. Please escalate to a human agent."
        # MVP: return full FAQ — Claude reads it and extracts the relevant answer.
        # Production: replace with semantic search returning top-3 chunks.
        return f"FAQ KNOWLEDGE BASE:\n\n{content}"
    except FileNotFoundError:
        return "FAQ database file not found. Please escalate to a human agent."
    except Exception as e:
        return f"Error reading FAQ database: {str(e)}"
