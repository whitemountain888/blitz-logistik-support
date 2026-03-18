"""
Escalation Tool — Layer 3 (pure function, no framework dependency)
"""

import os
import json
import smtplib
from datetime import datetime
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

LOG_PATH = Path(__file__).parent.parent / "escalations.log"


class _EscalateToHuman:
    def invoke(self, inputs: dict) -> str:
        customer_issue = inputs.get("customer_issue", "")
        customer_message = inputs.get("customer_message", "")
        urgency = inputs.get("urgency", "normal")

        escalation_email = os.getenv("ESCALATION_EMAIL", "")
        company_name = os.getenv("COMPANY_NAME", "the company")
        persona_name = os.getenv("PERSONA_NAME", "AI Assistant")
        language = os.getenv("LANGUAGE", "en")
        timestamp = datetime.utcnow().isoformat()

        # Log (always)
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
            pass

        # Email (if SMTP configured)
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
                    f"Time: {timestamp}\nUrgency: {urgency}\n"
                    f"Issue: {customer_issue}\n\nCustomer message:\n{customer_message}\n\n"
                    f"— {persona_name}"
                )
                msg.attach(MIMEText(body, "plain"))
                with smtplib.SMTP_SSL(smtp_host, 465) as server:
                    server.login(smtp_user, smtp_pass)
                    server.sendmail(smtp_user, escalation_email, msg.as_string())
            except Exception:
                pass

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


escalate_to_human = _EscalateToHuman()
