"""
OpenAI client wrapper for AI message generation.
Reads API key from settings and provides a configured client instance.
"""
from openai import OpenAI
from typing import Optional

from src.lib.settings import settings
from src.lib.logging import get_logger

logger = get_logger(__name__)


class OpenAIClient:
    """
    Wrapper around OpenAI client with configuration and error handling.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenAI client.
        
        Args:
            api_key: OpenAI API key (defaults to settings.openai_api_key)
        """
        self.api_key = api_key or settings.openai_api_key
        
        if not self.api_key:
            logger.warning("OpenAI API key not configured. AI features will be unavailable.")
        
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
    
    def is_available(self) -> bool:
        """Check if the OpenAI client is available (API key is set)."""
        return self.client is not None
    
    def get_client(self) -> Optional[OpenAI]:
        """
        Get the underlying OpenAI client instance.
        
        Returns:
            OpenAI client or None if not configured
        """
        return self.client


# Global client instance
openai_client = OpenAIClient()


def get_openai_client() -> OpenAIClient:
    """
    Get the global OpenAI client instance.
    
    Returns:
        Configured OpenAI client wrapper
    """
    return openai_client
