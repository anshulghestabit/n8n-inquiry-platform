import logging

from openai import OpenAI, OpenAIError

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


def get_llm_client() -> OpenAI:
    """
    Both Sarvam and LM Studio are OpenAI-compatible.
    Switch via LLM_PROVIDER env var — no code changes needed.
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
    if settings.llm_provider == "sarvam":
        return settings.sarvam_model
    if settings.llm_provider != "lmstudio":
        raise ValueError(f"Unknown LLM_PROVIDER: {settings.llm_provider}")
    return settings.lm_studio_model


async def chat(system_prompt: str, user_message: str) -> str:
    """
    Single unified chat call used by all 5 agents.
    Sarvam and LM Studio both speak OpenAI protocol.
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
