import json
import logging
from google import genai
from google.genai import types
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

EMAIL_PROMPT = """\
Write a cold outreach email from Parva Chaudhari to {contact_name} ({contact_title}) at {company}.

GREETING:
- Start with: "Hey {contact_first_name}," on its own line
- {contact_first_name} is the contact's first or given name
- If it looks like a full name (contains a space or comma), infer the correct given name: e.g. "Abraham Nurhssien, MBA" → "Abraham", "Man Si Leung" → "Man Si"

THEIR LINKEDIN:
Headline: {headline}
About: {about}
Recent experience: {recent_experience}

JOB CONTEXT:
- Role: {job_title}
- Team: {team_name}
- Key signals from JD: {key_signals}
- Relevant project: {relevant_project}
- Orbit: multi-tenant supply chain platform, GCP/FastAPI/Postgres, 24 Shopify stores, 66% sync speed improvement
- MindHive: open-source AI knowledge base, RAG, Gemini embeddings, pgvector, 75% latency reduction
- Portfolio: https://parvachaudhari.vercel.app
- GitHub: https://github.com/ParvaChaudhari

STRICT RULES:
- Subject (verbatim, do NOT change): "My pipeline scored {company} in the top 10%"
- Body must follow this exact narrative arc:

  Paragraph 1 (verbatim, do not change):
  "Most cold emails start with 'I'm excited.' Mine starts with a Python script that ranked your role in the top 10% of my queue."

  Paragraph 2 (2 sentences, one continuous flowing idea in plain natural prose):
  - Sentence 1: "That same instinct to [short action phrase] is what I put into {relevant_project}," followed immediately in the same sentence by the ONE concrete metric. No colon before the metric.
  - Sentence 2 (MANDATORY): Connect YOUR technical background to the role AND to their specific experience. Model it exactly on this pattern: "I believe this technical background aligns well with the {job_title} role on the {team_name} team at {company}, mirroring your own experience in [something specific from their headline or about]."
  - Write like a human talking to a peer. No parenthetical asides.

  Paragraph 3 (2 sentences, confident close):
  - Sentence 1: Assert the fit as a fact. Model it on this pattern: "My history of [short descriptor of your technical work] maps directly to what this role requires.".
  - Sentence 2: Portfolio link and ask written naturally: "You can find more of my work at https://parvachaudhari.vercel.app. Would love to chat if you have 15 minutes."

  Signature (verbatim):
  Best regards,
  Parva

- Tone: direct, peer-to-peer, no fluff
- BANNED: the em dash character. It must not appear anywhere in the body.
- BANNED phrases: "I am excited to" / "I hope this finds you well" / "I am passionate about" / "I recently built"
- Do NOT place a colon immediately before a metric (avoid patterns like "Orbit: a 66%")
- Do NOT make up details not in the profile
- The whole email must read as one continuous thought

Return ONLY valid JSON: {{"subject": "...", "body": "..."}}
"""


class EmailComposer:
    def __init__(self, model_name: str = "gemini-3-flash-preview"):
        self.model_name = model_name
        self.client = genai.Client()

    async def compose(
        self,
        contact_name: str,
        contact_first_name: str,
        contact_title: str,
        headline: str,
        about: str,
        recent_experience: str,
        company: str,
        job_title: str,
        team_name: str,
        key_signals: List[str],
        relevant_project: str,
    ) -> Dict[str, str]:
        """
        Compose a cold outreach email using the contact's full LinkedIn profile context.

        All fields are explicit — no dicts to pick apart here, the orchestrator
        extracts the relevant values and passes them directly.
        """
        try:
            prompt = EMAIL_PROMPT.format(
                contact_name=contact_name or "Hiring Manager",
                contact_first_name=contact_first_name or contact_name or "there",
                contact_title=contact_title or "Engineering Manager",
                headline=headline or "",
                about=(about or "")[:1500],          # cap to avoid token bloat
                recent_experience=recent_experience or "",
                company=company,
                job_title=job_title,
                team_name=team_name or "Engineering",
                key_signals=", ".join(key_signals) if key_signals else "",
                relevant_project=relevant_project or "Orbit",
            )

            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )
            data = json.loads(response.text)
            logger.info(f"Email composed for {contact_name} at {company}")
            return data

        except Exception as e:
            logger.error(f"Error composing email for {company}: {e}")
            return {
                "subject": f"My pipeline scored {company} in the top 10%",
                "body": (
                    f"Most cold emails start with 'I'm excited.' Mine starts with a Python script that ranked your role in the top 10% of my queue.\n\n"
                    f"I'd love to chat about the {job_title} role — more at https://parvachaudhari.vercel.app. Would you have 15 minutes?\n\n"
                    f"Best regards,\nParva"
                ),
            }
