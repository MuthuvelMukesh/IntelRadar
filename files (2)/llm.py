import json
import logging
import requests
from .config import OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_BASE_URL, VALID_CATEGORIES, VALID_REGIONS

logger = logging.getLogger(__name__)


class LLMClient:
    """Calls OpenRouter API for news classification and summarization."""

    def __init__(self):
        if not OPENROUTER_API_KEY:
            logger.warning("OPENROUTER_API_KEY is not set. LLM features disabled.")
        self.headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/antigravity-bot",
            "X-Title": "Antigravity News Bot",
        }

    def _call(self, prompt: str, max_tokens: int = 512) -> str | None:
        """Raw API call. Returns text content or None on failure."""
        if not OPENROUTER_API_KEY:
            return None
        payload = {
            "model": OPENROUTER_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.2,
        }
        try:
            r = requests.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"OpenRouter API error: {e}")
            return None

    def classify_and_summarize(self, text: str) -> dict:
        """
        Returns dict with keys: category, region, tags, summary, importance.
        Falls back gracefully on any failure.
        """
        categories_str = ", ".join(sorted(VALID_CATEGORIES))
        regions_str = ", ".join(sorted(VALID_REGIONS))

        prompt = f"""You are a professional financial and geopolitical news analyst.

Analyze this news item and return ONLY a valid JSON object — no markdown, no explanation.

News text:
\"\"\"
{text[:1500]}
\"\"\"

JSON schema to return:
{{
  "category": "<one of: {categories_str}>",
  "region": "<one of: {regions_str}, or null if not region-specific>",
  "tags": ["tag1", "tag2", "tag3"],
  "summary": "<1-2 sentence plain English summary>",
  "importance": <integer 0-10, where 10 = major breaking news>
}}

Rules:
- category must be exactly one of the listed values
- tags: 3-5 lowercase keywords, no hashtags
- importance: 8-10 for major market moves, central bank decisions, war/conflict, large hacks; 4-7 for notable news; 0-3 for routine updates
- Return ONLY the JSON object."""

        raw = self._call(prompt)
        return self._parse_result(raw)

    def generate_digest(self, items: list[dict], category: str | None = None) -> str:
        """
        Takes a list of summarized items and returns a cohesive digest paragraph.
        items: list of dicts with keys: category, summary, channel, date
        """
        if not items:
            return "No news items to summarize."

        label = f"**{category.upper()}**" if category else "**ALL CATEGORIES**"
        items_text = "\n".join(
            f"- [{i['category'].upper()} / {i['channel']}] {i['summary']}"
            for i in items[:30]
        )

        prompt = f"""You are a sharp financial news editor writing a morning briefing.

Below are individual news summaries from the last 24 hours for {label}.
Write a concise, well-structured digest (3-6 paragraphs). Group related stories. 
Use plain text (no markdown). Be direct and informative. Do NOT invent facts.

News items:
{items_text}

Digest:"""

        result = self._call(prompt, max_tokens=800)
        return result or "Could not generate digest."

    def _parse_result(self, raw: str | None) -> dict:
        """Parse LLM JSON response with fallback defaults."""
        default = {
            "category": "other",
            "region": None,
            "tags": [],
            "summary": "Could not process.",
            "importance": 0,
        }
        if not raw:
            return default
        try:
            # Strip markdown code fences if model adds them
            content = raw
            for marker in ("```json", "```"):
                content = content.replace(marker, "")
            content = content.strip()

            data = json.loads(content)

            # Validate / sanitize
            if data.get("category") not in VALID_CATEGORIES:
                data["category"] = "other"
            if data.get("region") not in VALID_REGIONS:
                data["region"] = None
            if not isinstance(data.get("tags"), list):
                data["tags"] = []
            data["importance"] = max(0, min(10, int(data.get("importance", 0))))

            return {**default, **data}
        except Exception as e:
            logger.warning(f"LLM parse error: {e} | raw: {raw[:200]}")
            return default
