from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, status
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime
from typing import List, Optional
import logging

from ..models.models import (
    Domain,
    File as FileModel,
    ProcessingPipeline,
    ParseVersion,
    ExtractVersion,
    MergeVersion,
    GroupVersion,
    OntologyVersion,
)
from ..models.schemas import (
    ProcessingStatus,
    FileStatus,
    ProcessPipelineSchema,
    ProcessingVersionBase,
)
from ..core.database import get_db
from ..processors.pdf.processor import PDFProcessor
from ..processors.entity.processor import EntityProcessor
from ..processors.groups.processor import GroupProcessor
from ..processors.ontology.processor import OntologyProcessor
from ..processors.merger.processor import EntityMerger
from ..core.config import ConfigManager
from .version_manager import VersionManager

logger = logging.getLogger(__name__)
router = APIRouter()


# Processing Functions
async def process_parse(
    file: FileModel, pipeline: ProcessingPipeline, config: ConfigManager, db: Session
) -> bool:
    """Process a single file through PDF parsing stage"""
    version_manager = VersionManager(pipeline.pipeline_id, db)

    try:
        parse_version = version_manager.create_parse_version(file.filepath)
        pipeline.current_parse_id = parse_version.version_id
        db.commit()

        pdf_processor = PDFProcessor(file, pipeline, config)
        pdf_result = pdf_processor.process()

        if not pdf_result.success:
            parse_version.status = "failed"
            parse_version.error = f"PDF processing failed: {pdf_result.message}"
            file.processing_status = "failed"
            file.processing_error = parse_version.error
            db.commit()
            return False

        parse_version.output_path = pdf_result.markdown_path
        parse_version.status = "completed"
        file.markdown_path = pdf_result.markdown_path
        file.processing_status = "completed"
        db.commit()
        return True

    except Exception as e:
        logger.error(f"Error in parse processing for file {file.file_id}: {str(e)}")
        parse_version.status = "failed"
        parse_version.error = str(e)
        file.processing_status = "failed"
        file.processing_error = str(e)
        db.commit()
        return False


async def process_extract(
    file: FileModel, pipeline: ProcessingPipeline, config: ConfigManager, db: Session
) -> bool:
    """Process a single file through entity extraction stage"""
    version_manager = VersionManager(pipeline.pipeline_id, db)

    try:
        if not file.markdown_path:
            raise ValueError("No markdown file available for extraction")

        extract_version = version_manager.create_extract_version(file.markdown_path)
        pipeline.current_extract_id = extract_version.version_id
        db.commit()

        entity_processor = EntityProcessor(pipeline, config)
        entity_result = entity_processor.process()

        if not entity_result.success:
            extract_version.status = "failed"
            extract_version.error = f"Entity extraction failed: {entity_result.message}"
            file.processing_status = "failed"
            file.processing_error = extract_version.error
            db.commit()
            return False

        extract_version.output_path = entity_result.analysis_path
        extract_version.status = "completed"
        file.entity_extraction_path = entity_result.analysis_path
        file.processing_status = "completed"
        db.commit()
        return True

    except Exception as e:
        logger.error(f"Error in extract processing for file {file.file_id}: {str(e)}")
        extract_version.status = "failed"
        extract_version.error = str(e)
        file.processing_status = "failed"
        file.processing_error = str(e)
        db.commit()
        return False


async def process_merge(
    pipeline: ProcessingPipeline,
    files: List[FileModel],
    config: ConfigManager,
    db: Session,
) -> bool:
    """Process entity merging stage"""
    version_manager = VersionManager(pipeline.pipeline_id, db)

    try:
        entity_paths = [
            f.entity_extraction_path
            for f in files
            if f.processing_status == "completed" and f.entity_extraction_path
        ]

        if not entity_paths:
            raise ValueError("No entity extraction files available for merging")

        merge_version = version_manager.create_merge_version(entity_paths)
        pipeline.current_merge_id = merge_version.version_id
        db.commit()

        merger = EntityMerger(pipeline, config)
        merge_result = merger.process()

        if not merge_result.success:
            merge_version.status = "failed"
            merge_version.error = f"Entity merging failed: {merge_result.message}"
            pipeline.status = "failed"
            pipeline.error = merge_version.error
            db.commit()
            return False

        merge_version.output_path = merge_result.merged_path
        merge_version.status = "completed"
        pipeline.merged_entities_path = merge_result.merged_path
        db.commit()
        return True

    except Exception as e:
        logger.error(f"Error in merge processing: {str(e)}")
        merge_version.status = "failed"
        merge_version.error = str(e)
        pipeline.status = "failed"
        pipeline.error = str(e)
        db.commit()
        return False


