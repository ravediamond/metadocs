from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, status
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime
from typing import List, Optional
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
    DomainVersion,
    DomainVersionStatus,
    FileVersion,
    PipelineStatus,
    PipelineStage,
)
from ..models.schemas import (
    ProcessingStatus,
    ProcessPipelineSchema,
    ProcessingVersionBase,
    MergeRequest,
    OntologyRequest,
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
from ..processors.parse.processor import ParseProcessor
from ..processors.extract.processor import ExtractProcessor
from ..processors.group.processor import GroupProcessor
from ..processors.ontology.processor import OntologyProcessor
from ..processors.merge.processor import MergeProcessor
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
        logger.info(f"Starting merge for {len(extract_versions)} extract versions")

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
            f"Error in extract processing for parse version {merge_result.version_id}: {str(e)}"
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
        "parse_version_id": parse_version.version_id,
    }


@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/versions/{domain_version}/parse/{parse_version_id}/extract",
    status_code=status.HTTP_202_ACCEPTED,
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
        "extract_version_id": extract_version.version_id,
    }


@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/versions/{domain_version}/merge",
    status_code=status.HTTP_202_ACCEPTED,
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
        input_extraction_version_id=merge_request.extract_version_ids,
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
        "merge_version_id": merge_version.version_id,
        "extract_version_ids": [str(ev.version_id) for ev in extract_versions],
    }


@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/versions/{domain_version}/merge/{merge_version_id}/group",
    status_code=status.HTTP_202_ACCEPTED,
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
        process_merge, merge_version.version_id, group_version.version_id, config, db
    )

    return {
        "message": "Entity extraction started",
        "pipeline_id": pipeline.pipeline_id,
        "merge_version_id": group_version.version_id,
    }


@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/versions/{domain_version}/ontology",
    status_code=status.HTTP_202_ACCEPTED,
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
        ontology_version.version_id,
        merge_version.version_id,
        group_version.version_id,
        ontology_version.version_id,
        config,
        db,
    )

    return {
        "message": "Ontology started",
        "pipeline_id": pipeline.pipeline_id,
        "merge_version_id": ontology_version.version_id,
    }


