from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, status
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime
from typing import List, Union
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
    file_version_id: UUID,
    parse_version_id: UUID,
    config: ConfigManager,
    db: Session,
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
        pipeline.status = PipelineStatus.RUNNING
        pipeline.stage = PipelineStage.PARSE
        db.commit()

        parse_processor = ParseProcessor(file_version, parse_version, config)
        parse_result = parse_processor.process()

        if not parse_result.success:
            logger.error(f"Parse failed: {parse_result.error}")
            parse_version.status = "failed"
            parse_version.error = parse_result.error
            pipeline.status = PipelineStatus.FAILED
            db.commit()
            return False

        parse_version.status = "completed"
        pipeline.status = PipelineStatus.COMPLETED
        db.commit()
        logger.info("Parse completed successfully")
        return True

    except Exception as e:
        logger.error(f"Error in parse processing: {str(e)}", exc_info=True)
        parse_version.status = "failed"
        parse_version.error = str(e)
        pipeline.status = PipelineStatus.FAILED
        db.commit()
        return False


async def process_extract(
    parse_version_id: UUID,
    extract_version_id: UUID,
    config: ConfigManager,
    db: Session,
) -> bool:
    """Process a single file through entity extraction stage"""
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
        pipeline.status = PipelineStatus.RUNNING
        pipeline.stage = PipelineStage.EXTRACT
        db.commit()

        # Process entities with base prompt from extract version
        extract_processor = ExtractProcessor(parse_version, extract_version, config)
        extract_result = extract_processor.process()

        if not extract_result.success:
            extract_version.status = extract_result.status
            extract_version.error = extract_result.error
            pipeline.status = PipelineStatus.FAILED
            db.commit()
            return False

        # Update extract version with output information
        extract_version.status = extract_result.status
        db.commit()
        return True

    except Exception as e:
        logger.error(
            f"Error in extract processing for parse version {parse_version.version_id}: {str(e)}"
        )
        extract_version.status = "failed"
        extract_version.error = str(e)
        pipeline.status = PipelineStatus.FAILED
        db.commit()
        return False


async def process_merge(
    extract_version_ids: List[UUID],
    merge_version_id: UUID,
    config: ConfigManager,
    db: Session,
) -> bool:
    """process multiple extract version through merging stage"""
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
        pipeline.status = PipelineStatus.RUNNING
        pipeline.stage = PipelineStage.MERGE
        db.commit()

        # Process entities with base prompt from extract version
        merge_processor = MergeProcessor(extract_versions, merge_version, config)
        merge_result = merge_processor.process()

        if not merge_result.success:
            merge_version.status = merge_result.status
            merge_version.error = merge_result.error
            pipeline.status = PipelineStatus.FAILED
            db.commit()
            return False

        # Update extract version with output information
        merge_version.status = merge_result.status
        db.commit()
        return True

    except Exception as e:
        logger.error(
            f"Error in merge processing for merge version {merge_version.version_id}: {str(e)}"
        )
        merge_version.status = "failed"
        merge_version.error = str(e)
        pipeline.status = PipelineStatus.FAILED
        db.commit()
        return False


async def process_group(
    merge_version_id: UUID,
    group_version_id: UUID,
    config: ConfigManager,
    db: Session,
) -> bool:
    """Process entity grouping stage"""
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
        pipeline.status = PipelineStatus.RUNNING
        pipeline.stage = PipelineStage.GROUP
        db.commit()

        # Process entities with base prompt from extract version
        group_processor = GroupProcessor(merge_version, group_version, config)
        group_result = group_processor.process()

        if not group_result.success:
            group_version.status = group_result.status
            group_version.error = group_result.error
            pipeline.status = PipelineStatus.FAILED
            db.commit()
            return False

        # Update extract version with output information
        group_version.status = group_result.status
        db.commit()
        return True

    except Exception as e:
        logger.error(
            f"Error in extract processing for merge version {merge_version.version_id}: {str(e)}"
        )
        group_version.status = "failed"
        group_version.error = str(e)
        pipeline.status = PipelineStatus.FAILED
        db.commit()
        return False


