from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from uuid import UUID
import logging
from typing import Optional, List
from langchain_core.messages import HumanMessage

from ..models.schemas import (
    ChatRequest,
    ChatResponse,
    MessageType,
    IntentType,
    ProcessingRequest,
    GraphUpdateRequest,
    VisualizationRequest,
)
from ..core.database import get_db
from ..chat.assistant import GraphAssistant
from ..llm.llm_factory import LLMFactory, LLMConfig
from ..core.config import ConfigManager
from ..models.models import (
    ProcessingPipeline,
    PipelineStatus,
    PipelineStage,
    Domain,
    DomainVersionFile,
    GraphVersion,
)

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
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Process a chat message and handle processing commands"""
    try:
        config = ConfigManager(db, str(tenant_id), str(domain_id))
        llm_client = create_llm_client(config)
        assistant = GraphAssistant(llm_client=llm_client, db=db, config=config)

        # Create state with message and context
        state = {
            "messages": [HumanMessage(content=request.message.content)],
            "tenant_id": tenant_id,
            "domain_id": domain_id,
            "db": db,
        }

        # Process message through assistant
        result = await assistant.process_message(state)

        # Handle processing commands if needed
        if result.get("intent") == IntentType.PROCESS:
            pipeline_id = await handle_processing_command(
                tenant_id,
                domain_id,
                result.get("command"),
                background_tasks,
                db,
                config,
            )
            if pipeline_id:
                result["pipeline_id"] = pipeline_id

        return ChatResponse(**result)

    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}", exc_info=True)
        return ChatResponse(
            message_type=MessageType.ERROR,
            intent=IntentType.ERROR,
            response=f"Error processing message: {str(e)}",
            warnings=[str(e)],
        )


@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/process", response_model=ChatResponse
)
async def start_processing(
    tenant_id: UUID,
    domain_id: UUID,
    request: ProcessingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Start processing through chat interface"""
    try:
        config = ConfigManager(db, str(tenant_id), str(domain_id))

        # Create new pipeline
        pipeline = ProcessingPipeline(
            domain_id=domain_id,
            stage=PipelineStage.NOT_STARTED,
            status=PipelineStatus.UNINITIALIZED,
        )
        db.add(pipeline)
        db.commit()

        # Start processing in background
        background_tasks.add_task(
            process_files,
            tenant_id,
            domain_id,
            pipeline.pipeline_id,
            request.files,
            db,
            config,
        )

        return ChatResponse(
            message_type=MessageType.COMMAND,
            intent=IntentType.PROCESS,
            response="Processing started",
            pipeline_id=pipeline.pipeline_id,
        )

    except Exception as e:
        logger.error(f"Error starting processing: {str(e)}", exc_info=True)
        return ChatResponse(
            message_type=MessageType.ERROR,
            intent=IntentType.ERROR,
            response=f"Error starting processing: {str(e)}",
            warnings=[str(e)],
        )


