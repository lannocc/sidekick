# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from . import google, openai

class AIClient:
    """
    A unified client that abstracts the provider-specific AI implementation.
    This class forwards calls to the appropriate provider module (Google or OpenAI)
    based on the initialization parameter.
    """
    def __init__(self, use_openai=False):
        """
        Initializes the AI client.

        Args:
            use_openai (bool): If True, uses the OpenAI provider. Otherwise, uses the Google provider.
        """
        self.provider = openai if use_openai else google

    def prompt_for_text(self, *args, **kwargs):
        """Wraps the provider's prompt_for_text function."""
        return self.provider.prompt_for_text(*args, **kwargs)

    def prompt_for_json(self, *args, **kwargs):
        """Wraps the provider's prompt_for_json function."""
        return self.provider.prompt_for_json(*args, **kwargs)

    def prompt_with_file_for_text(self, *args, **kwargs):
        """Wraps the provider's prompt_with_file_for_text function."""
        return self.provider.prompt_with_file_for_text(*args, **kwargs)

    def prompt_with_file_for_json(self, *args, **kwargs):
        """Wraps the provider's prompt_with_file_for_json function."""
        return self.provider.prompt_with_file_for_json(*args, **kwargs)

    async def async_prompt_for_text(self, *args, **kwargs):
        """Wraps the provider's async_prompt_for_text function."""
        return await self.provider.async_prompt_for_text(*args, **kwargs)

