import asyncio
import re
import json
from typing import Any, Dict
import base64
import json
import aiohttp
import uuid
from pathlib import Path

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from ..config import get_settings
from ..infrastructure.logging import get_logger

logger = get_logger(__name__)


class GeminiImageGenerator:
    """Wrapper for Gemini image generation model using direct HTTP requests."""

    def __init__(self, api_key: str, model: str, base_url: str | None):
        self.api_key = api_key
        self.model = model
        if not base_url:
            raise ValueError("base_url must be configured for GeminiImageGenerator")
        # Note: The actual endpoint might vary based on the provider (e.g., Google AI Studio vs. Vertex AI)
        self.endpoint_url = f"{base_url.rstrip('/')}/models/{self.model}:generateContent"
        logger.debug(f"GeminiImageGenerator initialized for endpoint: {self.endpoint_url}")

    async def draw(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """Generates an image by calling the Gemini generateContent API directly."""
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"]  # Crucial parameter based on user's working example
            }
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        logger.debug("Calling Gemini generateContent API", url=self.endpoint_url, payload=payload)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.endpoint_url, json=payload, headers=headers) as response:
                    response.raise_for_status()
                    response_text = await response.text()
                    logger.debug("Received raw response from Gemini API", status=response.status, content=response_text)

                    # Use regex to find base64 data in the raw text response. This is the most robust method.
                    # A valid base64 string for an image will be very long.
                    base64_pattern = re.compile(r'([A-Za-z0-9+/]{200,}=*)')
                    match = base64_pattern.search(response_text)
                    
                    if match:
                        base64_data = match.group(1)
                        logger.debug(f"Successfully extracted base64 data using regex, length: {len(base64_data)}")
                        return {"base64_data": base64_data}

                    # If regex fails, try to parse JSON for a more detailed error message
                    try:
                        data = json.loads(response_text)
                        logger.error("Failed to find image data using regex.", response_content=data)
                        return {"error": "No image data found in response", "details": data}
                    except json.JSONDecodeError:
                        logger.error("Failed to find image data and response is not valid JSON.", response_content=response_text)
                        return {"error": "No image data found in response and response is not valid JSON", "details": response_text}

        except Exception as e:
            logger.error("Error calling image generation API", error=str(e))
            details = str(e)
            if 'response_json' in locals():
                details = response_json
            return {"error": "Exception during API call", "details": details}


settings = get_settings()
image_generator_instance = GeminiImageGenerator(
    api_key=settings.openai_api_key,
    model="gemini-2.5-flash-image-preview",  # A model that explicitly supports vision/image tasks
    base_url=settings.openai_api_base,
)

@tool
async def generate_image(scene_description: str) -> dict:
    """
    Generates an image based on a descriptive theme, saves it to a file,
    and returns the file path for downstream processing.
    """
    logger.info("Starting image generation", scene_description=scene_description)

    prompt_enhancer_llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=settings.temperature,
        api_key=settings.openai_api_key,
        base_url=settings.openai_api_base,
    )
    prompt_template = (
        'You are an expert prompt engineer for an AI image generation model. '
        'Your task is to take a simple description and transform it into a detailed, artistic, and effective prompt in English. '
        'The output MUST be ONLY the prompt text itself, without any surrounding text, explanations, or conversational phrases. '
        'Do not offer choices or ask questions. '
        f'Based on the following description, generate a single, direct image prompt:\n\n"{scene_description}"'
    )

    try:
        logger.info("Generating enhanced image prompt with LLM...")
        response = await prompt_enhancer_llm.ainvoke(prompt_template)
        image_prompt = response.content.strip()
        logger.info("Enhanced image prompt generated", image_prompt=image_prompt)

        if not image_prompt or not isinstance(image_prompt, str):
            logger.error("LLM failed to generate a valid image prompt.", original_description=scene_description)
            return {"error": "LLM failed to generate a valid image prompt.", "details": f"Received: {image_prompt}"}

        final_prompt = image_prompt
        logger.info("Using pure enhanced English prompt for image generation", final_prompt=final_prompt)

        api_response = await image_generator_instance.draw(prompt=final_prompt)
        logger.info("Image generation API response received", response=api_response)

        if "error" in api_response:
            logger.error("Image generation failed, passing error upstream.", details=api_response)
            return api_response

        # Decode the Base64 string and save it to a file.
        encoded_data = api_response.get('base64_data')
        if not encoded_data:
            logger.error("No 'base64_data' found in API response", response=api_response)
            return {"error": "No image data found in API response"}

        # Robustly decode Base64, handling potential padding issues.
        def robust_b64decode(data_str: str) -> bytes:
            padding = '=' * (4 - len(data_str) % 4)
            return base64.b64decode(data_str + padding)

        try:
            image_data = robust_b64decode(encoded_data)
        except (ValueError, TypeError, base64.binascii.Error) as e:
            logger.error("Failed to decode Base64 string", error=str(e), data_prefix=encoded_data[:50])
            return {"error": "Failed to decode Base64 string", "details": str(e)}

        save_dir = Path("output/img_exist")
        save_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = save_dir / f"{uuid.uuid4()}.png"
        with open(file_path, "wb") as f:
            f.write(image_data)
        
        logger.info(f"Image data saved to file: {file_path}")

        return {
            "message": "Image generation successful! Image saved to file.",
            "file_path": str(file_path)
        }

    except Exception as e:
        logger.error("An error occurred during image generation", error=str(e))
        return {"error": "An error occurred during image generation", "details": str(e)}