async def process_group(
    pipeline: ProcessingPipeline, config: ConfigManager, db: Session
) -> bool:
    """Process entity grouping stage"""
    version_manager = VersionManager(pipeline.pipeline_id, db)

    try:
        # Get latest successful merge version
        merge_version = (
            db.query(MergeVersion)
            .filter(
                MergeVersion.pipeline_id == pipeline.pipeline_id,
                MergeVersion.status == "completed",
            )
            .order_by(MergeVersion.version_number.desc())
            .first()
        )

        if not merge_version or not merge_version.output_path:
            raise ValueError("No merged entities file available for grouping")

        group_version = version_manager.create_group_version(merge_version.output_path)
        pipeline.current_group_id = group_version.version_id
        db.commit()

        group_processor = GroupProcessor(pipeline, config)
        group_result = group_processor.process()

        if not group_result.success:
            group_version.status = "failed"
            group_version.error = f"Group analysis failed: {group_result.message}"
            pipeline.status = "failed"
            pipeline.error = group_version.error
            db.commit()
            return False

        group_version.output_path = group_result.groups_path
        group_version.status = "completed"
        pipeline.entity_grouping_path = group_result.groups_path
        db.commit()
        return True

    except Exception as e:
        logger.error(f"Error in group processing: {str(e)}")
        group_version.status = "failed"
        group_version.error = str(e)
        pipeline.status = "failed"
        pipeline.error = str(e)
        db.commit()
        return False


async def process_ontology(
    pipeline: ProcessingPipeline, config: ConfigManager, db: Session
) -> bool:
    """Process ontology generation stage"""
    version_manager = VersionManager(pipeline.pipeline_id, db)

    try:
        # Get latest successful group version
        group_version = (
            db.query(GroupVersion)
            .filter(
                GroupVersion.pipeline_id == pipeline.pipeline_id,
                GroupVersion.status == "completed",
            )
            .order_by(GroupVersion.version_number.desc())
            .first()
        )

        if not group_version or not group_version.output_path:
            raise ValueError(
                "No grouped entities file available for ontology generation"
            )

        ontology_version = version_manager.create_ontology_version(
            group_version.output_path
        )
        pipeline.current_ontology_id = ontology_version.version_id
        db.commit()

        ontology_processor = OntologyProcessor(pipeline, config)
        ontology_result = ontology_processor.process()

        if not ontology_result.success:
            ontology_version.status = "failed"
            ontology_version.error = (
                f"Ontology generation failed: {ontology_result.message}"
            )
            pipeline.status = "failed"
            pipeline.error = ontology_version.error
            db.commit()
            return False

        ontology_version.output_path = ontology_result.diagram_path
        ontology_version.status = "completed"
        pipeline.ontology_path = ontology_result.diagram_path
        pipeline.status = "completed"
        pipeline.completed_at = datetime.utcnow()
        db.commit()
        return True

    except Exception as e:
        logger.error(f"Error in ontology processing: {str(e)}")
        ontology_version.status = "failed"
        ontology_version.error = str(e)
        pipeline.status = "failed"
        pipeline.error = str(e)
        db.commit()
        return False


