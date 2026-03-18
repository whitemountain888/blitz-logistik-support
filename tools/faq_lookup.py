"""
FAQ Lookup Tool — Layer 3 (pure function, no framework dependency)
"""

from pathlib import Path

FAQ_PATH = Path(__file__).parent.parent / "faq.md"


class _FaqLookup:
    def invoke(self, inputs: dict) -> str:
        try:
            content = FAQ_PATH.read_text(encoding="utf-8").strip()
            if not content:
                return "The FAQ database is currently empty. Please escalate to a human agent."
            return f"FAQ KNOWLEDGE BASE:\n\n{content}"
        except FileNotFoundError:
            return "FAQ database not found. Please escalate to a human agent."
        except Exception as e:
            return f"Error reading FAQ: {str(e)}"


faq_lookup = _FaqLookup()
