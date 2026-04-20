"""
LLM Client Module for interacting with Ollama service.

This module provides a low-level interface to send formatted prompts to the Ollama
LLM service and receive raw generated code as a response.
"""

import httpx
from typing import Optional


class OllamaClient:
    """
    A client for communicating with the Ollama LLM service.
    
    Handles:
    - Connection management to the Ollama API
    - Sending prompts and receiving generated code
    - Error handling and timeout management
    - Model selection and configuration
    """
    
    def __init__(self, base_url: str, model: str = "tinyllama", timeout: float = 60.0):
        """
        Initialize the Ollama client.
        
        Args:
            base_url (str): The base URL of the Ollama service (e.g., "http://ollama:11434")
            model (str): The LLM model to use (default: "tinyllama")
            timeout (float): Request timeout in seconds (default: 60.0)
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout
        self.client = httpx.AsyncClient()
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Send a formatted prompt to the Ollama service and get generated code.
        
        Args:
            prompt (str): The formatted prompt to send to the LLM
            temperature (float): Sampling temperature (0.0-1.0). Lower = more deterministic.
                                 (default: 0.7)
            max_tokens (Optional[int]): Maximum tokens to generate. None for model default.
        
        Returns:
            str: The raw generated code from the LLM
        
        Raises:
            httpx.HTTPError: If the request to Ollama fails
            ValueError: If the response format is unexpected
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "temperature": temperature,
        }
        
        # Add max_tokens if specified
        if max_tokens is not None:
            payload["num_predict"] = max_tokens
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Extract the generated text from the response
            response_data = response.json()
            generated_code = response_data.get("response", "")
            
            if not generated_code:
                raise ValueError("LLM returned empty response")
            
            return generated_code
            
        except httpx.TimeoutException:
            raise TimeoutError(
                f"Ollama service did not respond within {self.timeout} seconds. "
                f"The model may be processing a complex prompt."
            )
        except httpx.ConnectError:
            raise ConnectionError(
                f"Could not connect to Ollama service at {self.base_url}. "
                f"Ensure the service is running and accessible."
            )
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"Ollama returned error {e.response.status_code}: {e.response.text}"
            )
    
    async def health_check(self) -> bool:
        """
        Check if the Ollama service is healthy and the model is available.
        
        Returns:
            bool: True if service is healthy, False otherwise
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/tags",
                timeout=5.0
            )
            
            if response.status_code != 200:
                return False
            
            # Check if our model is in the available models
            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            
            # Check if our model or a variant is available
            return any(self.model in name for name in model_names)
            
        except Exception:
            return False
    
    async def close(self):
        """Close the HTTP client connection."""
        await self.client.aclose()
    
    def __del__(self):
        """Ensure client is closed on garbage collection."""
        try:
            # Note: This is a fallback; proper cleanup should use async context manager
            if hasattr(self, 'client') and self.client:
                # Can't await in __del__, so we just note it
                pass
        except Exception:
            pass
