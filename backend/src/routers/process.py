from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, status
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime
from typing import List, Union, Optional
import logging
import os
import sys


from ..models.models import (
    Domain,
    File,
    ProcessingPipeline,
    ParseVersion,
    ExtractVersion,
    MergeVersion,
    GroupVersion,
    OntologyVersion,
    GraphVersion,
    DomainVersion,
    DomainVersionStatus,
    FileVersion,
    PipelineStatus,
    PipelineStage,
    DomainVersionFile,
)
from ..models.schemas import (
    ProcessingPipeline as ProcessingPipelineSchema,
    ProcessingVersionBase,
    MergeRequest,
    OntologyRequest,
    ParsePrompts,
    ExtractPrompts,
    MergePrompts,
    GroupPrompts,
    OntologyPrompts,
    StageStartResponse,
    StageStatusResponse,
    StageDependenciesResponse,
    StageBatchResponse,
    StartedVersionInfo,
    StageVersionInfo,
    PipelineActionResponse,
    PipelineStartRequest,
    PipelineErrorResponse,
)
from ..processors.prompts.parse_prompts import (
    SYSTEM_PROMPT as PARSE_SYSTEM_PROMPT,
    CHECK_READABILITY_PROMPT,
    CONVERT_TO_MARKDOWN_PROMPT,
)
from ..processors.prompts.extract_prompts import (
    SYSTEM_PROMPT as EXTRACT_SYSTEM_PROMPT,
    INITIAL_ENTITY_EXTRACTION_PROMPT,
    ITERATIVE_ENTITY_EXTRACTION_PROMPT,
    ENTITY_DETAILS_PROMPT as EXTRACT_ENTITY_DETAILS_PROMPT,
)
from ..processors.prompts.merge_prompts import (
    SYSTEM_PROMPT as MERGE_SYSTEM_PROMPT,
    ENTITY_DETAILS_PROMPT as MERGE_ENTITY_DETAILS_PROMPT,
    ENTITY_MERGE_PROMPT,
)
from ..processors.prompts.group_prompts import (
    SYSTEM_PROMPT as GROUP_SYSTEM_PROMPT,
    GROUP_PROMPT,
)
from ..processors.prompts.ontology_prompts import (
    SYSTEM_PROMPT as ONTOLOGY_SYSTEM_PROMPT,
    ONTOLOGY_PROMPT,
)
from ..core.database import get_db
from ..processors.parse_processor import ParseProcessor
from ..processors.extract_processor import ExtractProcessor
from ..processors.group_processor import GroupProcessor
from ..processors.ontology_processor import OntologyProcessor
from ..processors.merge_processor import MergeProcessor
from ..processors.pipeline_orchestrator import PipelineOrchestrator
from ..core.config import ConfigManager, FILE_SYSTEM

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def get_default_prompts(stage: str) -> dict:
    """Return default prompts for each stage"""
    defaults = {
        "parse": {
            "system_prompt": PARSE_SYSTEM_PROMPT,
            "readability_prompt": CHECK_READABILITY_PROMPT,
            "convert_prompt": CONVERT_TO_MARKDOWN_PROMPT,
        },
        "extract": {
            "system_prompt": EXTRACT_SYSTEM_PROMPT,
            "initial_entity_extraction_prompt": INITIAL_ENTITY_EXTRACTION_PROMPT,
            "iterative_extract_entities_prompt": ITERATIVE_ENTITY_EXTRACTION_PROMPT,
            "entity_details_prompt": EXTRACT_ENTITY_DETAILS_PROMPT,
        },
        # Add other stages...
    }
    return defaults.get(stage, {})


def get_stage_specific_prompts(stage: str, version) -> dict:
    """Get stage-specific prompts from a version object"""
    if stage == "parse":
        return {
            "readability_prompt": version.readability_prompt,
            "convert_prompt": version.convert_prompt,
        }
    elif stage == "extract":
        return {
            "initial_entity_extraction_prompt": version.initial_entity_extraction_prompt,
            "iterative_extract_entities_prompt": version.iterative_extract_entities_prompt,
            "entity_details_prompt": version.entity_details_prompt,
        }
    # Add other stages...
    return {}


def validate_stage_prompts(stage: str, prompts: dict):
    """Validate that all required prompts for a stage are present"""
    required_prompts = {
        "parse": ["system_prompt", "readability_prompt", "convert_prompt"],
        "extract": [
            "system_prompt",
            "initial_entity_extraction_prompt",
            "iterative_extract_entities_prompt",
            "entity_details_prompt",
        ],
        # Add other stages...
    }

    missing = [p for p in required_prompts[stage] if p not in prompts]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required prompts for {stage}: {', '.join(missing)}",
        )


def get_next_version_number(db: Session, pipeline_id: UUID, version_model) -> int:
    """Get next version number for a specific version type in a pipeline"""
    latest_version = (
        db.query(version_model)
        .filter(version_model.pipeline_id == pipeline_id)
        .order_by(version_model.version_number.desc())
        .first()
    )

    return (latest_version.version_number + 1) if latest_version else 1


