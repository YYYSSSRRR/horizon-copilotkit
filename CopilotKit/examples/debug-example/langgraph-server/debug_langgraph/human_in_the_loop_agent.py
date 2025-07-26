"""
直接复用 demo-viewer 的 human_in_the_loop agent，但简化为通用任务场景
"""

import json
import logging
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# LangGraph imports
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END, START
from langgraph.types import Command, interrupt
from langgraph.checkpoint.memory import MemorySaver

# CopilotKit imports
from copilotkit import CopilotKitState
from copilotkit.langgraph import copilotkit_customize_config, copilotkit_emit_state, copilotkit_exit

# LLM imports
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage

# Configure DeepSeek model with OpenAI-compatible API
def create_deepseek_model():
    return ChatOpenAI(
        model="deepseek-chat",
        openai_api_base="https://api.deepseek.com/v1",
        openai_api_key="sk-43fc565dd627428db42a1325b24886bd"  # Replace with your actual DeepSeek API key
    )

GENERATE_TASK_STEPS_TOOL = {
    "type": "function",
    "function": {
        "name": "generate_task_steps",
        "description": "Generate 5-10 steps for completing a task. Steps should be specific and actionable.",
        "parameters": {
            "type": "object",
            "properties": {
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "The step description in imperative form (e.g., 'Check logs', 'Run tests')"
                            },
                            "status": {
                                "type": "string",
                                "enum": ["enabled"],
                                "description": "The status of the step, always 'enabled'"
                            }
                        },
                        "required": ["description", "status"]
                    },
                    "description": "An array of 5-10 step objects"
                }
            },
            "required": ["steps"]
        }
    }
}

class AgentState(CopilotKitState):
    """
    Agent state for human-in-the-loop task planning.
    """
    steps: List[Dict[str, str]] = []

async def start_flow(state: Dict[str, Any], config: RunnableConfig):
    """
    Entry point for the flow.
    """
    logger.info("🚀 Start flow called with state keys: %s", list(state.keys()))
    if "steps" not in state:
        state["steps"] = []
    
    return Command(
        goto="chat_node",
        update={
            "messages": state["messages"],
            "steps": state["steps"],
        }
    )

async def chat_node(state: Dict[str, Any], config: RunnableConfig):
    """
    Chat node that can generate task steps for user confirmation.
    """
    logger.info("💬 Chat node called with %d messages", len(state.get("messages", [])))
    
    system_prompt = """
    You are a helpful assistant that can break down tasks into actionable steps.
    When the user asks for help with a task, you MUST call the `generate_task_steps` function 
    to create a list of steps they can review and modify.
    Always generate practical, specific steps that the user can actually follow.
    """

    # Configure model
    model = create_deepseek_model()
    
    if config is None:
        config = RunnableConfig(recursion_limit=25)
    
    # Configure CopilotKit for emitting state
    config = copilotkit_customize_config(
        config,
        emit_intermediate_state=[{
            "state_key": "steps", 
            "tool": "generate_task_steps",
            "tool_argument": "steps"
        }],
    )

    # Bind tools to model
    model_with_tools = model.bind_tools(
        [
            *state["copilotkit"]["actions"],
            GENERATE_TASK_STEPS_TOOL
        ],
        parallel_tool_calls=False,
    )

    # Generate response
    response = await model_with_tools.ainvoke([
        SystemMessage(content=system_prompt),
        *state["messages"],
    ], config)

    messages = state["messages"] + [response]
    
    # Handle tool calls
    if hasattr(response, "tool_calls") and response.tool_calls and len(response.tool_calls) > 0:
        tool_call = response.tool_calls[0]
        
        # Extract tool call information
        if hasattr(tool_call, "id"):
            tool_call_id = tool_call.id
            tool_call_name = tool_call.name
            tool_call_args = tool_call.args if not isinstance(tool_call.args, str) else json.loads(tool_call.args)
        else:
            tool_call_id = tool_call.get("id", "")
            tool_call_name = tool_call.get("name", "")
            args = tool_call.get("args", {})
            tool_call_args = args if not isinstance(args, str) else json.loads(args)

        if tool_call_name == "generate_task_steps":
            # Process steps from tool call
            steps_raw = tool_call_args.get("steps", [])
            
            steps_data = []
            if isinstance(steps_raw, list):
                for step in steps_raw:
                    if isinstance(step, dict) and "description" in step:
                        steps_data.append({
                            "description": step["description"],
                            "status": "enabled"
                        })
                    elif isinstance(step, str):
                        steps_data.append({
                            "description": step,
                            "status": "enabled"
                        })
            
            if not steps_data:
                await copilotkit_exit(config)
                return Command(
                    goto=END,
                    update={
                        "messages": messages,
                        "steps": state["steps"],
                    }
                )
            
            # Update state with steps
            state["steps"] = steps_data
            
            # Add tool response
            tool_response = {
                "role": "tool",
                "content": "Task steps generated.",
                "tool_call_id": tool_call_id
            }
            messages = messages + [tool_response]

            # Move to human confirmation node
            return Command(
                goto="process_steps_node",
                update={
                    "messages": messages,
                    "steps": state["steps"],
                }
            )
    
    # No tool calls, end conversation
    await copilotkit_exit(config)
    return Command(
        goto=END,
        update={
            "messages": messages,
            "steps": state["steps"],
        }
    )

async def process_steps_node(state: Dict[str, Any], config: RunnableConfig):
    """
    Node that handles human-in-the-loop step confirmation.
    """
    
    # Check if we already have user response (after interrupt)
    if "user_response" in state and state["user_response"]:
        user_response = state["user_response"]
    else:
        # Use LangGraph interrupt for human-in-the-loop
        user_response = interrupt({"steps": state["steps"]})
        state["user_response"] = user_response
    
    # Generate final response based on user selection
    final_prompt = """
    The user has confirmed their task steps. Provide a helpful summary of how to proceed with the selected steps.
    Keep your response practical and encouraging. If they disabled certain steps, acknowledge their choices.
    """
    
    final_response = await create_deepseek_model().ainvoke([
        SystemMessage(content=final_prompt),
        {"role": "user", "content": user_response}
    ], config)

    messages = state["messages"] + [final_response]
    
    # Clear user response for future interactions
    if "user_response" in state:
        state.pop("user_response")
    
    await copilotkit_exit(config)
    return Command(
        goto=END,
        update={
            "messages": messages,
            "steps": state["steps"],
        }
    )

# Build the workflow
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("start_flow", start_flow)
workflow.add_node("chat_node", chat_node)
workflow.add_node("process_steps_node", process_steps_node)

# Set entry point and edges
workflow.set_entry_point("start_flow")
workflow.add_edge(START, "start_flow")
workflow.add_edge("start_flow", "chat_node")
workflow.add_edge("process_steps_node", END)

# Add conditional edges from chat_node
def should_continue(command: Command):
    if command.goto == "process_steps_node":
        return "process_steps_node"
    else:
        return END

workflow.add_conditional_edges(
    "chat_node",
    should_continue,
    {
        "process_steps_node": "process_steps_node",
        END: END,
    },
)

# Compile the graph
debug_human_in_the_loop_graph = workflow.compile(checkpointer=MemorySaver())