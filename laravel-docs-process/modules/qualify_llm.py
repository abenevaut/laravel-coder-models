"""LLM-based qualification module for Q&A pairs.

Qualifies and enriches Q&A pairs using a Large Language Model API:
- Filters non-useful pairs
- Adds technical tags
- Adds difficulty level
- Validates code presence
"""

import json
import sys
import time
from typing import Any, Optional

try:
    import requests
except ImportError:
    requests = None


# Default configuration
DEFAULT_CONFIG = {
    "api_url": "http://localhost:11434",
    "model": "qwen3.5:4b-mlx",
    "timeout": 120,
    "batch_size": 10
}

# Prompt template for LLM qualification
QUALIFICATION_PROMPT = """
Analyse cette paire Q/R pour un modèle expert Laravel (v10-13) :
---
Question: {instruction}
Réponse: {output}
---
Réponds avec un JSON valide contenant EXACTEMENT ces champs :
{{
    "useful": true/false,
    "tags": ["tag1", "tag2", "tag3"],
    "level": "débutant"|"intermédiaire"|"avancé",
    "has_code": true/false
}}
Ne réponds que par le JSON, sans commentaire.
"""


class LLMQualifier:
    """Qualifies Q&A pairs using a LLM API."""
    
    def __init__(self, api_url: str = None, model: str = None, timeout: int = 120):
        """Initialize the qualifier.
        
        Args:
            api_url: LLM API endpoint URL (default: http://localhost:11434)
            model: LLM model name (default: qwen3.5:4b-mlx)
            timeout: Timeout in seconds for API requests
        """
        self.api_url = api_url or DEFAULT_CONFIG["api_url"]
        self.model = model or DEFAULT_CONFIG["model"]
        self.timeout = timeout
        self._session = None
        
        # Check if requests is available
        if requests is None:
            raise RuntimeError(
                "requests library is required for API-based LLM qualification. "
                "Install it with: pip install requests"
            )
        
        # Create a session with timeout
        self._session = requests.Session()
        self._session.timeout = timeout
    
    def _check_api_available(self) -> None:
        """Check if the API is available."""
        try:
            response = self._session.get(f"{self.api_url}/api/tags")
            response.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"LLM API not available at {self.api_url}: {e}")
    
    def _call_llm(self, prompt: str) -> str:
        """Call the LLM API with a prompt and return the response."""
        url = f"{self.api_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        
        try:
            response = self._session.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except requests.RequestException as e:
            raise RuntimeError(f"LLM API call failed: {e}")
    
    def _extract_json(self, response: str) -> dict[str, Any]:
        """Extract JSON from LLM response."""
        # Try to find JSON in response
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            json_str = response[start:end]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        # Fallback: return default values
        return {
            "useful": True,
            "tags": [],
            "level": "intermédiaire",
            "has_code": False
        }
    
    def qualify(self, qa: dict) -> dict:
        """Qualify a single Q&A pair using LLM.
        
        Args:
            qa: Q&A pair dict with 'instruction' and 'output' keys
            
        Returns:
            Enriched Q&A pair with qualification metadata
        """
        prompt = QUALIFICATION_PROMPT.format(
            instruction=qa.get("instruction", ""),
            output=qa.get("output", "")
        )
        
        response = self._call_llm(prompt)
        qualification = self._extract_json(response)
        
        # Add qualification metadata to Q&A
        return {
            **qa,
            "qualification": {
                "useful": qualification.get("useful", True),
                "tags": qualification.get("tags", []),
                "level": qualification.get("level", "intermédiaire"),
                "has_code": qualification.get("has_code", False)
            }
        }
    
    def qualify_batch(self, qa_list: list[dict], batch_size: int = 10) -> list[dict]:
        """Qualify a batch of Q&A pairs.
        
        Args:
            qa_list: List of Q&A pairs to qualify
            batch_size: Number of pairs to process at once
            
        Returns:
            List of qualified Q&A pairs
        """
        qualified = []
        for i in range(0, len(qa_list), batch_size):
            batch = qa_list[i:i + batch_size]
            for qa in batch:
                try:
                    qualified.append(self.qualify(qa))
                    # Rate limiting: sleep between requests
                    time.sleep(0.1)  # 100ms delay to avoid overwhelming the API
                except Exception as e:
                    print(f"Warning: Failed to qualify Q&A: {e}", file=sys.stderr)
                    # Keep the original Q&A without qualification
                    qualified.append(qa)
        return qualified


def qualify_llm(data: dict, **kwargs) -> dict:
    """Pipeline step: Qualify Q&A pairs using LLM.
    
    This is a placeholder step that would be called after generate_qa.
    In practice, this step needs to be called on the complete Q&A list,
    not per-file, so it's better to call it from main.py after pipeline completion.
    
    Note: This step requires requests library and a running LLM API.
    """
    # This step is a no-op in the per-file pipeline
    # LLM qualification should be done on the complete Q&A list in main.py
    return data