async def process_parse(
    file_version_id: UUID, parse_version_id: UUID, config: ConfigManager, db: Session
) -> bool:
    try:
        logger.info(f"Starting parse for file version {file_version_id}")

        file_version = (
            db.query(FileVersion)
            .filter(FileVersion.file_version_id == file_version_id)
            .first()
        )
        parse_version = (
            db.query(ParseVersion)
            .filter(ParseVersion.version_id == parse_version_id)
            .first()
        )
        pipeline = parse_version.pipeline

        # Update pipeline status
        pipeline.stage = PipelineStage.PARSE
        pipeline.status = PipelineStatus.RUNNING
        db.commit()

        parse_processor = ParseProcessor(file_version, parse_version, config)
        parse_result = parse_processor.process()

        if not parse_result.success:
            logger.error(f"Parse failed: {parse_result.error}")
            parse_version.status = "failed"
            parse_version.error = parse_result.error
            pipeline.update_pipeline_status()
            db.commit()
            return False

        parse_version.status = "completed"
        pipeline.update_pipeline_status()
        db.commit()
        logger.info("Parse completed successfully")
        return True

    except Exception as e:
        logger.error(f"Error in parse processing: {str(e)}", exc_info=True)
        parse_version.status = "failed"
        parse_version.error = str(e)
        pipeline.update_pipeline_status()
        db.commit()
        return False


async def process_extract(
    parse_version_id: UUID, extract_version_id: UUID, config: ConfigManager, db: Session
) -> bool:
    try:
        logger.info(f"Starting extract for parse version {parse_version_id}")

        parse_version = (
            db.query(ParseVersion)
            .filter(ParseVersion.version_id == parse_version_id)
            .first()
        )
        extract_version = (
            db.query(ExtractVersion)
            .filter(ExtractVersion.version_id == extract_version_id)
            .first()
        )
        pipeline = extract_version.pipeline

        # Verify dependencies
        if not pipeline.can_start_stage(PipelineStage.EXTRACT):
            logger.error("Cannot start extract - dependencies not met")
            extract_version.status = "failed"
            extract_version.error = "Parse stage not completed"
            db.commit()
            return False

        pipeline.stage = PipelineStage.EXTRACT
        pipeline.status = PipelineStatus.RUNNING
        db.commit()

        extract_processor = ExtractProcessor(parse_version, extract_version, config)
        extract_result = extract_processor.process()

        if not extract_result.success:
            extract_version.status = extract_result.status
            extract_version.error = extract_result.error
            pipeline.update_pipeline_status()
            db.commit()
            return False

        extract_version.status = extract_result.status
        pipeline.update_pipeline_status()
        db.commit()
        return True

    except Exception as e:
        logger.error(f"Error in extract processing: {str(e)}")
        extract_version.status = "failed"
        extract_version.error = str(e)
        pipeline.update_pipeline_status()
        db.commit()
        return False


async def process_merge(
    extract_version_ids: List[UUID],
    merge_version_id: UUID,
    config: ConfigManager,
    db: Session,
) -> bool:
    try:
        logger.info(f"Starting merge for {len(extract_version_ids)} extract versions")

        merge_version = (
            db.query(MergeVersion)
            .filter(MergeVersion.version_id == merge_version_id)
            .first()
        )
        extract_versions = (
            db.query(ExtractVersion)
            .filter(ExtractVersion.version_id.in_(extract_version_ids))
            .all()
        )
        pipeline = merge_version.pipeline

        # Verify dependencies
        if not pipeline.can_start_stage(PipelineStage.MERGE):
            logger.error("Cannot start merge - extract stage not completed")
            merge_version.status = "failed"
            merge_version.error = "Extract stage not completed"
            db.commit()
            return False

        pipeline.stage = PipelineStage.MERGE
        pipeline.status = PipelineStatus.RUNNING
        db.commit()

        merge_processor = MergeProcessor(extract_versions, merge_version, config)
        merge_result = merge_processor.process()

        if not merge_result.success:
            merge_version.status = merge_result.status
            merge_version.error = merge_result.error
            pipeline.update_pipeline_status()
            db.commit()
            return False

        merge_version.status = merge_result.status
        pipeline.update_pipeline_status()
        db.commit()
        return True

    except Exception as e:
        logger.error(f"Error in merge processing: {str(e)}")
        merge_version.status = "failed"
        merge_version.error = str(e)
        pipeline.update_pipeline_status()
        db.commit()
        return False


