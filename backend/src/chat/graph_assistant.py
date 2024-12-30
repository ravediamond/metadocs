import logging
import json
from typing import TypedDict, List, Dict, Any
from langchain.schema import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langgraph.graph import END, StateGraph, START

from ..core.config import ConfigManager
from ..llm.llm_factory import LLMConfig, LLMFactory
from ..models.schemas import (
    GraphState as BaseGraphState,
    ChatResponse,
    MessageType,
    IntentType,
)


class GraphAssistant:
    def __init__(self, config_manager: ConfigManager):
        """Initialize the GraphAssistant with configuration."""
        self.config = config_manager

        # Setup logging
        self.logger = logging.getLogger("graph_assistant")
        self.logger.setLevel(logging.DEBUG)

        # Create console handler with formatting
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        self.logger.info("Initializing GraphAssistant")

        # Initialize LLM
        llm_config = self._setup_llm_config()
        self.llm = LLMFactory(llm_config).create_model()

        # Setup prompts
        self.analyze_prompt = "Determine user intent from: {message}"
        self.response_prompt = """Generate a response for user help with intent: {intent}.
        Context: {context}"""

        # Setup workflow
        self.workflow = self._setup_workflow()
        self.graph = self.workflow.compile()

        self.logger.info("GraphAssistant initialization complete")

    def analyze_message(self, state: Dict) -> Dict:
        """Analyze the message to determine intent"""
        self.logger.info(f"ANALYZE STEP - Input state: {json.dumps(state, indent=2)}")

        messages = [
            SystemMessage(
                content="You are an intent analyzer. Classify as: create_version, modify_prompt, analyze_results, start_processing, get_status, or help"
            ),
            HumanMessage(content=state["message"]),
        ]

        self.logger.info("Sending to LLM for analysis")
        try:
            response = self.llm.invoke(messages)
            self.logger.info(f"LLM Response: {response.content}")

            # Extract intent from response
            intent = IntentType.UNKNOWN
            if "create" in response.content.lower():
                intent = IntentType.CREATE_VERSION
            elif (
                "modify" in response.content.lower()
                or "prompt" in response.content.lower()
            ):
                intent = IntentType.MODIFY_PROMPT
            elif "analyze" in response.content.lower():
                intent = IntentType.ANALYZE_RESULTS
            elif (
                "start" in response.content.lower()
                or "process" in response.content.lower()
            ):
                intent = IntentType.START_PROCESSING
            elif "status" in response.content.lower():
                intent = IntentType.GET_STATUS
            elif "help" in response.content.lower():
                intent = IntentType.HELP

            new_state = {**state, "intent": intent}
            self.logger.info(
                f"ANALYZE STEP - Output state: {json.dumps(new_state, indent=2)}"
            )
            return new_state

        except Exception as e:
            self.logger.error(f"Error in analyze_message: {str(e)}", exc_info=True)
            return {**state, "intent": IntentType.ERROR, "warnings": [str(e)]}

    def generate_response(self, state: Dict) -> Dict:
        """Generate response based on intent"""
        self.logger.info(f"GENERATE STEP - Input state: {json.dumps(state, indent=2)}")

        messages = [
            SystemMessage(content="You are a helpful knowledge graph assistant"),
            HumanMessage(
                content=f"""Based on the intent {state.get('intent', 'UNKNOWN')}, 
            help the user with their request: {state['message']}"""
            ),
        ]

        self.logger.info("Sending to LLM for response")
        try:
            response = self.llm.invoke(messages)
            self.logger.info(f"LLM Response: {response.content}")

            new_state = {
                **state,
                "response": response.content,
                "suggestions": [
                    "Consider looking at documentation",
                    "Try using the help command",
                ],
                "todo_list": ["Review current settings", "Verify configurations"],
                "warnings": [],
            }
            self.logger.info(
                f"GENERATE STEP - Output state: {json.dumps(new_state, indent=2)}"
            )
            return new_state

        except Exception as e:
            self.logger.error(f"Error in generate_response: {str(e)}", exc_info=True)
            return {
                **state,
                "response": "An error occurred while generating the response.",
                "warnings": [str(e)],
            }

    def _setup_workflow(self) -> StateGraph:
        """Setup the LangGraph workflow"""
        self.logger.info("Setting up workflow")
        workflow = StateGraph("AssistantState")

        # Add nodes
        workflow.add_node("analyze", self.analyze_message)
        workflow.add_node("generate", self.generate_response)

        # Build graph
        workflow.add_edge(START, "analyze")
        workflow.add_edge("analyze", "generate")
        workflow.add_edge("generate", END)

        return workflow

    def _setup_llm_config(self) -> LLMConfig:
        """Setup LLM configuration"""
        config = LLMConfig(
            provider=self.config.get("llm_provider", "bedrock"),
            profile_name=self.config.get("aws_profile"),
            model_id=self.config.get(
                "aws_model_id", "anthropic.claude-3-sonnet-20240229-v1:0"
            ),
            model_kwargs={
                "temperature": float(self.config.get("llm_temperature", 0)),
                "max_tokens": int(self.config.get("llm_max_tokens", 4096)),
            },
        )
        self.logger.info(f"LLM Config: {json.dumps(config.__dict__, indent=2)}")
        return config

    async def process_message(self, state: BaseGraphState) -> Dict[str, Any]:
        """Process a message through the workflow"""
        self.logger.info(f"Starting message processing for domain {state.domain_id}")
        self.logger.info(f"Input message: {state.message}")

        try:
            initial_state = {
                "message": state.message,
                "tenant_id": str(state.tenant_id),
                "domain_id": str(state.domain_id),
                "domain_version": state.domain_version,
                "parse_versions": state.parse_versions,
                "extract_versions": state.extract_versions,
                "merge_version_id": state.merge_version_id,
                "group_version_id": state.group_version_id,
                "ontology_version_id": state.ontology_version_id,
                "intent": None,
                "response": None,
                "suggestions": [],
                "warnings": [],
                "todo_list": [],
            }

            self.logger.info("Starting graph execution")
            final_state = None
            for step_num, output in enumerate(self.graph.stream(initial_state)):
                self.logger.info(
                    f"Step {step_num + 1} output: {json.dumps(output, indent=2)}"
                )
                # Store the latest output, accessing the nested state
                if "generate" in output:
                    final_state = output["generate"]
                elif "analyze" in output:
                    final_state = output["analyze"]

            if not final_state:
                raise Exception("Graph execution produced no output")

            # Create response using the final state
            response = ChatResponse(
                message_type=MessageType.TEXT,
                intent=final_state.get("intent", IntentType.ERROR),
                response=final_state.get(
                    "response", "An error occurred during processing."
                ),
                suggestions=final_state.get("suggestions", []),
                warnings=final_state.get("warnings", []),
                todo_list=final_state.get("todo_list", []),
            )

            self.logger.info(f"Final response: {json.dumps(response.dict(), indent=2)}")
            return response.dict()

        except Exception as e:
            self.logger.error(f"Error in message processing: {str(e)}", exc_info=True)
            return ChatResponse(
                message_type=MessageType.ERROR,
                intent=IntentType.ERROR,
                response="I apologize, but I encountered an error while processing your request.",
                warnings=[str(e)],
            ).dict()
