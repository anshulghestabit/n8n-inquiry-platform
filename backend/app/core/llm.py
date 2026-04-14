from openai import OpenAI
from app.core.config import get_settings

settings = get_settings()

def get_llm_client() -> OpenAI:
    """
    Both Sarvam and LM Studio are OpenAI-compatible.
    Switch via LLM_PROVIDER env var — no code changes needed.
    """
    if settings.llm_provider == "sarvam":
        return OpenAI(
            api_key=settings.sarvam_api_key,
            base_url=settings.sarvam_base_url
        )
    elif settings.llm_provider == "lmstudio":
        return OpenAI(
            api_key="lm-studio",  # ignored by LM Studio but required by SDK
            base_url=settings.lm_studio_base_url
        )
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {settings.llm_provider}")

def get_model_name() -> str:
    if settings.llm_provider == "sarvam":
        return settings.sarvam_model
    return settings.lm_studio_model

async def chat(system_prompt: str, user_message: str) -> str:
    """
    Single unified chat call used by all 5 agents.
    Sarvam and LM Studio both speak OpenAI protocol.
    """
    client = get_llm_client()
    model = get_model_name()

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        temperature=0.3,
        max_tokens=1000
    )
    return response.choices[0].message.content