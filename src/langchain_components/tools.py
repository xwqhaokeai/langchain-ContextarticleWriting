import asyncio
import datetime
import hashlib
import hmac
import json
import os
import io
from typing import Any, Dict, List, Optional
from urllib.parse import quote
from pathlib import Path

import requests
import aiohttp
from PIL import Image
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from .document_loader import PubMedLoader, PMCLoader
from ..config import get_settings

# --- LangChain 工具 ---

@tool
async def search_and_summarize(topic: str, keywords: Optional[List[str]] = None, max_results_per_source: int = 3) -> str:
    """
    Searches for a topic on PubMed and PMC, then generates a concise summary of the findings.
    """
    search_query = f"{topic} AND {' AND '.join(keywords)}" if keywords else topic
    print(f"Searching for '{search_query}' on PubMed and PMC...")

    try:
        # 并行执行搜索
        pubmed_loader = PubMedLoader(query=search_query, max_results=max_results_per_source)
        pmc_loader = PMCLoader(query=search_query, max_results=max_results_per_source)
        
        pubmed_docs, pmc_docs = await asyncio.gather(
            pubmed_loader.aload(),
            pmc_loader.aload()
        )
        
        all_docs = pubmed_docs + pmc_docs
        if not all_docs:
            return "No relevant articles found from any source."

        # 构建上下文
        context = "Found articles:\n"
        for i, doc in enumerate(all_docs):
            source_type = "PubMed" if "pubmed.ncbi.nlm.nih.gov" in doc.metadata.get("source", "") else "PMC"
            title = doc.metadata.get('title', 'N/A')
            content_preview = (doc.page_content[:400] + '...') if len(doc.page_content) > 400 else doc.page_content
            context += f"--- Doc {i+1} ({source_type}) ---\n"
            context += f"Title: {title}\n"
            context += f"Source: {doc.metadata.get('source', 'N/A')}\n"
            context += f"Content: {content_preview}\n\n"

        # 使用 LLM 进行总结
        settings = get_settings()
        llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.2,  # Summarization should be mostly deterministic
            openai_api_key=settings.openai_api_key,
            openai_api_base=settings.openai_api_base,
        )
        summarization_prompt = f"Based on the following articles, provide a concise summary for the topic '{topic}'.\n\n{context}"
        
        response = await llm.ainvoke(summarization_prompt)
        summary = response.content.strip()
        
        return f"Summary of Findings:\n{summary}\n\nSources:\n{context}"

    except Exception as e:
        return f"An error occurred during research: {e}"

@tool
def save_article(filename: str, content: str, output_dir: str = "output/md") -> str:
    """Saves text content into a Markdown file in a specified directory."""
    try:
        save_dir = Path(output_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        file_path = save_dir / f"{filename}.md"
        with open(file_path, "w", encoding="utf-8") as f: f.write(content)
        return f"Article successfully saved to {file_path}"
    except Exception as e: return f"Error saving article: {e}"

@tool
async def save_image_with_compression(image_input: str | dict, filename: str, output_dir: str = "output/img") -> str:
    """
    Processes an image, compresses it, converts to PNG, and saves it.
    The input can be a direct URL string, a dictionary containing an 'image_url',
    or a dictionary from the generate_image tool containing a 'temp_file_path'.
    """
    MAX_SIZE_BYTES = 500 * 1024
    image_data = None

    if isinstance(image_input, dict) and "temp_file_path" in image_input:
        # New logic: Handle the "receipt" from generate_image
        temp_path = Path(image_input["temp_file_path"])
        if temp_path.is_file():
            with open(temp_path, "rb") as f:
                image_data = f.read()
            # Clean up the temporary file
            temp_path.unlink()
        else:
            return f"Error: Temporary image file not found at {temp_path}"
    elif isinstance(image_input, dict) and "image_url" in image_input:
        # Existing logic for URL in dict
        url_to_fetch = image_input["image_url"]
        async with aiohttp.ClientSession() as session:
            async with session.get(url_to_fetch) as response:
                response.raise_for_status()
                image_data = await response.read()
    elif isinstance(image_input, str) and image_input.startswith('http'):
        # Existing logic for direct URL string
        url_to_fetch = image_input
        async with aiohttp.ClientSession() as session:
            async with session.get(url_to_fetch) as response:
                response.raise_for_status()
                image_data = await response.read()

    if not image_data:
        return "Error: Invalid input. Could not find or download valid image data."

    try:
        save_dir = Path(output_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        file_path = save_dir / f"{filename}.png"
        
        img = Image.open(io.BytesIO(image_data))
        
        # Compression logic migrated from old project
        try:
            img = img.quantize(colors=256, method=Image.Quantize.LIBIMAGEQUANT, dither=Image.Dither.FLOYDSTEINBERG)
        except Exception:
            img = img.convert('P', palette=Image.ADAPTIVE, colors=256)
        
        output_buffer = io.BytesIO()
        img.save(output_buffer, format="PNG", optimize=True)
        
        while output_buffer.tell() > MAX_SIZE_BYTES:
            img_to_resize = Image.open(output_buffer)
            w, h = img_to_resize.size
            if w // 2 < 1 or h // 2 < 1: break
            resized_img = img_to_resize.resize((w // 2, h // 2), Image.Resampling.LANCZOS)
            output_buffer = io.BytesIO()
            resized_img.save(output_buffer, format="PNG", optimize=True)

        with open(file_path, "wb") as f: f.write(output_buffer.getvalue())
        return f"Image successfully saved to {file_path}"
    except Exception as e: return f"Error saving image: {e}"

@tool
def finish(final_summary: str) -> str:
    """
    Call this tool to signify that all tasks are complete and to provide a final summary.
    """
    return final_summary
