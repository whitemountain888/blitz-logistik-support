# Template 1 — Customer Support Agent

**Tier:** Free (50 interactions/month)
**Framework:** LangGraph + Claude claude-sonnet-4-6 + Chainlit
**Deploy:** Render (web service)

The first factory template. Handles customer questions via FAQ lookup, escalates to human when needed.

---

## How the Factory Uses This

The factory fills `config.json` with client-specific values, copies `faq.md` with the client's content, then deploys to Render. Every `{{variable}}` in config.json is a factory injection point.

---

## WAT Layers

```
Layer 1 — WORKFLOW   → app.py       (Chainlit: session, auth, limits, routing)
Layer 2 — AGENT      → agent.py     (LangGraph: Claude decides when to use tools)
Layer 3 — TOOLS      → tools/       (faq_lookup, escalate_to_human)
```

---

## To Deploy Manually (for testing)

**1. Fill config.json**
Replace all `{{variables}}` with real values:
```json
{
  "agent_id": "000001-customer-support-de",
  "company_name": "Müller Logistik GmbH",
  "language": "de",
  "persona_name": "Müller-Assistent",
  "greeting": "Hallo! Ich bin der KI-Assistent von Müller Logistik. Wie kann ich Ihnen helfen?",
  "tone": "formal_german",
  "escalation_email": "support@mueller-logistik.de",
  "free_tier_limits": { "runs_per_month": 50 },
  "upgrade_cta": "Für unbegrenzten Zugriff kontaktieren Sie uns: upgrade@aurum-agency.de"
}
```

**2. Replace faq.md**
Copy the client's FAQ content into `faq.md`. Use `faq_sample.md` as format reference.

**3. Set env vars**
Copy `.env.example` to `.env` and fill in:
```
ANTHROPIC_API_KEY=sk-ant-...
APP_PASSWORD=clientpassword123
ESCALATION_EMAIL=support@client.de
```

**4. Run tests**
```bash
pip install -r requirements.txt
python tests.py
```
All 5 tests must pass before deploying.

**5. Run locally**
```bash
chainlit run app.py
```

**6. Deploy to Render**
- Push to GitHub repo
- Connect to Render → New Web Service
- Set env vars in Render dashboard
- Build: `pip install -r requirements.txt`
- Start: `chainlit run app.py --host 0.0.0.0 --port $PORT`

---

## Config Injection Points (for factory automation)

| Variable | Description | Example |
|---|---|---|
| `agent_id` | Unique ID for this agent | `000042-customer-support-de` |
| `company_name` | Client's company name | `Müller Logistik GmbH` |
| `language` | `de` or `en` | `de` |
| `persona_name` | Agent's name | `Müller-Assistent` |
| `greeting` | First message shown to user | `Hallo! Wie kann ich helfen?` |
| `tone` | `formal_german` / `professional` / `friendly` | `formal_german` |
| `escalation_email` | Where escalation emails go | `support@client.de` |
| `free_tier_limits.runs_per_month` | Monthly interaction cap | `50` |
| `upgrade_cta` | Upgrade call-to-action text | `Jetzt upgraden: ...` |

---

## File Structure

```
customer-support/
├── app.py              ← Layer 1: Chainlit workflow
├── agent.py            ← Layer 2: LangGraph agent + Claude
├── tools/
│   ├── __init__.py
│   ├── faq_lookup.py   ← Layer 3: FAQ search tool
│   └── escalation.py  ← Layer 3: Human escalation tool
├── config.json         ← Factory injection point (fill before deploy)
├── faq.md              ← Client FAQ content (replace before deploy)
├── faq_sample.md       ← Format reference
├── tests.py            ← 5 standard tests (must pass before deploy)
├── requirements.txt
├── render.yaml
├── .env.example
└── README.md
```

---

## Upgrade Path (when client pays)

- **Starter (€149/mo):** Increase `runs_per_month` to 500, add CRM logging skill
- **Pro (€399/mo):** Unlimited runs, add Slack/WhatsApp delivery, custom branding
- Both upgrades: update config.json + redeploy — no code changes needed
