"""
LLM Provider Interface and Implementations
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import json
import structlog
from openai import AsyncOpenAI

logger = structlog.get_logger()

class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    async def chat_completion(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        response_format: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 500
    ) -> str:
        """Generate a chat completion"""
        pass

    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate a vector embedding for text"""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI implementation of LLM provider"""
    
    def __init__(self, api_key: str, model: str, embedding_model: str):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.embedding_model = embedding_model
        self.logger = logger.bind(provider="openai")

    async def chat_completion(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        response_format: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 500
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        extra_params = {}
        if response_format == "json":
            extra_params["response_format"] = {"type": "json_object"}
            
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **extra_params
        )
        return response.choices[0].message.content

    async def generate_embedding(self, text: str) -> List[float]:
        response = await self.client.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        return response.data[0].embedding


class GeminiProvider(LLMProvider):
    """Google Gemini implementation of LLM provider"""
    
    def __init__(self, api_key: str, model: str, embedding_model: str):
        from google import genai
        # Initialize the new SDK client
        self.client = genai.Client(api_key=api_key)
        self.model_name = model
        self.embedding_model_name = embedding_model
        self.logger = logger.bind(provider="gemini")

    async def chat_completion(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        response_format: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 500
    ) -> str:
        from google.genai import types
        
        # Combine system prompt if provided
        contents = prompt
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_prompt if system_prompt else None
        )
        
        if response_format == "json":
            config.response_mime_type = "application/json"
            
        response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=config
        )
        return response.text

    async def generate_embedding(self, text: str) -> List[float]:
        result = await self.client.aio.models.embed_content(
            model=self.embedding_model_name,
            contents=text,
            config={'task_type': 'RETRIEVAL_DOCUMENT'}
        )
        # Handle single vs batch result structure in new SDK
        return result.embeddings[0].values if hasattr(result.embeddings[0], 'values') else result.embeddings[0]


def get_llm_provider(settings) -> Optional[LLMProvider]:
    """Factory to get the configured LLM provider"""
    provider_type = getattr(settings, "llm_provider", "openai").lower()
    
    if provider_type == "openai" and settings.openai_api_key:
        return OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.llm_model,
            embedding_model=settings.embedding_model
        )
    elif provider_type == "gemini" and settings.gemini_api_key:
        return GeminiProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            embedding_model=settings.gemini_embedding_model
        )
    
    return None
