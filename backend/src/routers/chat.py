from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from uuid import UUID
import logging
from typing import List, Dict, Any

from ..models.models import DomainVersion, Domain
from ..models.schemas import (
    ChatRequest,
    ChatResponse,
    GraphState,
    MessageType,
    IntentType,
)
from ..core.database import get_db
from ..core.config import ConfigManager
from ..chat.graph_assistant import GraphAssistant

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/chat",
    response_model=ChatResponse,
    description="Process a chat message for knowledge graph assistance",
)
async def process_chat_message(
    tenant_id: UUID,
    domain_id: UUID,
    request: ChatRequest,
    db: Session = Depends(get_db),
):
    """
    Process a chat message and return appropriate response.

    The function:
    1. Validates domain and versions
    2. Initializes graph assistant
    3. Processes message through workflow
    4. Returns formatted response
    """
    try:
        # Validate domain exists
        domain = (
            db.query(Domain)
            .filter(Domain.tenant_id == tenant_id, Domain.domain_id == domain_id)
            .first()
        )

        if not domain:
            raise HTTPException(status_code=404, detail="Domain not found")

        # Get current domain version
        domain_version = (
            db.query(DomainVersion)
            .filter(DomainVersion.domain_id == domain_id)
            .order_by(DomainVersion.version_number.desc())
            .first()
        )

        if not domain_version:
            raise HTTPException(status_code=404, detail="No domain version found")

        # Initialize config and assistant
        config = ConfigManager(db, str(tenant_id), str(domain_id))
        assistant = GraphAssistant(config)

        # Prepare initial state using GraphState schema
        initial_state = GraphState(
            message=request.message.content,
            tenant_id=tenant_id,
            domain_id=domain_id,
            domain_version=domain_version.version_number,
            parse_versions=request.versions.parse_versions,
            extract_versions=request.versions.extract_versions,
            merge_version_id=request.versions.merge_version_id,
            group_version_id=request.versions.group_version_id,
            ontology_version_id=request.versions.ontology_version_id,
            db=db,
        )

        # Process message through workflow
        logger.info(f"Processing message: {request.message.content}")
        result = await assistant.process_message(initial_state)

        # Create response using ChatResponse schema
        response = ChatResponse.parse_obj(result)

        logger.info(f"Generated response type: {response.message_type}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}", exc_info=True)
        # Return error response using schema
        return ChatResponse(
            message_type=MessageType.ERROR,
            intent=IntentType.ERROR,
            response=f"Error processing message: {str(e)}",
            warnings=[str(e)],
        )


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/chat/todo",
    response_model=List[Dict[str, Any]],
    description="Get todo list for a domain",
)
async def get_todo_list(
    tenant_id: UUID,
    domain_id: UUID,
    db: Session = Depends(get_db),
):
    """Get the current todo list for a domain"""
    try:
        # Here you would implement getting the todo list from your storage
        # This is a placeholder implementation
        return []
    except Exception as e:
        logger.error(f"Error getting todo list: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error retrieving todo list: {str(e)}"
        )
