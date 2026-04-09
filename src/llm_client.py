"""
LLM Client wrapper supporting multiple backends.
Supports: Anthropic Claude API, Ollama (local), and OpenAI (if needed).
"""

import os
import json
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod


class LLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    def generate(self, system_prompt: str, user_message: str, temperature: float = 0.7) -> str:
        """Generate a response from the LLM."""
        pass


class AnthropicClient(LLMClient):
    """Anthropic Claude API client."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")
        
        self.model = model
        
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError(
                "anthropic package not installed. Install it with: pip install anthropic"
            )
    
    def generate(self, system_prompt: str, user_message: str, temperature: float = 0.7) -> str:
        """Generate a response using Claude."""
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=8000,
                temperature=temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )
            return message.content[0].text
        except Exception as e:
            raise RuntimeError(f"Error calling Anthropic API: {str(e)}")


class OllamaClient(LLMClient):
    """Ollama local LLM client."""
    
    def __init__(self, model: str = "llama3.1", base_url: str = None):
        base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = model
        self.base_url = base_url
        
        try:
            import requests
            self.requests = requests
        except ImportError:
            raise ImportError(
                "requests package not installed. Install it with: pip install requests"
            )
    
    def generate(self, system_prompt: str, user_message: str, temperature: float = 0.7) -> str:
        """Generate a response using Ollama."""
        try:
            response = self.requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": f"System: {system_prompt}\n\nUser: {user_message}",
                    "stream": False,
                    "options": {
                        "temperature": temperature
                    }
                }
            )
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            raise RuntimeError(f"Error calling Ollama API: {str(e)}")


class OpenAIClient(LLMClient):
    """OpenAI API client."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
        
        self.model = model
        
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError(
                "openai package not installed. Install it with: pip install openai"
            )
    
    def generate(self, system_prompt: str, user_message: str, temperature: float = 0.7) -> str:
        """Generate a response using OpenAI."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"Error calling OpenAI API: {str(e)}")


def create_llm_client(
    backend: str = "anthropic",
    model: Optional[str] = None,
    **kwargs
) -> LLMClient:
    """
    Factory function to create an LLM client.
    
    Args:
        backend: Which LLM backend to use ('anthropic', 'ollama', 'openai')
        model: Specific model to use (optional, uses defaults if not provided)
        **kwargs: Additional arguments passed to the client constructor
    
    Returns:
        LLMClient instance
    
    Examples:
        # Use Anthropic Claude (same models as Windsurf)
        client = create_llm_client("anthropic")
        
        # Use local Ollama
        client = create_llm_client("ollama", model="llama3.1")
        
        # Use OpenAI
        client = create_llm_client("openai", model="gpt-4")
    """
    backend = backend.lower()
    
    if backend == "anthropic":
        return AnthropicClient(model=model or "claude-3-5-sonnet-20241022", **kwargs)
    elif backend == "ollama":
        return OllamaClient(model=model or "llama3.1", **kwargs)
    elif backend == "openai":
        return OpenAIClient(model=model or "gpt-4", **kwargs)
    else:
        raise ValueError(
            f"Unknown backend: {backend}. Choose from: 'anthropic', 'ollama', 'openai'"
        )


def get_backend_from_env() -> str:
    """Determine which backend to use based on environment variables."""
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    elif os.getenv("OPENAI_API_KEY"):
        return "openai"
    else:
        # Default to Ollama (local) if no API keys found
        return "ollama"
