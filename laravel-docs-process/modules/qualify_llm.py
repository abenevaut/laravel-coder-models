"""LLM-based qualification module for Q&A pairs.

Qualifies and enriches Q&A pairs using a Large Language Model API:
- Filters non-useful pairs
- Adds technical tags
- Adds difficulty level
- Validates code presence
- Adds weight based on level for fine-tuning
"""

import json
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Optional

try:
    import requests
except ImportError:
    requests = None


@dataclass
class LLMConfig:
    """Configuration for LLM API."""
    enabled: bool = False
    api_url: str = "https://api.mistral.ai/v1"
    model: str = "mistral-small"
    api_key: Optional[str] = None
    timeout: int = 120
    batch_size: int = 10


# Weight mapping based on level for fine-tuning
LEVEL_WEIGHTS = {
    "débutant": 1.0,
    "intermédiaire": 1.5,
    "avancé": 2.0
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
    
    def __init__(self, api_url: str = None, model: str = None, api_key: str = None, timeout: int = 120):
        """Initialize the qualifier.
        
        Args:
            api_url: LLM API endpoint URL (default: https://api.mistral.ai/v1)
            model: LLM model name (default: mistral-small)
            api_key: API key for authentication
            timeout: Timeout in seconds for API requests
        """
        self.api_url = api_url or "https://api.mistral.ai/v1"
        self.model = model or "mistral-small"
        self.api_key = api_key
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
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            self._headers["Authorization"] = f"Bearer {self.api_key}"
    
    def _check_api_available(self) -> None:
        """Check if the API is available."""
        try:
            response = self._session.get(f"{self.api_url}/api/tags")
            response.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"LLM API not available at {self.api_url}: {e}")
    
    def _call_llm(self, prompt: str) -> str:
        """Call the LLM API with a prompt and return the response."""
        # Check if this is Mistral API or Ollama
        if "mistral.ai" in self.api_url:
            url = f"{self.api_url}/chat/completions"
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }
        else:
            # Ollama API format
            url = f"{self.api_url}/api/generate"
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }
        
        try:
            response = self._session.post(url, json=payload, headers=self._headers)
            response.raise_for_status()
            result = response.json()
            
            # Handle different response formats
            if "mistral.ai" in self.api_url:
                # Mistral API format
                return result.get("choices", [{}])[0].get("message", {}).get("content", "")
            else:
                # Ollama API format
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
    
    def qualify(self, qa: dict, index: int = None, total: int = None) -> dict:
        """Qualify a single Q&A pair using LLM.
        
        Args:
            qa: Q&A pair dict with 'instruction' and 'output' keys
            index: Current index in batch (for progress logging)
            total: Total number of Q&A pairs (for progress logging)
            
        Returns:
            Enriched Q&A pair with qualification metadata and weight
        """
        # Log progress
        if index is not None and total is not None:
            instruction_preview = qa.get("instruction", "")[:60].replace("\n", " ")
            print(f"  [{index+1}/{total}] Qualifying: {instruction_preview}...", file=sys.stderr)
        
        prompt = QUALIFICATION_PROMPT.format(
            instruction=qa.get("instruction", ""),
            output=qa.get("output", "")
        )
        
        response = self._call_llm(prompt)
        qualification = self._extract_json(response)
        
        # Get level and compute weight
        level = qualification.get("level", "intermédiaire")
        weight = LEVEL_WEIGHTS.get(level, 1.0)
        
        # Log qualification result
        if index is not None and total is not None:
            useful = "✓" if qualification.get("useful", True) else "✗"
            has_code = "✓" if qualification.get("has_code", False) else "✗"
            print(f"  [{index+1}/{total}] Result: level={level}, weight={weight}, useful={useful}, has_code={has_code}", file=sys.stderr)
        
        # Add qualification metadata and weight to Q&A
        return {
            **qa,
            "niveau": level,
            "level": level,
            "weight": weight,
            "qualification": {
                "useful": qualification.get("useful", True),
                "tags": qualification.get("tags", []),
                "level": level,
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
        total = len(qa_list)
        
        print(f"Starting LLM qualification for {total} Q&A pairs...", file=sys.stderr)
        
        for i in range(0, len(qa_list), batch_size):
            batch = qa_list[i:i + batch_size]
            for j, qa in enumerate(batch):
                try:
                    qualified.append(self.qualify(qa, index=i+j, total=total))
                    # Rate limiting: sleep between requests
                    time.sleep(0.1)  # 100ms delay to avoid overwhelming the API
                except Exception as e:
                    print(f"  Warning: Failed to qualify Q&A: {e}", file=sys.stderr)
                    # Keep the original Q&A without qualification
                    qualified.append(qa)
        
        print(f"Finished LLM qualification: {len(qualified)}/{total} Q&A pairs qualified", file=sys.stderr)
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


def qualify_with_llm(all_qa: list[dict], llm_config: LLMConfig) -> list[dict]:
    """Qualify Q&A pairs using LLM API.
    
    Adds qualification metadata:
    - useful: bool (is the Q&A useful for Laravel experts)
    - tags: list of 3 technical tags
    - niveau/level: "débutant"|"intermédiaire"|"avancé"
    - has_code: bool (contains valid PHP code)
    - weight: float (for weighted loss fine-tuning)
    
    Args:
        all_qa: List of Q&A pairs
        llm_config: LLM configuration
        
    Returns:
        List of qualified Q&A pairs (filtered to useful ones only)
    """
    if not llm_config.enabled:
        return all_qa
    
    try:
        qualifier = LLMQualifier(
            api_url=llm_config.api_url,
            model=llm_config.model,
            api_key=llm_config.api_key,
            timeout=llm_config.timeout
        )
        qualified = []
        
        print("Qualifying Q&A pairs with LLM API...", file=sys.stderr)
        
        for qa in all_qa:
            try:
                qualified_qa = qualifier.qualify(qa)
                # Only keep useful Q&A pairs
                if qualified_qa.get("qualification", {}).get("useful", True):
                    qualified.append(qualified_qa)
            except Exception as e:
                print(f"Warning: Failed to qualify Q&A: {e}", file=sys.stderr)
                # Keep the original Q&A without qualification
                qualified.append(qa)
        
        print(f"Qualified {len(qualified)}/{len(all_qa)} Q&A pairs", file=sys.stderr)
        return qualified
        
    except (ImportError, RuntimeError) as e:
        print(f"Warning: LLM qualification disabled: {e}", file=sys.stderr)
        return all_qa


def load_llm_config(env_vars: dict, cli_args: list[str]) -> LLMConfig:
    """Load LLM configuration from environment variables and CLI args.
    
    Args:
        env_vars: Dictionary of environment variables
        cli_args: List of CLI arguments
        
    Returns:
        LLMConfig instance
    """
    config = LLMConfig()
    
    # Load from environment
    if "LLM_ENABLED" in env_vars:
        config.enabled = env_vars["LLM_ENABLED"].lower() in ("true", "1", "yes")
    
    if "LLM_API_URL" in env_vars:
        config.api_url = env_vars["LLM_API_URL"]
    
    if "LLM_MODEL" in env_vars:
        config.model = env_vars["LLM_MODEL"]
    
    if "LLM_API_KEY" in env_vars:
        config.api_key = env_vars["LLM_API_KEY"]
    
    if "LLM_TIMEOUT" in env_vars:
        try:
            config.timeout = int(env_vars["LLM_TIMEOUT"])
        except ValueError:
            pass
    
    if "LLM_BATCH_SIZE" in env_vars:
        try:
            config.batch_size = int(env_vars["LLM_BATCH_SIZE"])
        except ValueError:
            pass
    
    # CLI override
    if "--llm" in cli_args or "-l" in cli_args:
        config.enabled = True
    
    return config