async def process_ontology(
    merge_version_id: UUID,
    group_version_id: UUID,
    ontology_version_id: UUID,
    config: ConfigManager,
    db: Session,
) -> bool:
    """Process ontology generation stage"""
    try:
        logger.info(
            f"Starting ontology for group version {group_version_id} and ontology version {ontology_version_id}"
        )

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
        pipeline.status = PipelineStatus.RUNNING
        pipeline.stage = PipelineStage.ONTOLOGY
        db.commit()

        # Process entities with base prompt from extract version
        ontology_processor = OntologyProcessor(
            merge_version, group_version, ontology_version, config
        )
        ontology_result = ontology_processor.process()

        if not ontology_result.success:
            ontology_version.status = ontology_result.status
            ontology_version.error = ontology_result.error
            pipeline.status = PipelineStatus.FAILED
            db.commit()
            return False

        # Update extract version with output information
        group_version.status = ontology_version.status
        db.commit()
        return True

    except Exception as e:
        logger.error(
            f"Error in group or merge processing for ontology version merge -> {merge_version.version_id}, group -> {group_version.version_id}: {str(e)}"
        )
        ontology_version.status = "failed"
        ontology_version.error = str(e)
        pipeline.status = PipelineStatus.FAILED
        db.commit()
        return False


# API Endpoints
@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/versions/{domain_version}/files/{file_version_id}/parse",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=StageStartResponse,
)
async def start_parse_processing(
    tenant_id: UUID,
    domain_id: UUID,
    domain_version: int,
    file_version_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Start PDF parsing for a single file version"""
    # Check domain version exists and is in DRAFT
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
            status_code=400,
            detail="Can only parse files for domain versions in DRAFT status",
        )

    config = ConfigManager(db, str(tenant_id), str(domain_id))

    # Check file version exists
    file_version = (
        db.query(FileVersion)
        .join(File)
        .join(Domain)
        .filter(
            Domain.tenant_id == tenant_id,
            Domain.domain_id == domain_id,
            FileVersion.file_version_id == file_version_id,
        )
        .first()
    )

    if not file_version:
        raise HTTPException(status_code=404, detail="File version not found")

    # Get or create processing pipeline for this domain version
    pipeline = domain_version_obj.processing_pipeline
    if not pipeline:
        pipeline = ProcessingPipeline(domain_id=domain_id)
        domain_version_obj.processing_pipeline = pipeline
        db.add(pipeline)
        db.commit()

    # Create parse version
    parse_version = ParseVersion(
        pipeline_id=pipeline.pipeline_id,
        version_number=len(pipeline.parse_versions) + 1,
        system_prompt=PARSE_SYSTEM_PROMPT,
        readability_prompt=CHECK_READABILITY_PROMPT,
        convert_prompt=CONVERT_TO_MARKDOWN_PROMPT,
        input_file_version_id=file_version_id,
        output_dir="",
        output_path="",
        status="processing",
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

    # Start processing
    background_tasks.add_task(
        process_parse,
        file_version_id=file_version.file_version_id,
        parse_version_id=parse_version.version_id,
        config=config,
        db=db,
    )

    return {
        "message": "PDF parsing started",
        "pipeline_id": pipeline.pipeline_id,
        "version_id": parse_version.version_id,
        "input_version_ids": [file_version_id],
    }


@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/versions/{domain_version}/parse/{parse_version_id}/extract",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=StageStartResponse,
)
async def start_extract_processing(
    tenant_id: UUID,
    domain_id: UUID,
    domain_version: int,
    parse_version_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Start entity extraction from parse output"""
    # Check domain version exists and is in DRAFT
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
            status_code=400,
            detail="Can only extract entities for domain versions in DRAFT status",
        )

    config = ConfigManager(db, str(tenant_id), str(domain_id))

    # Check parse version exists and completed
    parse_version = (
        db.query(ParseVersion)
        .filter(
            ParseVersion.version_id == parse_version_id,
            ParseVersion.status == "completed",
        )
        .first()
    )

    if not parse_version:
        raise HTTPException(
            status_code=404, detail="Parse version not found or not completed"
        )

    # Get pipeline
    pipeline = domain_version_obj.processing_pipeline
    if not pipeline:
        raise HTTPException(
            status_code=404,
            detail="No processing pipeline found for this domain version",
        )

    # Create extract version
    extract_version = ExtractVersion(
        pipeline_id=pipeline.pipeline_id,
        version_number=len(pipeline.extract_versions) + 1,
        input_parse_version_id=parse_version_id,
        system_prompt=EXTRACT_SYSTEM_PROMPT,
        initial_entity_extraction_prompt=INITIAL_ENTITY_EXTRACTION_PROMPT,
        iterative_extract_entities_prompt=ITERATIVE_ENTITY_EXTRACTION_PROMPT,
        entity_details_prompt=EXTRACT_ENTITY_DETAILS_PROMPT,
        output_dir="",
        output_path="",
        status="processing",
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

    # Start processing
    background_tasks.add_task(
        process_extract,
        parse_version.version_id,
        extract_version.version_id,
        config,
        db,
    )

    return {
        "message": "Entity extraction started",
        "pipeline_id": pipeline.pipeline_id,
        "version_id": extract_version.version_id,
        "input_version_ids": [parse_version_id],
    }


@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/versions/{domain_version}/merge",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=StageStartResponse,
)
async def start_merge_processing(
    tenant_id: UUID,
    domain_id: UUID,
    domain_version: int,
    merge_request: MergeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Start merging entities from specified extract versions"""
    # Check domain version exists and is in DRAFT
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
            status_code=400,
            detail="Can only merge entities for domain versions in DRAFT status",
        )

    # Get pipeline
    pipeline = domain_version_obj.processing_pipeline
    if not pipeline:
        raise HTTPException(
            status_code=404,
            detail="No processing pipeline found for this domain version",
        )

    # Verify all extract versions exist and are completed
    extract_versions = (
        db.query(ExtractVersion)
        .filter(
            ExtractVersion.version_id.in_(merge_request.extract_version_ids),
            ExtractVersion.status == "completed",
        )
        .all()
    )

    if len(extract_versions) != len(merge_request.extract_version_ids):
        raise HTTPException(
            status_code=404,
            detail="One or more extract versions not found or not completed",
        )

    config = ConfigManager(db, str(tenant_id), str(domain_id))

    # Create merge version
    merge_version = MergeVersion(
        pipeline_id=pipeline.pipeline_id,
        version_number=len(pipeline.merge_versions) + 1,
        input_extract_version_ids=merge_request.extract_version_ids,
        system_prompt=MERGE_SYSTEM_PROMPT,
        entity_merge_prompt=ENTITY_MERGE_PROMPT,
        entity_details_prompt=MERGE_ENTITY_DETAILS_PROMPT,
        output_dir="",
        output_path="",
        status="processing",
    )
    db.add(merge_version)
    db.commit()

    output_dir = os.path.join(
        config.get("processing_dir", "processing_output"),
        str(pipeline.domain_id),
        str(pipeline.domain_version.version_number),
        "merge",
        str(merge_version.version_number),
    )
    merge_version.output_dir = output_dir
    merge_version.output_path = f"{output_dir}/output.json"
    db.commit()

    # Start processing
    background_tasks.add_task(
        process_merge,
        merge_version_id=merge_version.version_id,
        extract_version_ids=merge_request.extract_version_ids,
        config=config,
        db=db,
    )

    return {
        "message": "Entity merging started",
        "pipeline_id": pipeline.pipeline_id,
        "version_id": merge_version.version_id,
        "input_version_ids": merge_request.extract_version_ids,
    }


@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/versions/{domain_version}/merge/{merge_version_id}/group",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=StageStartResponse,
)
async def start_group_processing(
    tenant_id: UUID,
    domain_id: UUID,
    domain_version: int,
    merge_version_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Start grouping entities from merged results"""
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
            status_code=400,
            detail="Can only extract entities for domain versions in DRAFT status",
        )

    # Get pipeline
    pipeline = domain_version_obj.processing_pipeline
    if not pipeline:
        raise HTTPException(
            status_code=404,
            detail="No processing pipeline found for this domain version",
        )

    # Check parse version exists and completed
    merge_version = (
        db.query(MergeVersion)
        .filter(
            MergeVersion.version_id == merge_version_id,
            MergeVersion.status == "completed",
        )
        .first()
    )

    if not merge_version:
        raise HTTPException(
            status_code=404, detail="Merge version not found or not completed"
        )

    config = ConfigManager(db, str(tenant_id), str(domain_id))

    # Create extract version
    group_version = GroupVersion(
        pipeline_id=pipeline.pipeline_id,
        version_number=len(pipeline.group_versions) + 1,
        input_merge_version_id=merge_version_id,
        system_prompt=GROUP_SYSTEM_PROMPT,
        entity_group_prompt=GROUP_PROMPT,
        output_dir="",
        output_path="",
        status="processing",
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

    # Get pipeline
    pipeline = domain_version_obj.processing_pipeline
    if not pipeline:
        raise HTTPException(
            status_code=404,
            detail="No processing pipeline found for this domain version",
        )

    # Start processing
    background_tasks.add_task(
        process_group, merge_version.version_id, group_version.version_id, config, db
    )

    return {
        "message": "Entity grouping started",
        "pipeline_id": pipeline.pipeline_id,
        "version_id": group_version.version_id,
        "input_version_ids": [merge_version_id],
    }


@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/versions/{domain_version}/ontology",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=StageStartResponse,
)
async def start_ontology_processing(
    tenant_id: UUID,
    domain_id: UUID,
    domain_version: int,
    ontology_request: OntologyRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Start generating ontology from grouped entities"""
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
            status_code=400,
            detail="Can only extract entities for domain versions in DRAFT status",
        )

    # Get pipeline
    pipeline = domain_version_obj.processing_pipeline
    if not pipeline:
        raise HTTPException(
            status_code=404,
            detail="No processing pipeline found for this domain version",
        )

    # Check group version exists and completed
    group_version = (
        db.query(GroupVersion)
        .filter(
            GroupVersion.version_id == ontology_request.group_version_id,
            GroupVersion.status == "completed",
        )
        .first()
    )

    if not group_version:
        raise HTTPException(
            status_code=404, detail="Group version not found or not completed"
        )

    config = ConfigManager(db, str(tenant_id), str(domain_id))

    # Check merge version exists and completed
    merge_version = (
        db.query(MergeVersion)
        .filter(
            MergeVersion.version_id == ontology_request.merge_version_id,
            MergeVersion.status == "completed",
        )
        .first()
    )

    if not merge_version:
        raise HTTPException(
            status_code=404, detail="Merge version not found or not completed"
        )

    # Create extract version
    ontology_version = OntologyVersion(
        pipeline_id=pipeline.pipeline_id,
        version_number=len(pipeline.ontology_versions) + 1,
        input_group_version_id=ontology_request.group_version_id,
        input_merge_version_id=ontology_request.merge_version_id,
        system_prompt=ONTOLOGY_SYSTEM_PROMPT,
        ontology_prompt=ONTOLOGY_PROMPT,
        output_dir="",
        output_path="",
        status="processing",
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

    # Get pipeline
    pipeline = domain_version_obj.processing_pipeline
    if not pipeline:
        raise HTTPException(
            status_code=404,
            detail="No processing pipeline found for this domain version",
        )

    # Start processing
    background_tasks.add_task(
        process_ontology,
        merge_version.version_id,
        group_version.version_id,
        ontology_version.version_id,
        config,
        db,
    )

    return {
        "message": "Ontology generation started",
        "pipeline_id": pipeline.pipeline_id,
        "version_id": ontology_version.version_id,
        "input_version_ids": [
            ontology_request.merge_version_id,
            ontology_request.group_version_id,
        ],
    }


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