@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/graph/update", response_model=ChatResponse
)
async def update_graph(
    tenant_id: UUID,
    domain_id: UUID,
    request: GraphUpdateRequest,
    db: Session = Depends(get_db),
):
    """Update knowledge graph based on feedback"""
    try:
        config = ConfigManager(db, str(tenant_id), str(domain_id))
        llm_client = create_llm_client(config)
        assistant = GraphAssistant(llm_client=llm_client, db=db, config=config)

        result = await assistant.update_graph(domain_id, request.feedback)

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])

        return ChatResponse(
            message_type=MessageType.COMMAND,
            intent=IntentType.PROCESS,
            response="Graph updated successfully",
            visualization=result.get("data", {}).get("visualization"),
        )

    except Exception as e:
        logger.error(f"Error updating graph: {str(e)}", exc_info=True)
        return ChatResponse(
            message_type=MessageType.ERROR,
            intent=IntentType.ERROR,
            response=f"Error updating graph: {str(e)}",
            warnings=[str(e)],
        )


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/graph/{graph_version_id}",
    response_model=ChatResponse,
)
async def get_graph_status(
    tenant_id: UUID,
    domain_id: UUID,
    graph_version_id: UUID,
    db: Session = Depends(get_db),
):
    """Get graph status and latest visualization"""
    try:
        version = db.query(GraphVersion).get(graph_version_id)
        if not version:
            raise HTTPException(status_code=404, detail="Graph version not found")

        return ChatResponse(
            message_type=MessageType.COMMAND,
            intent=IntentType.ANALYZE,
            response=f"Graph status: {version.status}",
            visualization=(
                version.visualization if version.status == "completed" else None
            ),
        )

    except Exception as e:
        logger.error(f"Error getting graph status: {str(e)}", exc_info=True)
        return ChatResponse(
            message_type=MessageType.ERROR,
            intent=IntentType.ERROR,
            response=f"Error getting graph status: {str(e)}",
            warnings=[str(e)],
        )


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/graph/{graph_version_id}/visualize",
    response_model=ChatResponse,
)
async def generate_visualization(
    tenant_id: UUID,
    domain_id: UUID,
    graph_version_id: UUID,
    request: VisualizationRequest,
    db: Session = Depends(get_db),
):
    """Generate specific visualization for graph"""
    try:
        config = ConfigManager(db, str(tenant_id), str(domain_id))
        llm_client = create_llm_client(config)
        assistant = GraphAssistant(llm_client=llm_client, db=db, config=config)

        # Get graph version
        version = db.query(GraphVersion).get(graph_version_id)
        if not version:
            raise HTTPException(status_code=404, detail="Graph version not found")

        # Generate visualization using the visualization tool
        visualization = await assistant.generate_visualization(
            version.output_path, request.visualization_type
        )

        return ChatResponse(
            message_type=MessageType.COMMAND,
            intent=IntentType.VISUALIZE,
            response="Visualization generated",
            visualization=visualization,
        )

    except Exception as e:
        logger.error(f"Error generating visualization: {str(e)}", exc_info=True)
        return ChatResponse(
            message_type=MessageType.ERROR,
            intent=IntentType.ERROR,
            response=f"Error generating visualization: {str(e)}",
            warnings=[str(e)],
        )


async def handle_processing_command(
    tenant_id: UUID,
    domain_id: UUID,
    command: dict,
    background_tasks: BackgroundTasks,
    db: Session,
    config: ConfigManager,
) -> Optional[UUID]:
    """Handle processing commands from chat"""
    try:
        # Check if there's an existing pipeline
        pipeline = (
            db.query(ProcessingPipeline)
            .filter(ProcessingPipeline.domain_id == domain_id)
            .order_by(ProcessingPipeline.created_at.desc())
            .first()
        )

        # If pipeline exists and is running, return its ID
        if pipeline and pipeline.status == PipelineStatus.RUNNING:
            return pipeline.pipeline_id

        # Create new pipeline if needed
        if not pipeline or pipeline.status in [
            PipelineStatus.COMPLETED,
            PipelineStatus.FAILED,
        ]:
            pipeline = ProcessingPipeline(
                domain_id=domain_id,
                stage=PipelineStage.NOT_STARTED,
                status=PipelineStatus.UNINITIALIZED,
            )
            db.add(pipeline)
            db.commit()

        # Get files to process
        files = (
            db.query(DomainVersionFile)
            .filter(DomainVersionFile.domain_id == domain_id)
            .all()
        )

        if not files:
            raise HTTPException(status_code=400, detail="No files found for processing")

        # Start processing in background
        background_tasks.add_task(
            process_files,
            tenant_id,
            domain_id,
            pipeline.pipeline_id,
            [f.file_version_id for f in files],
            db,
            config,
        )

        return pipeline.pipeline_id

    except Exception as e:
        logger.error(f"Error handling processing command: {str(e)}")
        raise


async def process_files(
    tenant_id: UUID,
    domain_id: UUID,
    pipeline_id: UUID,
    file_version_ids: List[UUID],
    db: Session,
    config: ConfigManager,
):
    """Process files through the pipeline"""
    try:
        # Initialize LLM and assistant
        llm_client = create_llm_client(config)
        assistant = GraphAssistant(llm_client=llm_client, db=db, config=config)

        # Create state for processing
        state = {
            "tenant_id": tenant_id,
            "domain_id": domain_id,
            "pipeline_id": pipeline_id,
            "file_version_ids": file_version_ids,
            "db": db,
        }

        # Process through assistant
        await assistant.process_pipeline(state)

    except Exception as e:
        logger.error(f"Error processing files: {str(e)}", exc_info=True)
        # Update pipeline status to failed
        try:
            pipeline = db.query(ProcessingPipeline).get(pipeline_id)
            if pipeline:
                pipeline.status = PipelineStatus.FAILED
                pipeline.error = str(e)
                db.commit()
        except Exception as commit_error:
            logger.error(f"Error updating pipeline status: {str(commit_error)}")