async def process_group(
    merge_version_id: UUID, group_version_id: UUID, config: ConfigManager, db: Session
) -> bool:
    try:
        logger.info(f"Starting group processing for merge version {merge_version_id}")

        merge_version = (
            db.query(MergeVersion)
            .filter(MergeVersion.version_id == merge_version_id)
            .first()
        )
        group_version = (
            db.query(GroupVersion)
            .filter(GroupVersion.version_id == group_version_id)
            .first()
        )
        pipeline = group_version.pipeline

        # Verify dependencies
        if not pipeline.can_start_stage(PipelineStage.GROUP):
            logger.error("Cannot start group - merge stage not completed")
            group_version.status = "failed"
            group_version.error = "Merge stage not completed"
            db.commit()
            return False

        pipeline.stage = PipelineStage.GROUP
        pipeline.status = PipelineStatus.RUNNING
        db.commit()

        group_processor = GroupProcessor(merge_version, group_version, config)
        group_result = group_processor.process()

        if not group_result.success:
            group_version.status = group_result.status
            group_version.error = group_result.error
            pipeline.update_pipeline_status()
            db.commit()
            return False

        group_version.status = group_result.status
        pipeline.update_pipeline_status()
        db.commit()
        return True

    except Exception as e:
        logger.error(f"Error in group processing: {str(e)}")
        group_version.status = "failed"
        group_version.error = str(e)
        pipeline.update_pipeline_status()
        db.commit()
        return False


