from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from uuid import UUID
import logging
from typing import Optional
from langchain_core.messages import HumanMessage

from ..models.schemas import ChatRequest, ChatResponse, MessageType, IntentType
from ..core.database import get_db
from ..chat.assistant import GraphAssistant
from ..llm.llm_factory import LLMFactory, LLMConfig
from ..core.config import ConfigManager

logger = logging.getLogger(__name__)
router = APIRouter()


def create_llm_client(config: ConfigManager):
    """Create LLM client with configuration"""
    llm_config = LLMConfig(
        provider=config.get("llm_provider", "bedrock"),
        profile_name=config.get("aws_profile"),
        model_id=config.get(
            "aws_model_id", "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
        ),
        model_kwargs={
            "temperature": float(config.get("llm_temperature", 0)),
            "max_tokens": int(config.get("llm_max_tokens", 4096)),
        },
    )
    return LLMFactory(llm_config).create_model()


@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/chat", response_model=ChatResponse
)
async def process_chat_message(
    tenant_id: UUID,
    domain_id: UUID,
    request: ChatRequest,
    db: Session = Depends(get_db),
):
    """Process a chat message within a specific domain"""
    try:

        # Get configuration
        config = ConfigManager(db, str(tenant_id), str(domain_id))

        # Create LLM client
        llm_client = create_llm_client(config)

        # Create graph assistant
        assistant = GraphAssistant(llm_client=llm_client, db=db)

        # Prepare state for processing
        state = {
            "messages": [HumanMessage(content=request.message.content)],
            "tenant_id": tenant_id,
            "domain_id": domain_id,
            "db": db,
            "versions": {
                "file_versions": request.versions.file_versions,
                "parse_versions": request.versions.parse_versions,
                "extract_versions": request.versions.extract_versions,
                "merge_version": request.versions.merge_version_id,
                "group_version": request.versions.group_version_id,
                "ontology_version": request.versions.ontology_version_id,
            },
        }

        # Process message through graph
        result = await assistant.process_message(state)

        print(result)

        return ChatResponse(
            message_type=MessageType.TEXT,
            intent=IntentType.ANALYZE_RESULTS,
            response=result.get("response", ""),
            suggestions=result.get("suggestions", []),
            warnings=result.get("warnings", []),
            visualization=result.get("visualization"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}", exc_info=True)
        return ChatResponse(
            message_type=MessageType.ERROR,
            intent=IntentType.ERROR,
            response=f"Error processing message: {str(e)}",
            warnings=[str(e)],
        )