# API Endpoints
@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/files/{file_id}/parse",
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_parse_processing(
    tenant_id: UUID,
    domain_id: UUID,
    file_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Start PDF parsing for a single file"""
    file = (
        db.query(FileModel)
        .join(Domain)
        .filter(
            Domain.tenant_id == tenant_id,
            FileModel.domain_id == domain_id,
            FileModel.file_id == file_id,
        )
        .first()
    )

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    pipeline = ProcessingPipeline(domain_id=domain_id, status="processing")
    db.add(pipeline)
    db.commit()

    file.processing_status = "processing_pdf"
    db.commit()

    config = ConfigManager(db, str(tenant_id), str(domain_id))
    background_tasks.add_task(process_parse, file, pipeline, config, db)

    return {"message": "PDF parsing started", "pipeline_id": pipeline.pipeline_id}


@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/files/{file_id}/extract",
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_extract_processing(
    tenant_id: UUID,
    domain_id: UUID,
    file_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Start entity extraction for a single file"""
    file = (
        db.query(FileModel)
        .join(Domain)
        .filter(
            Domain.tenant_id == tenant_id,
            FileModel.domain_id == domain_id,
            FileModel.file_id == file_id,
        )
        .first()
    )

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    if not file.markdown_path:
        raise HTTPException(status_code=400, detail="File has not been parsed yet")

    pipeline = ProcessingPipeline(domain_id=domain_id, status="processing")
    db.add(pipeline)
    db.commit()

    file.processing_status = "processing_entities"
    db.commit()

    config = ConfigManager(db, str(tenant_id), str(domain_id))
    background_tasks.add_task(process_extract, file, pipeline, config, db)

    return {"message": "Entity extraction started", "pipeline_id": pipeline.pipeline_id}


@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/merge",
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_merge_processing(
    tenant_id: UUID,
    domain_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Start merging entities from all processed files in the domain"""
    files = (
        db.query(FileModel)
        .join(Domain)
        .filter(
            Domain.tenant_id == tenant_id,
            FileModel.domain_id == domain_id,
            FileModel.processing_status == "completed",
            FileModel.entity_extraction_path.isnot(None),
        )
        .all()
    )

    if not files:
        raise HTTPException(
            status_code=400, detail="No completed files available for merging"
        )

    pipeline = ProcessingPipeline(domain_id=domain_id, status="processing")
    db.add(pipeline)
    db.commit()

    config = ConfigManager(db, str(tenant_id), str(domain_id))
    background_tasks.add_task(process_merge, pipeline, files, config, db)

    return {"message": "Entity merging started", "pipeline_id": pipeline.pipeline_id}


@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/group",
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_group_processing(
    tenant_id: UUID,
    domain_id: UUID,
    pipeline_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Start grouping entities from merged results"""
    pipeline = (
        db.query(ProcessingPipeline)
        .join(Domain)
        .filter(
            Domain.tenant_id == tenant_id,
            ProcessingPipeline.domain_id == domain_id,
            ProcessingPipeline.pipeline_id == pipeline_id,
            ProcessingPipeline.merged_entities_path.isnot(None),
        )
        .first()
    )

    if not pipeline:
        raise HTTPException(
            status_code=404,
            detail="Processing pipeline not found or merge not completed",
        )

    config = ConfigManager(db, str(tenant_id), str(domain_id))
    background_tasks.add_task(process_group, pipeline, config, db)

    return {"message": "Entity grouping started", "pipeline_id": pipeline.pipeline_id}


@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/ontology",
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_ontology_processing(
    tenant_id: UUID,
    domain_id: UUID,
    pipeline_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Start generating ontology from grouped entities"""
    pipeline = (
        db.query(ProcessingPipeline)
        .join(Domain)
        .filter(
            Domain.tenant_id == tenant_id,
            ProcessingPipeline.domain_id == domain_id,
            ProcessingPipeline.pipeline_id == pipeline_id,
            ProcessingPipeline.entity_grouping_path.isnot(None),
        )
        .first()
    )

    if not pipeline:
        raise HTTPException(
            status_code=404,
            detail="Processing pipeline not found or grouping not completed",
        )

    config = ConfigManager(db, str(tenant_id), str(domain_id))
    background_tasks.add_task(process_ontology, pipeline, config, db)

    return {
        "message": "Ontology generation started",
        "pipeline_id": pipeline.pipeline_id,
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