async def process_ontology(
    merge_version_id: UUID,
    group_version_id: UUID,
    ontology_version_id: UUID,
    config: ConfigManager,
    db: Session,
) -> bool:
    try:
        logger.info(f"Starting ontology for group version {group_version_id}")

        merge_version = (
            db.query(MergeVersion)
            .filter(MergeVersion.version_id == merge_version_id)
            .first()
        )
        group_version = (
            db.query(GroupVersion)
            .filter(GroupVersion.version_id == group_version_id)
            .first()
        )
        ontology_version = (
            db.query(OntologyVersion)
            .filter(OntologyVersion.version_id == ontology_version_id)
            .first()
        )
        pipeline = ontology_version.pipeline

        # Verify dependencies
        if not pipeline.can_start_stage(PipelineStage.ONTOLOGY):
            logger.error("Cannot start ontology - dependencies not met")
            ontology_version.status = "failed"
            ontology_version.error = "Previous stages not completed"
            db.commit()
            return False

        pipeline.stage = PipelineStage.ONTOLOGY
        pipeline.status = PipelineStatus.RUNNING
        db.commit()

        ontology_processor = OntologyProcessor(
            merge_version, group_version, ontology_version, config
        )
        ontology_result = ontology_processor.process()

        if not ontology_result.success:
            ontology_version.status = ontology_result.status
            ontology_version.error = ontology_result.error
            pipeline.update_pipeline_status()
            db.commit()
            return False

        ontology_version.status = ontology_result.status
        pipeline.update_pipeline_status()
        db.commit()
        return True

    except Exception as e:
        logger.error(f"Error in ontology processing: {str(e)}")
        ontology_version.status = "failed"
        ontology_version.error = str(e)
        pipeline.update_pipeline_status()
        db.commit()
        return False


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

    current_merge = (
        db.query(MergeVersion)
        .filter(MergeVersion.pipeline_id == pipeline_id)
        .order_by(MergeVersion.version_number.desc())
        .first()
    )

    current_group = (
        db.query(GroupVersion)
        .filter(GroupVersion.pipeline_id == pipeline_id)
        .order_by(GroupVersion.version_number.desc())
        .first()
    )

    current_ontology = (
        db.query(OntologyVersion)
        .filter(OntologyVersion.pipeline_id == pipeline_id)
        .order_by(OntologyVersion.version_number.desc())
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
        current_merge_id=current_merge.version_id if current_merge else None,
        current_group_id=current_group.version_id if current_group else None,
        current_ontology_id=current_ontology.version_id if current_ontology else None,
        current_graph_id=current_graph.version_id if current_graph else None,
        latest_parse_version_id=current_parse.version_id if current_parse else None,
        latest_extract_version_id=(
            current_extract.version_id if current_extract else None
        ),
        latest_merge_version_id=current_merge.version_id if current_merge else None,
        latest_group_version_id=current_group.version_id if current_group else None,
        latest_ontology_version_id=(
            current_ontology.version_id if current_ontology else None
        ),
    )


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/pipeline/{pipeline_id}/parse/{version_id}",
    response_model=ProcessingVersionBase,
)
async def get_parse_version(
    tenant_id: UUID,
    domain_id: UUID,
    pipeline_id: UUID,
    version_id: UUID,
    db: Session = Depends(get_db),
):
    """Get details of a specific parse version"""
    version = (
        db.query(ParseVersion)
        .join(ProcessingPipeline)
        .join(Domain)
        .filter(
            Domain.tenant_id == tenant_id,
            ProcessingPipeline.domain_id == domain_id,
            ProcessingPipeline.pipeline_id == pipeline_id,
            ParseVersion.version_id == version_id,
        )
        .first()
    )

    if not version:
        raise HTTPException(status_code=404, detail="Parse version not found")

    return version


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/pipeline/{pipeline_id}/extract/{version_id}",
    response_model=ProcessingVersionBase,
)
async def get_extract_version(
    tenant_id: UUID,
    domain_id: UUID,
    pipeline_id: UUID,
    version_id: UUID,
    db: Session = Depends(get_db),
):
    """Get details of a specific extract version"""
    version = (
        db.query(ExtractVersion)
        .join(ProcessingPipeline)
        .join(Domain)
        .filter(
            Domain.tenant_id == tenant_id,
            ProcessingPipeline.domain_id == domain_id,
            ProcessingPipeline.pipeline_id == pipeline_id,
            ExtractVersion.version_id == version_id,
        )
        .first()
    )

    if not version:
        raise HTTPException(status_code=404, detail="Extract version not found")

    return version


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/pipeline/{pipeline_id}/merge/{version_id}",
    response_model=ProcessingVersionBase,
)
async def get_merge_version(
    tenant_id: UUID,
    domain_id: UUID,
    pipeline_id: UUID,
    version_id: UUID,
    db: Session = Depends(get_db),
):
    """Get details of a specific merge version"""
    version = (
        db.query(MergeVersion)
        .join(ProcessingPipeline)
        .join(Domain)
        .filter(
            Domain.tenant_id == tenant_id,
            ProcessingPipeline.domain_id == domain_id,
            ProcessingPipeline.pipeline_id == pipeline_id,
            MergeVersion.version_id == version_id,
        )
        .first()
    )

    if not version:
        raise HTTPException(status_code=404, detail="Merge version not found")

    return version


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/pipeline/{pipeline_id}/group/{version_id}",
    response_model=ProcessingVersionBase,
)
async def get_group_version(
    tenant_id: UUID,
    domain_id: UUID,
    pipeline_id: UUID,
    version_id: UUID,
    db: Session = Depends(get_db),
):
    """Get details of a specific group version"""
    version = (
        db.query(GroupVersion)
        .join(ProcessingPipeline)
        .join(Domain)
        .filter(
            Domain.tenant_id == tenant_id,
            ProcessingPipeline.domain_id == domain_id,
            ProcessingPipeline.pipeline_id == pipeline_id,
            GroupVersion.version_id == version_id,
        )
        .first()
    )

    if not version:
        raise HTTPException(status_code=404, detail="Group version not found")

    return version


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/pipeline/{pipeline_id}/ontology/{version_id}",
    response_model=ProcessingVersionBase,
)
async def get_ontology_version(
    tenant_id: UUID,
    domain_id: UUID,
    pipeline_id: UUID,
    version_id: UUID,
    db: Session = Depends(get_db),
):
    """Get details of a specific ontology version"""
    version = (
        db.query(OntologyVersion)
        .join(ProcessingPipeline)
        .join(Domain)
        .filter(
            Domain.tenant_id == tenant_id,
            ProcessingPipeline.domain_id == domain_id,
            ProcessingPipeline.pipeline_id == pipeline_id,
            OntologyVersion.version_id == version_id,
        )
        .first()
    )

    if not version:
        raise HTTPException(status_code=404, detail="Ontology version not found")

    return version


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/versions/{domain_version}/prompts/{stage}"
)
async def get_stage_prompts(
    tenant_id: UUID,
    domain_id: UUID,
    domain_version: int,
    stage: PipelineStage,
    db: Session = Depends(get_db),
):
    """Get current prompts for a specific processing stage"""
    domain_version_obj = (
        db.query(DomainVersion)
        .join(Domain)
        .filter(
            Domain.tenant_id == tenant_id,
            DomainVersion.domain_id == domain_id,
            DomainVersion.version_number == domain_version,
        )
        .first()
    )
    if not domain_version_obj:
        raise HTTPException(status_code=404, detail="Domain version not found")

    # Get pipeline
    pipeline = domain_version_obj.processing_pipeline
    if not pipeline:
        raise HTTPException(status_code=404, detail="No processing pipeline found")

    # Map stages to version models
    version_model = {
        PipelineStage.PARSE: ParseVersion,
        PipelineStage.EXTRACT: ExtractVersion,
        PipelineStage.MERGE: MergeVersion,
        PipelineStage.GROUP: GroupVersion,
        PipelineStage.ONTOLOGY: OntologyVersion,
    }.get(stage)

    if not version_model:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid stage. Must be one of: {', '.join([s.value for s in PipelineStage if s not in [PipelineStage.NOT_STARTED, PipelineStage.VALIDATE, PipelineStage.COMPLETED]])}",
        )

    # Get latest version
    latest_version = (
        db.query(version_model)
        .filter(version_model.pipeline_id == pipeline.pipeline_id)
        .order_by(version_model.version_number.desc())
        .first()
    )

    if not latest_version:
        return get_default_prompts(stage.value.lower())

    prompts = {
        "system_prompt": latest_version.system_prompt,
        "custom_instructions": latest_version.custom_instructions,
    }

    # Add stage-specific prompts
    stage_prompts = {
        PipelineStage.PARSE: {
            "readability_prompt": latest_version.readability_prompt,
            "convert_prompt": latest_version.convert_prompt,
        },
        PipelineStage.EXTRACT: {
            "initial_entity_extraction_prompt": latest_version.initial_entity_extraction_prompt,
            "iterative_extract_entities_prompt": latest_version.iterative_extract_entities_prompt,
            "entity_details_prompt": latest_version.entity_details_prompt,
        },
        PipelineStage.MERGE: {
            "entity_details_prompt": latest_version.entity_details_prompt,
            "entity_merge_prompt": latest_version.entity_merge_prompt,
        },
        PipelineStage.GROUP: {
            "entity_group_prompt": latest_version.entity_group_prompt,
        },
        PipelineStage.ONTOLOGY: {
            "ontology_prompt": latest_version.ontology_prompt,
        },
    }

    prompts.update(stage_prompts.get(stage, {}))
    return prompts


