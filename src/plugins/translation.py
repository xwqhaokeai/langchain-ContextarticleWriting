from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from ..config import get_settings
from ..infrastructure.logging import get_logger

logger = get_logger(__name__)

@tool
async def translate_text(text: str, target_language: str) -> str:
    """Translates a given text into a specified target language."""
    logger.info("Starting translation", text_length=len(text), target_language=target_language)
    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=0,  # Translation should be deterministic
        api_key=settings.openai_api_key,
        base_url=settings.openai_api_base,
    )
    prompt = f"Translate the following text into {target_language}. Provide only the raw translated text.\n\nText: {text}"
    try:
        response = await llm.ainvoke(prompt)
        logger.info("Translation successful")
        return response.content.strip()
    except Exception as e:
        logger.error("Error during translation", error=str(e))
        return f"Error during translation: {e}"