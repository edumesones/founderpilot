"""LLM provider abstraction and routing."""

from typing import Literal

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from src.core.config import settings


class LLMRouter:
    """Routes LLM calls to appropriate providers based on task type.

    Task types and their default providers:
    - classify: GPT-4o-mini (fast, cheap)
    - generate: Claude 3.5 Sonnet (quality)
    - analyze: Claude 3 Opus (complex reasoning)
    """

    TASK_ROUTING = {
        "classify": ("gpt-4o-mini", "claude-3-haiku-20240307"),
        "generate": ("claude-3-5-sonnet-20241022", "gpt-4o"),
        "analyze": ("claude-3-opus-20240229", "gpt-4o"),
    }

    def __init__(
        self,
        openai_api_key: str | None = None,
        anthropic_api_key: str | None = None,
    ):
        """Initialize the LLM router.

        Args:
            openai_api_key: OpenAI API key (defaults to settings)
            anthropic_api_key: Anthropic API key (defaults to settings)
        """
        self.openai_key = openai_api_key or settings.openai_api_key
        self.anthropic_key = anthropic_api_key or settings.anthropic_api_key

        self._clients: dict = {}

    def _get_client(self, model: str):
        """Get or create a client for the given model."""
        if model in self._clients:
            return self._clients[model]

        if model.startswith("gpt-") or model.startswith("o1"):
            client = ChatOpenAI(
                model=model,
                api_key=self.openai_key,
                temperature=0.1,
            )
        elif model.startswith("claude-"):
            client = ChatAnthropic(
                model=model,
                api_key=self.anthropic_key,
                temperature=0.1,
            )
        else:
            raise ValueError(f"Unknown model: {model}")

        self._clients[model] = client
        return client

    async def call(
        self,
        task_type: Literal["classify", "generate", "analyze"],
        system_prompt: str,
        user_prompt: str,
        model_override: str | None = None,
    ) -> str:
        """Call the appropriate LLM for the task.

        Args:
            task_type: Type of task (determines which model to use)
            system_prompt: System message for the LLM
            user_prompt: User message/query
            model_override: Optional specific model to use

        Returns:
            LLM response text

        Raises:
            Exception: If both primary and fallback providers fail
        """
        if model_override:
            models = [model_override]
        else:
            models = list(self.TASK_ROUTING.get(task_type, ("gpt-4o-mini",)))

        last_error = None

        for model in models:
            try:
                client = self._get_client(model)

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]

                response = await client.ainvoke(messages)
                return response.content

            except Exception as e:
                last_error = e
                # Try next model in fallback chain
                continue

        # All models failed
        raise Exception(f"All LLM providers failed. Last error: {last_error}")
