from langchain_core.pydantic_v1 import BaseModel, Field
from typing import Literal, Dict, List, Optional
from langchain_aws.chat_models import ChatBedrock
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


def generate_response(messages):
    """Generate response using ReAct agent."""
    try:
        agent = init_agent()
        formatted_messages = []
        for msg in messages[:-1]:
            role = "assistant" if msg["role"] == "assistant" else "user"
            content = msg.get("content")
            formatted_messages.append((role, content))

        last_message = messages[-1]["content"]
        formatted_messages.append(("user", last_message))

        result = agent.invoke(
            {
                "messages": formatted_messages,
            }
        )

        if "messages" in result:
            last_message = result["messages"][-1]
            content = last_message.content if hasattr(last_message, "content") else ""

            # Try to find JSON in content
            json_start = content.find("{")
            if json_start != -1:
                try:
                    json_str = content[json_start:]
                    parsed_response = json.loads(json_str)
                except json.JSONDecodeError:
                    # If JSON parsing fails, wrap the content in our expected format
                    parsed_response = {
                        "message": content,
                        "visualization": {
                            "type": "markdown",
                            "content": content,
                            "title": "Response",
                        },
                    }
            else:
                # If no JSON found, wrap the plain text in our expected format
                parsed_response = {
                    "message": content,
                    "visualization": {
                        "type": "markdown",
                        "content": content,
                        "title": "Response",
                    },
                }

            return {
                "content": parsed_response["message"],
                "viz_content": parsed_response["visualization"]["content"],
                "viz_type": parsed_response["visualization"]["type"],
            }

        raise ValueError("No valid message content found")

    except Exception as e:
        print(f"Error in generate_response: {str(e)}")
        return {
            "content": f"I encountered an error: {str(e)}",
            "viz_content": "",
            "viz_type": "none",
        }
