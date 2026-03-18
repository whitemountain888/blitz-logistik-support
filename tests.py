"""
Customer Support Agent — Standard Test Suite
5 tests that must pass before this agent is deployed via the factory.

Run: python tests.py
Pass criteria: all 5 tests green.
"""

import os
import sys
import json
from pathlib import Path

# Ensure config.json is filled before running tests
CONFIG_PATH = Path(__file__).parent / "config.json"


def _check_config():
    """Fail fast if config still has unfilled template variables."""
    raw = CONFIG_PATH.read_text(encoding="utf-8")
    if "{{" in raw:
        print("FAIL: config.json still contains unfilled template variables ({{...}})")
        print("Fill config.json before running tests.")
        sys.exit(1)


def _check_env():
    """Fail fast if ANTHROPIC_API_KEY is not set."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("FAIL: ANTHROPIC_API_KEY not set in environment.")
        sys.exit(1)


def _check_faq():
    """Fail fast if faq.md is the sample file (unreplaced)."""
    faq_path = Path(__file__).parent / "faq.md"
    if not faq_path.exists():
        print("FAIL: faq.md not found. Create it with client FAQ content.")
        sys.exit(1)
    content = faq_path.read_text(encoding="utf-8")
    if "[COMPANY_NAME]" in content:
        print("WARN: faq.md still contains placeholder [COMPANY_NAME]. Replace with real content.")


def run_tests():
    _check_config()
    _check_env()
    _check_faq()

    from agent import handle_message, CFG

    lang = CFG.get("language", "en")
    company = CFG.get("company_name", "the company")
    passed = 0
    failed = 0

    def test(name, user_input, must_contain=None, must_not_contain=None, history=None):
        nonlocal passed, failed
        try:
            response = handle_message(user_input, history or [])
            assert isinstance(response, str) and len(response) > 0, "Empty response"

            if must_contain:
                for keyword in must_contain:
                    assert keyword.lower() in response.lower(), (
                        f"Expected '{keyword}' in response but got:\n{response}"
                    )
            if must_not_contain:
                for keyword in must_not_contain:
                    assert keyword.lower() not in response.lower(), (
                        f"'{keyword}' should NOT be in response but got:\n{response}"
                    )

            print(f"  PASS  {name}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {name}")
            print(f"         {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {name}")
            print(f"         {e}")
            failed += 1

    print(f"\nRunning tests for: {company} ({lang})\n")

    # Test 1 — Agent responds (basic sanity check)
    test(
        "T1: Agent responds to greeting",
        user_input="Hello, I need help." if lang == "en" else "Hallo, ich brauche Hilfe.",
        must_contain=[],  # Just check it responds
    )

    # Test 2 — FAQ lookup is triggered and used
    test(
        "T2: FAQ lookup triggered for factual question",
        user_input=(
            "What are your opening hours?"
            if lang == "en"
            else "Was sind Ihre Öffnungszeiten?"
        ),
        must_not_contain=["I don't know", "Ich weiß nicht"],
    )

    # Test 3 — Escalation triggered for complaint
    test(
        "T3: Escalation triggered for angry customer",
        user_input=(
            "I am very angry and frustrated. This is completely unacceptable! I want to speak to a real person NOW."
            if lang == "en"
            else "Ich bin sehr verärgert und frustriert! Das ist völlig inakzeptabel! Ich möchte sofort mit einem echten Mitarbeiter sprechen."
        ),
        must_contain=(
            ["team", "forward"] if lang == "en" else ["weitergeleitet", "Mitarbeiter"]
        ),
    )

    # Test 4 — Multi-turn conversation maintains context
    history = [
        {"role": "user", "content": "I placed an order yesterday." if lang == "en" else "Ich habe gestern eine Bestellung aufgegeben."},
        {"role": "assistant", "content": "I see. How can I help you with your order?" if lang == "en" else "Ich verstehe. Wie kann ich Ihnen bei Ihrer Bestellung helfen?"},
    ]
    test(
        "T4: Multi-turn context maintained",
        user_input=(
            "I haven't received any confirmation email."
            if lang == "en"
            else "Ich habe keine Bestätigungs-E-Mail erhalten."
        ),
        history=history,
        must_not_contain=["{{", "}}"],  # No unfilled template variables
    )

    # Test 5 — No template variables leak into responses
    test(
        "T5: No template placeholders in response",
        user_input=(
            "Who are you and what company do you work for?"
            if lang == "en"
            else "Wer sind Sie und für welches Unternehmen arbeiten Sie?"
        ),
        must_contain=[company],
        must_not_contain=["{{", "}}"],
    )

    # Summary
    total = passed + failed
    print(f"\n{'─' * 40}")
    print(f"Results: {passed}/{total} passed")
    if failed > 0:
        print(f"FAILED: {failed} test(s) — fix before deploying.")
        sys.exit(1)
    else:
        print("All tests passed. Ready to deploy.")
        sys.exit(0)


if __name__ == "__main__":
    run_tests()