@router.put(
    "/tenants/{tenant_id}/domains/{domain_id}/versions/{domain_version}/prompts/{stage}"
)
async def update_stage_prompts(
    tenant_id: UUID,
    domain_id: UUID,
    domain_version: int,
    stage: PipelineStage,
    prompts: Union[
        ParsePrompts, ExtractPrompts, MergePrompts, GroupPrompts, OntologyPrompts
    ],
    db: Session = Depends(get_db),
):
    """Update prompts for a specific processing stage"""
    domain_version_obj = (
        db.query(DomainVersion)
        .join(Domain)
        .filter(
            Domain.tenant_id == tenant_id,
            DomainVersion.domain_id == domain_id,
            DomainVersion.version_number == domain_version,
        )
        .first()
    )
    if not domain_version_obj:
        raise HTTPException(status_code=404, detail="Domain version not found")
    if domain_version_obj.status != DomainVersionStatus.DRAFT:
        raise HTTPException(
            status_code=400, detail="Can only update prompts in DRAFT status"
        )

    # Get or create pipeline
    pipeline = domain_version_obj.processing_pipeline
    if not pipeline:
        pipeline = ProcessingPipeline(domain_id=domain_id)
        domain_version_obj.processing_pipeline = pipeline
        db.add(pipeline)
        db.commit()

    # Map stages to version models
    version_model = {
        PipelineStage.PARSE: ParseVersion,
        PipelineStage.EXTRACT: ExtractVersion,
        PipelineStage.MERGE: MergeVersion,
        PipelineStage.GROUP: GroupVersion,
        PipelineStage.ONTOLOGY: OntologyVersion,
    }.get(stage)

    if not version_model:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid stage. Must be one of: {', '.join([s.value for s in PipelineStage if s not in [PipelineStage.NOT_STARTED, PipelineStage.VALIDATE, PipelineStage.COMPLETED]])}",
        )

    # Required prompts for each stage
    required_prompts = {
        PipelineStage.PARSE: [
            "system_prompt",
            "readability_prompt",
            "convert_prompt",
            "custom_instructions",
        ],
        PipelineStage.EXTRACT: [
            "system_prompt",
            "initial_entity_extraction_prompt",
            "iterative_extract_entities_prompt",
            "entity_details_prompt",
            "custom_instructions",
        ],
        PipelineStage.MERGE: [
            "system_prompt",
            "entity_details_prompt",
            "entity_merge_prompt",
            "custom_instructions",
        ],
        PipelineStage.GROUP: [
            "system_prompt",
            "entity_group_prompt",
            "custom_instructions",
        ],
        PipelineStage.ONTOLOGY: [
            "system_prompt",
            "ontology_prompt",
            "custom_instructions",
        ],
    }

    # Validate required prompts
    missing_prompts = [p for p in required_prompts[stage] if p not in prompts]
    if missing_prompts:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required prompts for {stage.value}: {', '.join(missing_prompts)}",
        )

    # Create new version with next version number
    next_version_number = get_next_version_number(
        db, pipeline.pipeline_id, version_model
    )

    # Create new version with the provided prompts
    new_version = version_model(
        pipeline_id=pipeline.pipeline_id,
        version_number=next_version_number,
        **prompts,
    )

    db.add(new_version)
    db.commit()

    return {
        "message": f"{stage.value} prompts updated successfully",
        "version_number": next_version_number,
    }


@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/versions/{domain_version}/validate",
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_validate_stage(
    tenant_id: UUID,
    domain_id: UUID,
    domain_version: int,
    db: Session = Depends(get_db),
):
    """Set pipeline status to validate stage"""
    domain_version_obj = (
        db.query(DomainVersion)
        .join(Domain)
        .filter(
            Domain.tenant_id == tenant_id,
            DomainVersion.domain_id == domain_id,
            DomainVersion.version_number == domain_version,
        )
        .first()
    )

    if not domain_version_obj:
        raise HTTPException(status_code=404, detail="Domain version not found")

    pipeline = domain_version_obj.processing_pipeline
    if not pipeline:
        raise HTTPException(
            status_code=404,
            detail="No processing pipeline found for this domain version",
        )

    pipeline.stage = PipelineStage.VALIDATE
    pipeline.status = PipelineStatus.RUNNING
    db.commit()

    return {
        "message": "Pipeline moved to validate stage",
        "pipeline_id": pipeline.pipeline_id,
    }


