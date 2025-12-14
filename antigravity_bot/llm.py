import json
import google.generativeai as genai
from .config import LLM_API_KEY, VALID_CATEGORIES

class LLMClient:
    def __init__(self):
        if not LLM_API_KEY:
            print("Warning: LLM_API_KEY is not set.")
            return
            
        genai.configure(api_key=LLM_API_KEY)
        self.model = genai.GenerativeModel('gemini-pro')

    def classify_and_summarize(self, text):
        """
        Analyzes the text to determine the category, generate tags, and write a summary.
        Returns a dictionary with 'category', 'tags', and 'summary'.
        """
        prompt = f"""
        You are a news analyst. Analyze the following news item:
        
        "{text}"
        
        Tasks:
        1. Classify it into exactly ONE of these categories: {', '.join(VALID_CATEGORIES)}.
           If it doesn't fit well, use "other".
        2. Generate 3-5 relevant tags (comma separated).
        3. Write a concise 1-sentence summary.
        
        Return ONLY a JSON object with keys: "category", "tags", "summary".
        Do not include Markdown formatting (like ```json).
        """

        try:
            response = self.model.generate_content(prompt)
            content = response.text.strip()
            
            # Clean up potential markdown code blocks if the model includes them
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            content = content.strip()
            
            data = json.loads(content)
            
            # Validate category
            if data.get("category") not in VALID_CATEGORIES:
                data["category"] = "other"
                
            return data
            
        except Exception as e:
            print(f"LLM Error: {e}")
            return {
                "category": "other",
                "tags": "error",
                "summary": "Could not process text."
            }