# Status check endpoints
@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/pipeline/{pipeline_id}",
    response_model=ProcessPipelineSchema,
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

    # Get associated file IDs
    file_ids = [file.file_id for file in pipeline.files]

    return ProcessPipelineSchema(
        processing_id=pipeline.pipeline_id,
        domain_id=pipeline.domain_id,
        status=pipeline.status,
        error=pipeline.error,
        merged_entities_path=pipeline.merged_entities_path,
        entity_grouping_path=pipeline.entity_grouping_path,
        ontology_path=pipeline.ontology_path,
        created_at=pipeline.created_at,
        completed_at=pipeline.completed_at if pipeline.status == "completed" else None,
        file_ids=file_ids,
    )


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/pipeline/{pipeline_id}/parse/{version_number}",
    response_model=ProcessingVersionBase,
)
async def get_parse_version(
    tenant_id: UUID,
    domain_id: UUID,
    pipeline_id: UUID,
    version_number: int,
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
            ParseVersion.version_number == version_number,
        )
        .first()
    )

    if not version:
        raise HTTPException(status_code=404, detail="Parse version not found")

    return version


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/pipeline/{pipeline_id}/extract/{version_number}",
    response_model=ProcessingVersionBase,
)
async def get_extract_version(
    tenant_id: UUID,
    domain_id: UUID,
    pipeline_id: UUID,
    version_number: int,
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
            ExtractVersion.version_number == version_number,
        )
        .first()
    )

    if not version:
        raise HTTPException(status_code=404, detail="Extract version not found")

    return version


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/pipeline/{pipeline_id}/merge/{version_number}",
    response_model=ProcessingVersionBase,
)
async def get_merge_version(
    tenant_id: UUID,
    domain_id: UUID,
    pipeline_id: UUID,
    version_number: int,
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
            MergeVersion.version_number == version_number,
        )
        .first()
    )

    if not version:
        raise HTTPException(status_code=404, detail="Merge version not found")

    return version


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/pipeline/{pipeline_id}/group/{version_number}",
    response_model=ProcessingVersionBase,
)
async def get_group_version(
    tenant_id: UUID,
    domain_id: UUID,
    pipeline_id: UUID,
    version_number: int,
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
            GroupVersion.version_number == version_number,
        )
        .first()
    )

    if not version:
        raise HTTPException(status_code=404, detail="Group version not found")

    return version


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/pipeline/{pipeline_id}/ontology/{version_number}",
    response_model=ProcessingVersionBase,
)
async def get_ontology_version(
    tenant_id: UUID,
    domain_id: UUID,
    pipeline_id: UUID,
    version_number: int,
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
            OntologyVersion.version_number == version_number,
        )
        .first()
    )

    if not version:
        raise HTTPException(status_code=404, detail="Ontology version not found")

    return version


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/pipeline/{pipeline_id}/latest",
    response_model=dict,
)
async def get_latest_versions(
    tenant_id: UUID,
    domain_id: UUID,
    pipeline_id: UUID,
    db: Session = Depends(get_db),
):
    """Get the latest version numbers for each processing stage"""
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

    # Get latest versions
    latest_versions = {
        "parse": db.query(ParseVersion)
        .filter(ParseVersion.pipeline_id == pipeline_id)
        .order_by(ParseVersion.version_number.desc())
        .first(),
        "extract": db.query(ExtractVersion)
        .filter(ExtractVersion.pipeline_id == pipeline_id)
        .order_by(ExtractVersion.version_number.desc())
        .first(),
        "merge": db.query(MergeVersion)
        .filter(MergeVersion.pipeline_id == pipeline_id)
        .order_by(MergeVersion.version_number.desc())
        .first(),
        "group": db.query(GroupVersion)
        .filter(GroupVersion.pipeline_id == pipeline_id)
        .order_by(GroupVersion.version_number.desc())
        .first(),
        "ontology": db.query(OntologyVersion)
        .filter(OntologyVersion.pipeline_id == pipeline_id)
        .order_by(OntologyVersion.version_number.desc())
        .first(),
    }

    return {
        stage: (
            {
                "version_number": version.version_number,
                "status": version.status,
                "created_at": version.created_at,
                "error": version.error,
            }
            if version
            else None
        )
        for stage, version in latest_versions.items()
    }


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/pipeline/{pipeline_id}/parse/{version_id}/status"
)
async def get_parse_status(
    tenant_id: UUID,
    domain_id: UUID,
    pipeline_id: UUID,
    version_id: UUID,
    db: Session = Depends(get_db),
) -> ProcessingStatus:
    """Get parse processing status for a specific version"""
    parse_version = (
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

    if not parse_version:
        raise HTTPException(status_code=404, detail="Parse version not found")

    total_files = len(parse_version.file_versions_id)
    completed = sum(
        1 for status in parse_version.file_statuses if status == "completed"
    )
    failed = sum(1 for status in parse_version.file_statuses if status == "failed")
    processing = sum(
        1 for status in parse_version.file_statuses if status == "processing"
    )

    return ProcessingStatus(
        message=f"Processing {completed}/{total_files} files",
        total_files=total_files,
        files_completed=completed,
        files_failed=failed,
        files_processing=processing,
        processing_started=True,
        parse_status=parse_version.global_status,
    )


# Add these routes to manage stage prompts
@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/versions/{domain_version}/prompts/{stage}"
)
async def get_stage_prompts(
    tenant_id: UUID,
    domain_id: UUID,
    domain_version: int,
    stage: str,
    db: Session = Depends(get_db),
):
    """Get current prompts for a specific processing stage"""
    # Validate stage
    valid_stages = {"parse", "extract", "merge", "group", "ontology"}
    if stage not in valid_stages:
        raise HTTPException(status_code=400, detail="Invalid stage")

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

    # Get latest version of the specified stage
    pipeline = domain_version_obj.processing_pipeline
    if not pipeline:
        raise HTTPException(status_code=404, detail="No processing pipeline found")

    version_model = {
        "parse": ParseVersion,
        "extract": ExtractVersion,
        "merge": MergeVersion,
        "group": GroupVersion,
        "ontology": OntologyVersion,
    }[stage]

    latest_version = (
        db.query(version_model)
        .filter(version_model.pipeline_id == pipeline.pipeline_id)
        .order_by(version_model.version_number.desc())
        .first()
    )

    if not latest_version:
        return get_default_prompts(stage)

    return {
        "system_prompt": latest_version.system_prompt,
        "custom_instructions": latest_version.custom_instructions,
        # Add stage-specific prompts
        **get_stage_specific_prompts(stage, latest_version),
    }


@router.put(
    "/tenants/{tenant_id}/domains/{domain_id}/versions/{domain_version}/prompts/{stage}"
)
async def update_stage_prompts(
    tenant_id: UUID,
    domain_id: UUID,
    domain_version: int,
    stage: str,
    prompts: dict,
    db: Session = Depends(get_db),
):
    """Update prompts for a specific processing stage"""
    valid_stages = {"parse", "extract", "merge", "group", "ontology"}
    if stage not in valid_stages:
        raise HTTPException(status_code=400, detail="Invalid stage")

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

    # Create new version with updated prompts
    pipeline = domain_version_obj.processing_pipeline
    if not pipeline:
        pipeline = ProcessingPipeline(domain_id=domain_id)
        domain_version_obj.processing_pipeline = pipeline
        db.add(pipeline)
        db.commit()

    version_model = {
        "parse": ParseVersion,
        "extract": ExtractVersion,
        "merge": MergeVersion,
        "group": GroupVersion,
        "ontology": OntologyVersion,
    }[stage]

    # Validate required prompts are present
    validate_stage_prompts(stage, prompts)

    # Create new version with provided prompts
    new_version = version_model(
        pipeline_id=pipeline.pipeline_id,
        version_number=get_next_version_number(db, pipeline.pipeline_id, version_model),
        **prompts,
    )

    db.add(new_version)
    db.commit()

    return {"message": f"{stage} prompts updated successfully"}


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