@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/versions/{domain_version}/complete",
    status_code=status.HTTP_202_ACCEPTED,
)
async def complete_pipeline(
    tenant_id: UUID,
    domain_id: UUID,
    domain_version: int,
    db: Session = Depends(get_db),
):
    """Mark pipeline as completed"""
    domain_version_obj = (
        db.query(DomainVersion)
        .join(Domain)
        .filter(
            Domain.tenant_id == tenant_id,
            DomainVersion.domain_id == domain_id,
            DomainVersion.version_number == domain_version,
        )
        .first()
    )

    if not domain_version_obj:
        raise HTTPException(status_code=404, detail="Domain version not found")

    pipeline = domain_version_obj.processing_pipeline
    if not pipeline:
        raise HTTPException(
            status_code=404,
            detail="No processing pipeline found for this domain version",
        )

    pipeline.stage = PipelineStage.COMPLETED
    pipeline.status = PipelineStatus.COMPLETED
    db.commit()

    return {
        "message": "Pipeline marked as completed",
        "pipeline_id": pipeline.pipeline_id,
    }


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/pipeline/{pipeline_id}/{stage}/{version_id}/content"
)
async def get_processing_output_content(
    tenant_id: UUID,
    domain_id: UUID,
    pipeline_id: UUID,
    stage: str,
    version_id: UUID,
    db: Session = Depends(get_db),
):
    """Get the output content for a specific processing version"""
    # Map stages to version models
    version_model = {
        "parse": ParseVersion,
        "extract": ExtractVersion,
        "merge": MergeVersion,
        "group": GroupVersion,
        "ontology": OntologyVersion,
    }.get(stage)

    if not version_model:
        raise HTTPException(status_code=400, detail="Invalid stage")

    version = (
        db.query(version_model)
        .join(ProcessingPipeline)
        .join(Domain)
        .filter(
            Domain.tenant_id == tenant_id,
            ProcessingPipeline.domain_id == domain_id,
            ProcessingPipeline.pipeline_id == pipeline_id,
            version_model.version_id == version_id,
        )
        .first()
    )

    if not version:
        raise HTTPException(status_code=404, detail=f"{stage} version not found")

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
    """Get detailed status for a specific pipeline stage"""
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


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/pipeline/{pipeline_id}/stage/{stage}/dependencies",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=StageDependenciesResponse,
)
async def get_stage_dependencies(
    tenant_id: UUID,
    domain_id: UUID,
    pipeline_id: UUID,
    stage: PipelineStage,
    db: Session = Depends(get_db),
):
    """Get dependency information for a specific stage"""
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

    dependencies = {
        PipelineStage.PARSE: [],
        PipelineStage.EXTRACT: [
            {
                "stage": PipelineStage.PARSE,
                "completed": pipeline.get_stage_status(PipelineStage.PARSE)
                == PipelineStatus.COMPLETED,
            }
        ],
        PipelineStage.MERGE: [
            {
                "stage": PipelineStage.EXTRACT,
                "completed": pipeline.get_stage_status(PipelineStage.EXTRACT)
                == PipelineStatus.COMPLETED,
            }
        ],
        PipelineStage.GROUP: [
            {
                "stage": PipelineStage.MERGE,
                "completed": pipeline.get_stage_status(PipelineStage.MERGE)
                == PipelineStatus.COMPLETED,
            }
        ],
        PipelineStage.ONTOLOGY: [
            {
                "stage": PipelineStage.MERGE,
                "completed": pipeline.get_stage_status(PipelineStage.MERGE)
                == PipelineStatus.COMPLETED,
            },
            {
                "stage": PipelineStage.GROUP,
                "completed": pipeline.get_stage_status(PipelineStage.GROUP)
                == PipelineStatus.COMPLETED,
            },
        ],
    }

    return {
        "stage": stage,
        "dependencies": dependencies.get(stage, []),
        "can_start": pipeline.can_start_stage(stage),
    }


