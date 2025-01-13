from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import Literal, Dict, List, Optional
from langchain_aws.chat_models import ChatBedrock
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from tools import tools
from prompts import AGENT_PROMPT, SYSTEM_TEMPLATE
import json


class Visualization(BaseModel):
    type: Literal["mermaid", "markdown", "code", "none"] = Field(...)
    content: str = Field(...)
    title: str = Field(...)


class LLMResponse(BaseModel):
    message: str = Field(...)
    visualization: Visualization = Field(...)
    tool_usage: Optional[List[Dict[str, str]]] = Field(default=[])


def init_agent():
    """Initialize the ReAct agent with tools."""
    # Initialize the model
    model = ChatBedrock(
        model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        region_name="us-east-1",
        credentials_profile_name="ho-s-e0-df-ds-workspaces",
        model_kwargs={
            "temperature": 0,
            "max_tokens": 4096,
        },
    )

    # Create ReAct agent with correct parameters
    agent_executor = create_react_agent(
        model,  # The LLM
        tools,  # Available tools
        state_modifier=AGENT_PROMPT,  # The prompt template
    )

    return agent_executor


def format_messages(messages, pdf_context: str = None) -> List[Dict[str, str]]:
    """
    Format chat messages and PDF context for the agent.

    Args:
        messages: List of chat messages
        pdf_context: Optional PDF content

    Returns:
        List of formatted messages
    """
    formatted_messages = []
    system_content = SYSTEM_TEMPLATE

    # Add PDF context to system message if available
    if pdf_context:
        system_content += f"""
Available PDF Content for Reference:
{pdf_context}

Guidelines for PDF content:
- Cite specific sections when referencing
- Create visualizations to explain concepts
- Integrate with programming knowledge
- Maintain clear structure in responses
"""

    # Add system message
    formatted_messages.append({"role": "system", "content": system_content})

    # Add conversation messages
    for msg in messages:
        if msg["role"] == "user":
            formatted_messages.append({"role": "user", "content": msg["content"]})
        elif msg["role"] == "assistant":
            formatted_messages.append(
                {
                    "role": "assistant",
                    "content": msg.get("explanation", ""),
                    "tool_usage": msg.get("tool_usage", []),
                }
            )

    return formatted_messages


def extract_visualization(response: str) -> Dict[str, str]:
    """
    Extract visualization content from response.

    Args:
        response: Agent response string

    Returns:
        Dictionary with visualization type and content
    """
    viz_content = ""
    viz_type = "none"
    viz_title = ""

    # Check for Mermaid diagram
    if "```mermaid" in response:
        viz_type = "mermaid"
        viz_content = response.split("```mermaid")[1].split("```")[0].strip()
        viz_title = "Diagram"

    # Check for Python code
    elif "```python" in response:
        viz_type = "code"
        viz_content = response.split("```python")[1].split("```")[0].strip()
        viz_title = "Code Example"

    # Check for Markdown content
    elif "```markdown" in response:
        viz_type = "markdown"
        viz_content = response.split("```markdown")[1].split("```")[0].strip()
        viz_title = "Documentation"

    return {"type": viz_type, "content": viz_content, "title": viz_title}


def generate_response(messages, pdf_context: str = None):
    """Generate response using ReAct agent."""
    try:
        agent = init_agent()

        # Format the input
        last_message = messages[-1]["content"]
        if pdf_context:
            last_message = f"Context:\n{pdf_context}\n\nQuery: {last_message}"

        # Invoke the agent
        result = agent.invoke(
            {
                "messages": [("user", last_message)],
                "is_last_step": "false",
                "remaining_steps": "Analyze and respond to the query",
            }
        )

        # Parse the response as JSON
        if isinstance(result, str):
            parsed_response = json.loads(result)
        elif isinstance(result, dict) and "messages" in result:
            # Get the last message content and parse it as JSON
            last_message_content = result["messages"][-1].content
            parsed_response = json.loads(last_message_content)
        else:
            parsed_response = json.loads(str(result))

        return {
            "explanation": parsed_response["message"],
            "viz_content": parsed_response["visualization"]["content"],
            "viz_type": parsed_response["visualization"]["type"],
        }

    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {str(e)}")
        return {
            "explanation": "Error parsing response format",
            "viz_content": "",
            "viz_type": "none",
        }
    except Exception as e:
        print(f"Error in generate_response: {str(e)}")
        return {
            "explanation": f"I encountered an error: {str(e)}",
            "viz_content": "",
            "viz_type": "none",
        }


def format_chat_history(messages: List[Dict]) -> List[Dict]:
    """
    Format chat history for the agent.

    Args:
        messages: List of chat messages

    Returns:
        Formatted chat history
    """
    return [
        {
            "role": msg["role"],
            "content": msg["content"] if msg["role"] == "user" else msg["explanation"],
            "tool_usage": msg.get("tool_usage", []),
        }
        for msg in messages
    ]


# Optional: Add debugging functions
def debug_agent_response(response: Dict):
    """
    Print detailed debug information about agent response.

    Args:
        response: Agent response dictionary
    """
    print("\n=== Agent Response Debug ===")
    print(
        "Explanation:",
        (
            response["explanation"][:100] + "..."
            if len(response["explanation"]) > 100
            else response["explanation"]
        ),
    )
    print("\nVisualization Type:", response["viz_type"])
    print(
        "Visualization Content:",
        response["viz_content"][:100] + "..." if response["viz_content"] else "None",
    )
    print("\nTool Usage:")
    for tool in response["tool_usage"]:
        print(f"- Tool: {tool['tool']}")
        print(f"  Input: {tool['input']}")
        print(
            f"  Output: {tool['output'][:100]}..."
            if len(tool["output"]) > 100
            else tool["output"]
        )
    print("========================\n")


def list_available_tools() -> List[Dict[str, str]]:
    """
    List all available tools and their descriptions.

    Returns:
        List of tool information dictionaries
    """
    return [
        {"name": tool.name, "description": tool.description, "args": str(tool.args)}
        for tool in tools
    ]


if __name__ == "__main__":
    # Test code
    test_messages = [
        {"role": "user", "content": "Can you list the Python files in this project?"}
    ]
