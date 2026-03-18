"""
Escalation Tool — Layer 3 (Execution only, no reasoning)

Logs escalation to file and optionally sends email via SMTP.
If SMTP env vars are not set, logs only (safe default for MVP).
"""

import os
import json
import smtplib
from datetime import datetime
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from langchain_core.tools import tool

LOG_PATH = Path(__file__).parent.parent / "escalations.log"


@tool
def escalate_to_human(
    customer_issue: str,
    customer_message: str,
    urgency: str = "normal"
) -> str:
    """Escalate a customer issue to a human agent.

    Use this when:
    - The FAQ does not contain a satisfactory answer
    - The customer is frustrated, angry, or upset
    - The issue involves money, contracts, or complaints
    - You have tried twice and cannot resolve the issue

    Args:
        customer_issue: One-sentence summary of the issue.
        customer_message: The customer's exact last message.
        urgency: 'normal' or 'urgent'. Use 'urgent' for angry customers or billing issues.

    Returns:
        Confirmation message to show the customer.
    """
    escalation_email = os.getenv("ESCALATION_EMAIL", "")
    company_name = os.getenv("COMPANY_NAME", "the company")
    persona_name = os.getenv("PERSONA_NAME", "AI Assistant")
    language = os.getenv("LANGUAGE", "en")

    timestamp = datetime.utcnow().isoformat()

    # --- Log to file (always) ---
    log_entry = {
        "timestamp": timestamp,
        "urgency": urgency,
        "issue": customer_issue,
        "customer_message": customer_message,
    }
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception:
        pass  # Don't crash if log write fails

    # --- Send email if SMTP is configured ---
    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")

    if smtp_host and smtp_user and smtp_pass and escalation_email:
        try:
            msg = MIMEMultipart()
            msg["From"] = smtp_user
            msg["To"] = escalation_email
            msg["Subject"] = f"[{urgency.upper()}] Customer Escalation — {company_name}"
            body = (
                f"Time: {timestamp}\n"
                f"Urgency: {urgency}\n"
                f"Issue: {customer_issue}\n\n"
                f"Customer's last message:\n{customer_message}\n\n"
                f"— {persona_name} ({company_name})"
            )
            msg.attach(MIMEText(body, "plain"))
            with smtplib.SMTP_SSL(smtp_host, 465) as server:
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, escalation_email, msg.as_string())
        except Exception:
            pass  # Email failure is non-fatal — escalation is already logged

    # --- Response to customer (language-aware) ---
    if language == "de":
        return (
            "Ich habe Ihr Anliegen an unser Team weitergeleitet. "
            "Ein Mitarbeiter wird sich so schnell wie möglich bei Ihnen melden. "
            "Vielen Dank für Ihre Geduld."
        )
    return (
        "I've forwarded your issue to our team. "
        "A team member will get back to you as soon as possible. "
        "Thank you for your patience."
    )