@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/pipeline/{pipeline_id}/stage/{stage}/start-batch",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=StageBatchResponse,
)
async def start_stage_batch(
    tenant_id: UUID,
    domain_id: UUID,
    pipeline_id: UUID,
    stage: PipelineStage,
    version_ids: List[UUID],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Start multiple processes for a stage"""
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

    if not pipeline.can_start_stage(stage):
        raise HTTPException(
            status_code=400, detail=f"Cannot start {stage} - dependencies not met"
        )

    config = ConfigManager(db, str(tenant_id), str(domain_id))
    started_versions: List[StartedVersionInfo] = []

    try:
        if stage == PipelineStage.PARSE:
            for file_version_id in version_ids:
                parse_version = ParseVersion(
                    pipeline_id=pipeline.pipeline_id,
                    version_number=get_next_version_number(
                        db, pipeline.pipeline_id, ParseVersion
                    ),
                    input_file_version_id=file_version_id,
                    status="processing",
                    system_prompt=PARSE_SYSTEM_PROMPT,
                    readability_prompt=CHECK_READABILITY_PROMPT,
                    convert_prompt=CONVERT_TO_MARKDOWN_PROMPT,
                    custom_instructions=[],
                    output_dir="",
                    output_path="",
                )
                db.add(parse_version)
                db.commit()

                output_dir = os.path.join(
                    config.get("processing_dir", "processing_output"),
                    str(pipeline.domain_id),
                    str(pipeline.domain_version.version_number),
                    "parse",
                    str(parse_version.version_number),
                    str(parse_version.input_file_version_id),
                )
                parse_version.output_dir = output_dir
                parse_version.output_path = f"{output_dir}/output.md"
                db.commit()

                background_tasks.add_task(
                    process_parse,
                    file_version_id=file_version_id,
                    parse_version_id=parse_version.version_id,
                    config=config,
                    db=db,
                )

                started_versions.append(
                    StartedVersionInfo(
                        message="Parse started",
                        pipeline_id=pipeline.pipeline_id,
                        version_id=parse_version.version_id,
                        input_version_ids=[file_version_id],
                    )
                )

        elif stage == PipelineStage.EXTRACT:
            for parse_version_id in version_ids:
                extract_version = ExtractVersion(
                    pipeline_id=pipeline.pipeline_id,
                    version_number=get_next_version_number(
                        db, pipeline.pipeline_id, ExtractVersion
                    ),
                    input_parse_version_id=parse_version_id,
                    status="processing",
                    system_prompt=EXTRACT_SYSTEM_PROMPT,
                    initial_entity_extraction_prompt=INITIAL_ENTITY_EXTRACTION_PROMPT,
                    iterative_extract_entities_prompt=ITERATIVE_ENTITY_EXTRACTION_PROMPT,
                    entity_details_prompt=EXTRACT_ENTITY_DETAILS_PROMPT,
                    custom_instructions=[],
                    output_dir="",
                    output_path="",
                )
                db.add(extract_version)
                db.commit()

                output_dir = os.path.join(
                    config.get("processing_dir", "processing_output"),
                    str(pipeline.domain_id),
                    str(pipeline.domain_version.version_number),
                    "extract",
                    str(extract_version.version_number),
                )
                extract_version.output_dir = output_dir
                extract_version.output_path = f"{output_dir}/output.json"
                db.commit()

                background_tasks.add_task(
                    process_extract,
                    parse_version_id=parse_version_id,
                    extract_version_id=extract_version.version_id,
                    config=config,
                    db=db,
                )

                started_versions.append(
                    StartedVersionInfo(
                        message="Extract started",
                        pipeline_id=pipeline.pipeline_id,
                        version_id=extract_version.version_id,
                        input_version_ids=[parse_version_id],
                    )
                )

        elif stage == PipelineStage.GROUP:
            merge_version_id = version_ids[0] if version_ids else None
            if not merge_version_id:
                raise HTTPException(
                    status_code=400, detail="Merge version ID required for group stage"
                )

            group_version = GroupVersion(
                pipeline_id=pipeline.pipeline_id,
                version_number=get_next_version_number(
                    db, pipeline.pipeline_id, GroupVersion
                ),
                input_merge_version_id=merge_version_id,
                status="processing",
                system_prompt=GROUP_SYSTEM_PROMPT,
                entity_group_prompt=GROUP_PROMPT,
                custom_instructions=[],
                output_dir="",
                output_path="",
            )
            db.add(group_version)
            db.commit()

            output_dir = os.path.join(
                config.get("processing_dir", "processing_output"),
                str(pipeline.domain_id),
                str(pipeline.domain_version.version_number),
                "group",
                str(group_version.version_number),
            )
            group_version.output_dir = output_dir
            group_version.output_path = f"{output_dir}/output.json"
            db.commit()

            background_tasks.add_task(
                process_group,
                merge_version_id=merge_version_id,
                group_version_id=group_version.version_id,
                config=config,
                db=db,
            )

            started_versions.append(
                StartedVersionInfo(
                    message="Group started",
                    pipeline_id=pipeline.pipeline_id,
                    version_id=group_version.version_id,
                    input_version_ids=[merge_version_id],
                )
            )

        elif stage == PipelineStage.ONTOLOGY:
            if len(version_ids) != 2:
                raise HTTPException(
                    status_code=400,
                    detail="Both merge and group version IDs required for ontology stage",
                )

            merge_version_id, group_version_id = version_ids

            ontology_version = OntologyVersion(
                pipeline_id=pipeline.pipeline_id,
                version_number=get_next_version_number(
                    db, pipeline.pipeline_id, OntologyVersion
                ),
                input_merge_version_id=merge_version_id,
                input_group_version_id=group_version_id,
                status="processing",
                system_prompt=ONTOLOGY_SYSTEM_PROMPT,
                ontology_prompt=ONTOLOGY_PROMPT,
                custom_instructions=[],
                output_dir="",
                output_path="",
            )
            db.add(ontology_version)
            db.commit()

            output_dir = os.path.join(
                config.get("processing_dir", "processing_output"),
                str(pipeline.domain_id),
                str(pipeline.domain_version.version_number),
                "ontology",
                str(ontology_version.version_number),
            )
            ontology_version.output_dir = output_dir
            ontology_version.output_path = f"{output_dir}/output.json"
            db.commit()

            background_tasks.add_task(
                process_ontology,
                merge_version_id=merge_version_id,
                group_version_id=group_version_id,
                ontology_version_id=ontology_version.version_id,
                config=config,
                db=db,
            )

            started_versions.append(
                StartedVersionInfo(
                    message="Ontology started",
                    pipeline_id=pipeline.pipeline_id,
                    version_id=ontology_version.version_id,
                    input_version_ids=[merge_version_id, group_version_id],
                )
            )

        return StageBatchResponse(
            message=f"Started {stage} processing", started_versions=started_versions
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error in start_stage_batch: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to start {stage} processing: {str(e)}"
        )


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/pipeline/{pipeline_id}/stage/{stage}/versions",
    response_model=List[StageVersionInfo],
)
async def get_stage_versions(
    tenant_id: UUID,
    domain_id: UUID,
    pipeline_id: UUID,
    stage: PipelineStage,
    db: Session = Depends(get_db),
):
    """Get all versions for a specific stage"""
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

    versions = pipeline.get_stage_versions(stage)
    return versions


@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/versions/{domain_version}/pipeline/start",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=PipelineActionResponse,
    responses={
        400: {"model": PipelineErrorResponse},
        404: {"model": PipelineErrorResponse},
    },
)
async def start_pipeline_processing(
    tenant_id: UUID,
    domain_id: UUID,
    domain_version: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    pipeline_config: Optional[PipelineStartRequest] = None,
):
    """Start the full processing pipeline"""
    try:
        domain_version_obj = (
            db.query(DomainVersion)
            .join(Domain)
            .filter(
                Domain.tenant_id == tenant_id,
                DomainVersion.domain_id == domain_id,
                DomainVersion.version_number == domain_version,
            )
            .first()
        )

        if not domain_version_obj:
            raise HTTPException(
                status_code=404,
                detail=PipelineErrorResponse(
                    detail="Domain version not found",
                    error_code="DOMAIN_VERSION_NOT_FOUND",
                ).dict(),
            )

        # Create or get pipeline
        pipeline = domain_version_obj.processing_pipeline
        if not pipeline:
            pipeline = ProcessingPipeline(domain_id=domain_id)
            domain_version_obj.processing_pipeline = pipeline
            db.add(pipeline)
            db.commit()

        # Get files
        files = (
            db.query(DomainVersionFile)
            .filter(
                DomainVersionFile.domain_id == domain_id,
                DomainVersionFile.version_number == domain_version,
            )
            .all()
        )

        if not files:
            raise HTTPException(
                status_code=400,
                detail=PipelineErrorResponse(
                    detail="No files found for processing", error_code="NO_FILES_FOUND"
                ).dict(),
            )

        # Set up orchestrator with SessionLocal
        config = ConfigManager(db, str(tenant_id), str(domain_id))
        from ..core.database import SessionLocal  # Import the session factory

        orchestrator = PipelineOrchestrator(
            SessionLocal=SessionLocal, config=config, pipeline_id=pipeline.pipeline_id
        )

        # Start pipeline in background
        file_version_ids = [file.file_version_id for file in files]

        async def run_pipeline():
            try:
                await orchestrator.process_pipeline(file_version_ids)
            except Exception as e:
                logger.error(f"Pipeline processing failed: {str(e)}")

        background_tasks.add_task(run_pipeline)

        logger.info(f"Pipeline started with {len(file_version_ids)} files")
        return PipelineActionResponse(
            message="Pipeline processing started", pipeline_id=pipeline.pipeline_id
        )

    except Exception as e:
        logger.error(f"Error starting pipeline: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=PipelineErrorResponse(
                detail=f"Failed to start pipeline: {str(e)}",
                error_code="PIPELINE_START_ERROR",
            ).dict(),
        )


@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/versions/{domain_version}/pipeline/stop",
    status_code=status.HTTP_200_OK,
    response_model=PipelineActionResponse,
    responses={404: {"model": PipelineErrorResponse}},
)
async def stop_pipeline_processing(
    tenant_id: UUID,
    domain_id: UUID,
    domain_version: int,
    db: Session = Depends(get_db),
):
    """Stop the processing pipeline"""
    domain_version_obj = (
        db.query(DomainVersion)
        .join(Domain)
        .filter(
            Domain.tenant_id == tenant_id,
            DomainVersion.domain_id == domain_id,
            DomainVersion.version_number == domain_version,
        )
        .first()
    )

    if not domain_version_obj or not domain_version_obj.processing_pipeline:
        raise HTTPException(
            status_code=404,
            detail=PipelineErrorResponse(
                detail="Pipeline not found", error_code="PIPELINE_NOT_FOUND"
            ).dict(),
        )

    pipeline = domain_version_obj.processing_pipeline
    pipeline.status = PipelineStatus.FAILED
    pipeline.error = "Pipeline stopped by user"
    db.commit()

    return PipelineActionResponse(
        message="Pipeline processing stopped", pipeline_id=pipeline.pipeline_id
    )
