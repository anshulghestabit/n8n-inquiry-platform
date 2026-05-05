"""OpenAI-compatible LLM client helpers for Sarvam and LM Studio."""

import logging

from openai import OpenAI, OpenAIError

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


def get_llm_client() -> OpenAI:
    """Creates an OpenAI-compatible client for the configured provider.

    Returns:
        OpenAI SDK client pointing at Sarvam or LM Studio.

    Raises:
        RuntimeError: If required provider configuration is missing.
        ValueError: If `LLM_PROVIDER` is unsupported.
    """
    if settings.llm_provider == "sarvam":
        if not settings.sarvam_api_key:
            raise RuntimeError("SARVAM_API_KEY is not configured")
        return OpenAI(
            api_key=settings.sarvam_api_key,
            base_url=settings.sarvam_base_url,
        )
    if settings.llm_provider == "lmstudio":
        return OpenAI(
            api_key="lm-studio",  # ignored by LM Studio but required by SDK
            base_url=settings.lm_studio_base_url,
        )
    raise ValueError(f"Unknown LLM_PROVIDER: {settings.llm_provider}")


def get_model_name() -> str:
    """Returns the model name configured for the active LLM provider.

    Returns:
        Model name sent to the chat completion API.

    Raises:
        ValueError: If `LLM_PROVIDER` is unsupported.
    """
    if settings.llm_provider == "sarvam":
        return settings.sarvam_model
    if settings.llm_provider != "lmstudio":
        raise ValueError(f"Unknown LLM_PROVIDER: {settings.llm_provider}")
    return settings.lm_studio_model


async def chat(system_prompt: str, user_message: str) -> str:
    """Runs one chat completion against the configured LLM provider.

    Args:
        system_prompt: System prompt defining the agent role.
        user_message: User or workflow message to process.

    Returns:
        Text content from the first completion choice.

    Raises:
        RuntimeError: If the request, configuration, or response is invalid.
    """
    try:
        client = get_llm_client()
        model = get_model_name()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            max_tokens=1000,
        )
    except OpenAIError:
        logger.exception("LLM chat completion failed")
        raise RuntimeError("LLM request failed")
    except (RuntimeError, ValueError):
        logger.exception("LLM configuration failed")
        raise RuntimeError("LLM configuration failed")

    if not response.choices:
        raise RuntimeError("LLM response did not include choices")

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("LLM response did not include content")
    return content
