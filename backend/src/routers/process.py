from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional
import logging

from ..models.models import (
    Domain,
    ProcessingPipeline,
    PipelineStatus,
    PipelineStage,
    ParseVersion,
    ExtractVersion,
    GraphVersion,
)
from ..models.schemas import (
    ProcessingPipeline as ProcessingPipelineSchema,
    ProcessingVersionBase,
    StageStatusResponse,
    PipelineActionResponse,
    PipelineErrorResponse,
)
from ..core.database import get_db
from ..core.config import ConfigManager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/pipeline/{pipeline_id}",
    response_model=ProcessingPipelineSchema,
)
async def get_pipeline_status(
    tenant_id: UUID,
    domain_id: UUID,
    pipeline_id: UUID,
    db: Session = Depends(get_db),
):
    """Get the status of a specific processing pipeline"""
    pipeline = (
        db.query(ProcessingPipeline)
        .join(Domain)
        .filter(
            Domain.tenant_id == tenant_id,
            ProcessingPipeline.domain_id == domain_id,
            ProcessingPipeline.pipeline_id == pipeline_id,
        )
        .first()
    )

    if not pipeline:
        raise HTTPException(status_code=404, detail="Processing pipeline not found")

    # Get current version IDs for each stage
    current_parse = (
        db.query(ParseVersion)
        .filter(ParseVersion.pipeline_id == pipeline_id)
        .order_by(ParseVersion.version_number.desc())
        .first()
    )

    current_extract = (
        db.query(ExtractVersion)
        .filter(ExtractVersion.pipeline_id == pipeline_id)
        .order_by(ExtractVersion.version_number.desc())
        .first()
    )

    current_graph = (
        db.query(GraphVersion)
        .filter(GraphVersion.pipeline_id == pipeline_id)
        .order_by(GraphVersion.version_number.desc())
        .first()
    )

    return ProcessingPipelineSchema(
        pipeline_id=pipeline.pipeline_id,
        domain_id=pipeline.domain_id,
        stage=pipeline.stage,
        status=pipeline.status,
        error=pipeline.error,
        created_at=pipeline.created_at,
        current_parse_id=current_parse.version_id if current_parse else None,
        current_extract_id=current_extract.version_id if current_extract else None,
        current_graph_id=current_graph.version_id if current_graph else None,
    )


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/pipeline/{pipeline_id}/content/{version_id}",
    response_model=dict,
)
async def get_processing_content(
    tenant_id: UUID,
    domain_id: UUID,
    pipeline_id: UUID,
    version_id: UUID,
    db: Session = Depends(get_db),
):
    """Get the output content for a specific processing version"""
    # Try to find the version in each possible stage
    version = None
    for Version in [ParseVersion, ExtractVersion, GraphVersion]:
        version = (
            db.query(Version)
            .join(ProcessingPipeline)
            .join(Domain)
            .filter(
                Domain.tenant_id == tenant_id,
                ProcessingPipeline.domain_id == domain_id,
                ProcessingPipeline.pipeline_id == pipeline_id,
                Version.version_id == version_id,
            )
            .first()
        )
        if version:
            break

    if not version:
        raise HTTPException(status_code=404, detail="Processing version not found")

    try:
        if not os.path.exists(version.output_path):
            return {"content": None}

        with open(version.output_path, "r") as f:
            content = f.read()

        return {"content": content}
    except Exception as e:
        logger.error(f"Error reading output file: {str(e)}")
        raise HTTPException(status_code=500, detail="Error reading output file")


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/pipeline/{pipeline_id}/stage/{stage}/status",
    response_model=StageStatusResponse,
)
async def get_stage_status(
    tenant_id: UUID,
    domain_id: UUID,
    pipeline_id: UUID,
    stage: PipelineStage,
    db: Session = Depends(get_db),
):
    """Get status for a specific pipeline stage"""
    pipeline = (
        db.query(ProcessingPipeline)
        .join(Domain)
        .filter(
            Domain.tenant_id == tenant_id,
            Domain.domain_id == domain_id,
            ProcessingPipeline.pipeline_id == pipeline_id,
        )
        .first()
    )

    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    return {
        "stage": stage,
        "status": pipeline.get_stage_status(stage),
        "can_start": pipeline.can_start_stage(stage),
        "versions": pipeline.get_stage_versions(stage),
        "latest_version_id": pipeline.get_latest_version_by_stage(stage),
    }
