import asyncio
import datetime
import hashlib
import hmac
import json
import os
from typing import Any, Dict
from urllib.parse import quote

import requests
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from ..config import get_settings
from ..infrastructure.logging import get_logger

logger = get_logger(__name__)

class JimengDrawer:
    def __init__(self, ak: str, sk: str):
        self.ak, self.sk = ak, sk
        self.host, self.region, self.service = 'visual.volcengineapi.com', 'cn-south-1', 'cv'
        self.endpoint, self.req_key = 'https://visual.volcengineapi.com', 'jimeng_high_aes_general_v21_L'
    def _sign(self, key, msg): return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()
    def _get_signature_key(self, key, dateStamp, regionName, serviceName):
        kDate = self._sign(key.encode('utf-8'), dateStamp)
        kRegion = self._sign(kDate, regionName)
        kService = self._sign(kRegion, serviceName)
        return self._sign(kService, 'request')
    def _format_query(self, p): return '&'.join([f"{k}={quote(str(p[k]))}" for k in sorted(p)])
    def _sign_v4_request(self, req_query, req_body):
        t = datetime.datetime.utcnow()
        current_date, datestamp = t.strftime('%Y%m%dT%H%M%SZ'), t.strftime('%Y%m%d')
        payload_hash = hashlib.sha256(req_body.encode('utf-8')).hexdigest()
        canonical_request = f"POST\n/\n{req_query}\ncontent-type:application/json\nhost:{self.host}\nx-content-sha256:{payload_hash}\nx-date:{current_date}\n\ncontent-type;host;x-content-sha256;x-date\n{payload_hash}"
        credential_scope = f"{datestamp}/{self.region}/{self.service}/request"
        string_to_sign = f"HMAC-SHA256\n{current_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        signing_key = self._get_signature_key(self.sk, datestamp, self.region, self.service)
        signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        auth_header = f"HMAC-SHA256 Credential={self.ak}/{credential_scope}, SignedHeaders=content-type;host;x-content-sha256;x-date, Signature={signature}"
        return {'X-Date': current_date, 'Authorization': auth_header, 'X-Content-Sha256': payload_hash, 'Content-Type': 'application/json'}
    def draw(self, prompt: str, **kwargs):
        query = self._format_query({'Action': 'CVProcess', 'Version': '2022-08-31'})
        body = {"req_key": self.req_key, "prompt": prompt, **kwargs}
        headers = self._sign_v4_request(query, json.dumps(body, ensure_ascii=False))
        resp = requests.post(f'{self.endpoint}?{query}', headers=headers, data=json.dumps(body, ensure_ascii=False))
        resp.raise_for_status()
        return resp.json()

settings = get_settings()
drawer_instance = JimengDrawer(settings.JIMENG_AK, settings.JIMENG_SK) if settings.JIMENG_AK and settings.JIMENG_SK else None

@tool
async def generate_image(scene_description: str) -> str:
    """Generates an image based on a descriptive theme or scene."""
    logger.info("Starting image generation", scene_description=scene_description)
    if not drawer_instance:
        logger.error("Image generation service not configured.")
        return "Error: Image generation service not configured."
    
    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=settings.temperature,
        api_key=settings.openai_api_key,
        base_url=settings.openai_api_base,
    )
    prompt_template = f'Create a detailed, artistic prompt in English for an AI image model, based on: "{scene_description}"'
    try:
        logger.info("Generating image prompt with LLM...")
        response = await llm.ainvoke(prompt_template)
        image_prompt = response.content.strip()
        logger.info("Image prompt generated", image_prompt=image_prompt)
        
        logger.info("Calling image generation API...")
        api_response = await asyncio.to_thread(drawer_instance.draw, prompt=image_prompt, width=600, height=600, seed=-1, return_url=True)
        
        if api_response and api_response.get('code') == 10000 and api_response.get('data', {}).get('image_urls'):
            url = api_response['data']['image_urls'][0]
            logger.info("Image generation successful", url=url)
            return f"Image generation successful! URL: {url}"
        
        logger.error("Image API returned an issue", response=api_response)
        return f"Error: Image API returned an issue. Response: {json.dumps(api_response)}"
    except Exception as e:
        logger.error("Error during image generation", error=str(e))
        return f"Error during image generation: {e}"