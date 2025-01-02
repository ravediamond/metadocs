from typing import Dict, Any
from uuid import UUID
import logging
from pydantic import BaseModel
from sqlalchemy.orm import Session
import json
from ..models.schemas import MessageType, IntentType
from . import prompts


class ChatState(BaseModel):
    message: str
    tenant_id: UUID
    domain_id: UUID
    db: Session
    domain_version: int
    versions: Dict[str, Any]

    class Config:
        arbitrary_types_allowed = True


class GraphAssistant:
    def __init__(self, llm_client, db: Session):
        self.llm = llm_client
        self.db = db
        self.logger = logging.getLogger("graph_assistant")

    async def process_message(self, state: ChatState) -> Dict[str, Any]:
        try:
            data = self._load_version_data(state.versions)
            messages = prompts.ANALYZE_TYPE_PROMPT.format_messages(
                message=state.message
            )
            response = await self.llm.ainvoke(messages)

            try:
                is_question = json.loads(response.content)["is_question"]
            except json.JSONDecodeError:
                self.logger.warning(
                    f"Failed to parse analysis response: {response.content}"
                )
                is_question = "?" in state.message

            if is_question:
                messages = prompts.QUESTION_PROMPT.format_messages(
                    message=state.message, data=json.dumps(data, indent=2)
                )
                response = await self.llm.ainvoke(messages)
                intent = IntentType.ANALYZE_RESULTS
            else:
                messages = prompts.MODIFICATION_PROMPT.format_messages(
                    message=state.message, data=json.dumps(data, indent=2)
                )
                response = await self.llm.ainvoke(messages)
                intent = IntentType.MODIFY_PROMPT

            try:
                result = json.loads(response.content)
            except json.JSONDecodeError:
                self.logger.error(f"Failed to parse response: {response.content}")
                result = {
                    "content": "I had trouble understanding that. Could you rephrase?",
                    "next_steps": [],
                    "warnings": ["Failed to parse response"],
                }

            return {
                "message_type": MessageType.TEXT,
                "intent": intent,
                "response": result["content"],
                "suggestions": result.get("next_steps", []),
                "warnings": result.get("warnings", []),
            }

        except Exception as e:
            self.logger.error(f"Error: {str(e)}", exc_info=True)
            return {
                "message_type": MessageType.ERROR,
                "intent": IntentType.ERROR,
                "response": "An error occurred processing your request",
                "warnings": [str(e)],
            }

    def _load_version_data(self, versions: Dict[str, Any]) -> Dict[str, Any]:
        data = {}
        try:
            for version_type, version_id in versions.items():
                if version_id:
                    version_obj = self._get_version_object(version_type, version_id)
                    if version_obj and version_obj.output_path:
                        with open(version_obj.output_path, "r") as f:
                            data[version_type] = json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading data: {str(e)}")
        return data

    def _get_version_object(self, version_type: str, version_id: Any):
        model_map = {
            "parse": "ParseVersion",
            "extract": "ExtractVersion",
            "merge": "MergeVersion",
            "group": "GroupVersion",
            "ontology": "OntologyVersion",
        }
        model = globals().get(model_map.get(version_type))
        return model and self.db.query(model).filter_by(version_id=version_id).first()
