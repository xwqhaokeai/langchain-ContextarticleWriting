
import time
import uuid
import asyncio
import json
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException
from langchain_core.messages import HumanMessage

from ...config import get_settings
from ...infrastructure.exceptions import AgentExecutionError
from ...infrastructure.logging import get_logger
from ...schemas import WriteRequest, WriteResponse, TranslateRequest, ImageGenerationRequest
from ...langchain_components.agent_graph import agent_graph
from ...langchain_components.tools import save_article, save_image_with_compression
from ...plugins.translation import translate_text
from ...plugins.image_generation import generate_image

router = APIRouter()
logger = get_logger(__name__)

@router.post("/write", response_model=WriteResponse)
async def create_article(request: WriteRequest, x_trace_id: Optional[str] = Header(None)):
    start_time = time.time()
    article_id = str(uuid.uuid4())
    trace_id = x_trace_id or f"article-{article_id[:8]}"

    prompt_parts = [
        "You are an expert research assistant. Your task is to write a high-quality article based on scientific literature.",
        "Please follow these steps in order:",
        f"1. First, research the topic '{request.topic}' with the keywords '{', '.join(request.keywords) if request.keywords else 'None'}' using the `search_and_summarize` tool.",
        f"2. Second, based on the research, write a {request.style} article in {request.language}.",
        f"3. Third, save the article using the `save_article` tool with filename '{article_id}_main' and output_dir 'output/md'.",
    ]
    if request.translate_to:
        for lang in request.translate_to:
            prompt_parts.append(f"4. Then, translate the article into {lang} and save it using `save_article` with filename '{article_id}_main_{lang}' and output_dir 'output/md'.")
    if request.generate_images:
        prompt_parts.append(f"5. Finally, generate an image for the main topic and save it using `save_image_with_compression` with filename '{article_id}_image' and output_dir 'output/img'.")
    prompt_parts.append(f"{len(prompt_parts)}. **Finish**: After all other steps are complete, call the `finish` tool to provide a final summary of all actions taken, including the paths to all saved files.")
    initial_prompt = "\n".join(prompt_parts)
    
    try:
        inputs = {"messages": [HumanMessage(content=initial_prompt)]}
        final_state, tool_outputs = None, {}
        async for event in agent_graph.astream_events(inputs, version="v1"):
            if event["event"] == "on_tool_end":
                tool_name, tool_output = event["name"], event["data"].get("output")
                tool_outputs.setdefault(tool_name, []).append(tool_output)
            elif event["event"] == "on_graph_end":
                final_state = event["data"]["output"]

        if not final_state:
            raise AgentExecutionError("Agent execution did not produce a valid final state.")

        messages = final_state.get('messages') if isinstance(final_state, dict) else final_state
        if not messages or not isinstance(messages, list) or not messages[-1].content:
            raise AgentExecutionError(
                "Final state did not contain a valid final message.",
                details={"final_state": final_state}
            )
        
        final_summary = messages[-1].content
        file_paths = {}
        for tool_name in ['save_article', 'save_image_with_compression']:
            if tool_name in tool_outputs:
                for output in tool_outputs[tool_name]:
                    if "successfully saved to" in output:
                        path_str = output.split("successfully saved to")[1].strip()
                        file_paths[Path(path_str).name] = path_str
        
        return WriteResponse(
            article_id=article_id, status="completed", content=final_summary,
            metadata={"topic": request.topic}, processing_time=time.time() - start_time,
            trace_id=trace_id, file_paths=file_paths,
        )
    except Exception as e:
        return WriteResponse(
            article_id=article_id, status="failed", error=str(e),
            trace_id=trace_id, processing_time=time.time() - start_time,
        )

@router.post("/write/translate", response_model=WriteResponse)
async def translate_existing_article(request: TranslateRequest):
    start_time = time.time()
    settings = get_settings()
    
    if request.source_file:
        source_path = Path(request.source_file)
    else:
        source_path = Path(settings.app.output_dir) / "md" / f"{request.article_id}_main.md"

    if not source_path.is_file():
        raise HTTPException(status_code=404, detail=f"Source file not found: {source_path}")

    with open(source_path, "r", encoding="utf-8") as f: content = f.read()

    try:
        translated_contents = await asyncio.gather(*[translate_text.ainvoke({"text": content, "target_language": lang}) for lang in request.target_languages])
        file_paths = {}
        for lang, translated_text in zip(request.target_languages, translated_contents):
            filename = f"{source_path.stem}_{lang}"
            save_result = save_article.invoke({"filename": filename, "content": translated_text, "output_dir": "output/trans_exist"})
            if "successfully saved to" in save_result:
                path_str = save_result.split("successfully saved to")[1].strip()
                file_paths[Path(path_str).name] = path_str
        
        return WriteResponse(
            article_id=request.article_id, status="completed",
            processing_time=time.time() - start_time, file_paths=file_paths,
            metadata={"source_file": str(source_path)}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation error: {e}")

@router.post("/write/generate-images", response_model=WriteResponse)
async def images_existing_article(request: ImageGenerationRequest):
    start_time = time.time()
    settings = get_settings()

    if request.source_file:
        source_path = Path(request.source_file)
    else:
        source_path = Path(settings.app.output_dir) / "md" / f"{request.article_id}_main.md"

    if not source_path.is_file():
        raise HTTPException(status_code=404, detail=f"Source file not found: {source_path}")
    
    scene_description = f"A descriptive image for an article titled '{source_path.stem.replace('_', ' ')}'"
    
    try:
        image_results = await asyncio.gather(*[generate_image.ainvoke({"scene_description": scene_description}) for _ in range(request.number_of_images)])
        file_paths = {}
        for result in image_results:
            if isinstance(result, dict) and "file_path" in result:
                path_str = result["file_path"]
                file_paths[Path(path_str).name] = path_str
                logger.info("Successfully generated and saved image", path=path_str)
            elif isinstance(result, dict) and "error" in result:
                logger.error("Image generation tool returned an error", error=result.get("error"), details=result.get("details"))
            else:
                logger.warning("Received an unexpected result from generate_image tool", result=result)

        return WriteResponse(
            article_id=request.article_id, status="completed",
            processing_time=time.time() - start_time, file_paths=file_paths,
            metadata={"source_file": str(source_path)}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image generation error: {e}")