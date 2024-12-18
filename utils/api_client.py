"""OpenAI API client and related utilities."""

import time
from typing import Optional
from openai import OpenAI
import os

from config.constants import MAX_RETRIES, RETRY_DELAY

class APIClient:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def check_api_key(self) -> bool:
        """Verify OpenAI API key."""
        try:
            self.client.models.list()
            return True
        except Exception:
            return False

    def get_response(
        self, 
        prompt: str, 
        model: str = "gpt-4-turbo-preview",
        temperature: float = 0.7,
        retries: int = MAX_RETRIES,
        delay: int = RETRY_DELAY
    ) -> Optional[str]:
        """Get response from OpenAI API with retry mechanism."""
        attempt = 0
        while attempt < retries:
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=500,
                    temperature=temperature
                )
                return response.choices[0].message.content
            except Exception as e:
                attempt += 1
                if attempt < retries:
                    time.sleep(delay)
                else:
                    raise e
        return None

# Global API client instance
api_client = APIClient()

def get_gpt_response(prompt: str, **kwargs) -> str:
    """Convenience function for getting GPT responses."""
    response = api_client.get_response(prompt, **kwargs)
    if response is None:
        raise Exception("Failed to get response from API")
    return response