from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from uuid import UUID
import logging
from typing import Dict, Any, List

from ..models.schemas import ChatRequest, ChatResponse, MessageType, IntentType
from ..core.database import get_db
from ..chat.graph_assistant import GraphAssistant, ChatState
from ..models.models import Domain, DomainVersion
from ..llm.llm_factory import LLMFactory, LLMConfig
from ..core.config import ConfigManager

logger = logging.getLogger(__name__)
router = APIRouter()


def create_llm_client(config: ConfigManager):
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
    try:
        config = ConfigManager(db, str(tenant_id), str(domain_id))
        llm_client = create_llm_client(config)
        assistant = GraphAssistant(llm_client=llm_client, db=db)

        domain = (
            db.query(Domain)
            .filter(Domain.tenant_id == tenant_id, Domain.domain_id == domain_id)
            .first()
        )
        if not domain:
            raise HTTPException(status_code=404, detail="Domain not found")

        last_version = (
            db.query(DomainVersion)
            .filter(DomainVersion.domain_id == domain_id)
            .order_by(DomainVersion.version_number.desc())
            .first()
        )

        state = ChatState(
            message=request.message.content,
            tenant_id=tenant_id,
            domain_id=domain_id,
            db=db,
            domain_version=last_version.version_number,
            versions={
                "parse": request.versions.parse_versions,
                "extract": request.versions.extract_versions,
                "merge": request.versions.merge_version_id,
                "group": request.versions.group_version_id,
                "ontology": request.versions.ontology_version_id,
            },
        )

        result = await assistant.process_message(state)
        return ChatResponse(**result)

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
