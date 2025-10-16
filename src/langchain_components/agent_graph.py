from typing import Sequence
import operator

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from ..config import get_settings
from .tools import search_and_summarize, save_article, read_article, save_image_with_compression, finish
from ..plugins.image_generation import generate_image
from ..plugins.translation import translate_text
from ..infrastructure.logging import get_logger
from .agent_state import AgentState

logger = get_logger(__name__)

tools = [generate_image, translate_text, search_and_summarize, save_article, read_article, save_image_with_compression, finish]
tool_node = ToolNode(tools)

settings = get_settings()
model = ChatOpenAI(
    temperature=settings.temperature,
    streaming=True,
    model_name=settings.openai_model,
    api_key=settings.openai_api_key,
    base_url=settings.openai_api_base,
).bind_tools(tools)

def should_continue(state: AgentState) -> str:
    logger.info("Checking condition: should_continue")
    last_message = state['messages'][-1]
    if not last_message.tool_calls:
        logger.warning("No tool calls found in the last message. Ending graph.")
        return "end"
    
    return "call_tool"

def call_model(state: AgentState):
    logger.info("--- Calling Model ---")
    messages = state['messages']
    logger.debug("Messages sent to model:", messages=messages)
    
    try:
        response = model.invoke(messages)
    except Exception as e:
        logger.error(f"Error calling model: {e}")
        # Create a message to inform the user of the error
        error_message = HumanMessage(content=f"An error occurred while calling the model: {e}")
        return {"messages": [error_message]}
    
    logger.info("Model response received.")
    logger.debug("Model response content:", content=response.content)
    if response.tool_calls:
        logger.debug("Model requested tool calls:", tool_calls=response.tool_calls)
    
    return {"messages": [response]}

def call_tool_with_logging(state: AgentState):
    logger.info("--- Calling Tool ---")
    last_message = state["messages"][-1]
    logger.debug("Tools to be called:", tool_calls=last_message.tool_calls)
    
    response = tool_node.invoke(state)
    
    logger.info("Tool execution finished.")
    logger.debug("Tool response:", response=response)
    
    return response

workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)
workflow.add_node("action", call_tool_with_logging)

workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "call_tool": "action",
        "end": END,
    },
)

def after_tool_call(state: AgentState) -> str:
    logger.info("Checking condition: after_tool_call")
    last_message = state['messages'][-1]
    # The last message is a ToolMessage, which doesn't have tool_calls.
    # We need to look at the message before it, which is the AI message with the tool call.
    ai_message_with_tool_call = state['messages'][-2]
    tool_name = ai_message_with_tool_call.tool_calls[0]['name']
    
    logger.info(f"Tool called was: {tool_name}")
    if tool_name == "finish":
        logger.info("Finish tool was called. Ending graph.")
        return "end"
    
    logger.info("Continuing with agent.")
    return "continue"

workflow.add_conditional_edges(
    "action",
    after_tool_call,
    {
        "continue": "agent",
        "end": END,
    },
)

agent_graph = workflow.compile()
