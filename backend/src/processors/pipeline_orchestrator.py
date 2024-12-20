import os
import asyncio
from typing import List, Optional
from uuid import UUID
import logging
from sqlalchemy.orm import Session
from ..models.models import (
    ProcessingPipeline,
    ParseVersion,
    ExtractVersion,
    MergeVersion,
    GroupVersion,
    OntologyVersion,
    FileVersion,
    PipelineStatus,
    PipelineStage,
)
from ..core.config import ConfigManager
from ..processors.parse_processor import ParseProcessor
from ..processors.extract_processor import ExtractProcessor
from ..processors.merge_processor import MergeProcessor
from ..processors.group_processor import GroupProcessor
from ..processors.ontology_processor import OntologyProcessor
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
    ENTITY_MERGE_PROMPT,
    ENTITY_DETAILS_PROMPT as MERGE_ENTITY_DETAILS_PROMPT,
)
from ..processors.prompts.group_prompts import (
    SYSTEM_PROMPT as GROUP_SYSTEM_PROMPT,
    GROUP_PROMPT,
)
from ..processors.prompts.ontology_prompts import (
    SYSTEM_PROMPT as ONTOLOGY_SYSTEM_PROMPT,
    ONTOLOGY_PROMPT,
)

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    def __init__(self, SessionLocal: Session, config: ConfigManager, pipeline_id: UUID):
        self.SessionLocal = SessionLocal
        self.config = config
        self.pipeline_id = pipeline_id

    def _setup_stage_paths(
        self,
        pipeline,
        stage_name: str,
        version_number: int,
        file_version_id: Optional[str] = None,
    ) -> tuple[str, str]:
        """Setup output paths for a processing stage

        Args:
            pipeline: The processing pipeline instance
            stage_name: Name of the stage (parse, extract, merge, etc.)
            version_number: Version number for this stage
            file_version_id: Optional file version ID (only used for parse stage)

        Returns:
            Tuple of (output_dir, output_path)
        """
        try:
            # Build base output directory path
            base_path = os.path.join(
                self.config.get("processing_dir", "processing_output"),
                str(pipeline.domain_id),
                str(pipeline.domain_version.version_number),
                stage_name,
                str(version_number),
            )

            # Add file_version_id for parse stage only
            if stage_name == "parse" and file_version_id:
                base_path = os.path.join(base_path, str(file_version_id))

            # Create directories
            os.makedirs(base_path, exist_ok=True)

            # Verify directory is writable
            if not os.access(base_path, os.W_OK):
                raise PermissionError(f"Directory {base_path} is not writable")

            # Get correct extension based on stage
            extension = ".md" if stage_name == "parse" else ".json"
            output_path = os.path.join(base_path, f"output{extension}")

            logger.info(f"Set up paths for {stage_name} stage: {output_path}")
            return base_path, output_path

        except Exception as e:
            logger.error(f"Error setting up paths for {stage_name} stage: {str(e)}")
            raise

    async def _process_parse_stage(
        self, db: Session, pipeline: ProcessingPipeline, file_version_ids: List[UUID]
    ) -> List[ParseVersion]:
        """Process the parse stage for all input files."""
        logger.info("Starting PARSE stage")
        pipeline.stage = PipelineStage.PARSE
        pipeline.status = PipelineStatus.RUNNING
        db.commit()

        parse_versions = []
        for file_version_id in file_version_ids:
            try:
                file_version = (
                    db.query(FileVersion)
                    .filter(FileVersion.file_version_id == file_version_id)
                    .first()
                )
                if not file_version:
                    logger.error(f"File version {file_version_id} not found")
                    continue

                version_number = len(pipeline.parse_versions) + 1
                output_dir, output_path = self._setup_stage_paths(
                    pipeline, "parse", version_number, str(file_version_id)
                )

                parse_version = ParseVersion(
                    pipeline_id=self.pipeline_id,
                    version_number=version_number,
                    system_prompt=PARSE_SYSTEM_PROMPT,
                    readability_prompt=CHECK_READABILITY_PROMPT,
                    convert_prompt=CONVERT_TO_MARKDOWN_PROMPT,
                    input_file_version_id=file_version_id,
                    status="processing",
                    custom_instructions=[],
                    output_dir=output_dir,
                    output_path=output_path,
                )
                db.add(parse_version)
                db.commit()

                parse_versions.append((parse_version, file_version))
                logger.info(f"Created parse version for file {file_version_id}")

            except Exception as e:
                logger.error(
                    f"Error creating parse version for file {file_version_id}: {str(e)}"
                )
                db.rollback()

        if not parse_versions:
            raise Exception("No parse versions could be created")

        # Process files in parallel
        parse_tasks = [
            (
                pv,
                asyncio.create_task(
                    asyncio.to_thread(ParseProcessor(fv, pv, self.config).process)
                ),
            )
            for pv, fv in parse_versions
        ]

        successful_versions = []
        for parse_version, task in parse_tasks:
            try:
                result = await task
                parse_version.status = "completed" if result.success else "failed"
                if result.success:
                    successful_versions.append(parse_version)
                else:
                    parse_version.error = result.error
                db.commit()
            except Exception as e:
                logger.error(
                    f"Error in parse task {parse_version.version_id}: {str(e)}"
                )
                parse_version.status = "failed"
                parse_version.error = str(e)
                db.commit()

        if not successful_versions:
            raise Exception("All parse tasks failed")

        logger.info(
            f"Completed parse stage with {len(successful_versions)} successful parses"
        )
        return successful_versions

    async def _process_extract_stage(
        self,
        db: Session,
        pipeline: ProcessingPipeline,
        parse_versions: List[ParseVersion],
    ) -> List[ExtractVersion]:
        """Process the extract stage for all parsed files."""
        logger.info("Starting EXTRACT stage")
        pipeline.stage = PipelineStage.EXTRACT
        pipeline.status = PipelineStatus.RUNNING
        db.commit()

        extract_versions = []
        for parse_version in parse_versions:
            try:
                db.refresh(parse_version)
                if parse_version.status != "completed":
                    continue

                version_number = len(pipeline.extract_versions) + 1
                output_dir, output_path = self._setup_stage_paths(
                    pipeline, "extract", version_number
                )

                extract_version = ExtractVersion(
                    pipeline_id=self.pipeline_id,
                    version_number=version_number,
                    input_parse_version_id=parse_version.version_id,
                    status="processing",
                    system_prompt=EXTRACT_SYSTEM_PROMPT,
                    initial_entity_extraction_prompt=INITIAL_ENTITY_EXTRACTION_PROMPT,
                    iterative_extract_entities_prompt=ITERATIVE_ENTITY_EXTRACTION_PROMPT,
                    entity_details_prompt=EXTRACT_ENTITY_DETAILS_PROMPT,
                    custom_instructions=[],
                    output_dir=output_dir,
                    output_path=output_path,
                )
                db.add(extract_version)
                db.commit()

                processor = ExtractProcessor(
                    parse_version, extract_version, self.config
                )
                task = asyncio.create_task(asyncio.to_thread(processor.process))
                extract_versions.append((extract_version, task))

            except Exception as e:
                logger.error(f"Error creating extract version: {str(e)}")
                db.rollback()

        if not extract_versions:
            raise Exception("No extract versions could be created")

        successful_versions = []
        for version, task in extract_versions:
            try:
                result = await task
                version.status = "completed" if result.success else "failed"
                if result.success:
                    successful_versions.append(version)
                else:
                    version.error = result.error
                db.commit()
            except Exception as e:
                logger.error(f"Error in extract task: {str(e)}")
                version.status = "failed"
                version.error = str(e)
                db.commit()

        if not successful_versions:
            raise Exception("All extract tasks failed")

        return successful_versions

    async def _process_merge_stage(
        self,
        db: Session,
        pipeline: ProcessingPipeline,
        extract_versions: List[ExtractVersion],
    ) -> MergeVersion:
        """Process the merge stage combining all extracted entities."""
        logger.info("Starting MERGE stage")
        pipeline.stage = PipelineStage.MERGE
        pipeline.status = PipelineStatus.RUNNING
        db.commit()

        version_number = len(pipeline.merge_versions) + 1
        output_dir, output_path = self._setup_stage_paths(
            pipeline, "merge", version_number
        )

        merge_version = MergeVersion(
            pipeline_id=self.pipeline_id,
            version_number=version_number,
            input_extract_version_ids=[v.version_id for v in extract_versions],
            status="processing",
            system_prompt=MERGE_SYSTEM_PROMPT,
            entity_merge_prompt=ENTITY_MERGE_PROMPT,
            entity_details_prompt=MERGE_ENTITY_DETAILS_PROMPT,
            custom_instructions=[],
            output_dir=output_dir,
            output_path=output_path,
        )
        db.add(merge_version)
        db.commit()

        processor = MergeProcessor(extract_versions, merge_version, self.config)
        result = await asyncio.to_thread(processor.process)

        if not result.success:
            raise Exception(f"Merge processing failed: {result.error}")

        merge_version.status = "completed"
        db.commit()
        return merge_version

    async def _process_group_stage(
        self, db: Session, pipeline: ProcessingPipeline, merge_version: MergeVersion
    ) -> GroupVersion:
        """Process the group stage to analyze entity groups."""
        logger.info("Starting GROUP stage")
        pipeline.stage = PipelineStage.GROUP
        pipeline.status = PipelineStatus.RUNNING
        db.commit()

        version_number = len(pipeline.group_versions) + 1
        output_dir, output_path = self._setup_stage_paths(
            pipeline, "group", version_number
        )

        group_version = GroupVersion(
            pipeline_id=self.pipeline_id,
            version_number=version_number,
            input_merge_version_id=merge_version.version_id,
            status="processing",
            system_prompt=GROUP_SYSTEM_PROMPT,
            entity_group_prompt=GROUP_PROMPT,
            custom_instructions=[],
            output_dir=output_dir,
            output_path=output_path,
        )
        db.add(group_version)
        db.commit()

        processor = GroupProcessor(merge_version, group_version, self.config)
        result = await asyncio.to_thread(processor.process)

        if not result.success:
            raise Exception(f"Group processing failed: {result.error}")

        group_version.status = "completed"
        db.commit()
        return group_version

    async def _process_ontology_stage(
        self,
        db: Session,
        pipeline: ProcessingPipeline,
        merge_version: MergeVersion,
        group_version: GroupVersion,
    ):
        """Process the final ontology stage."""
        logger.info("Starting ONTOLOGY stage")
        pipeline.stage = PipelineStage.ONTOLOGY
        pipeline.status = PipelineStatus.RUNNING
        db.commit()

        version_number = len(pipeline.ontology_versions) + 1
        output_dir, output_path = self._setup_stage_paths(
            pipeline, "ontology", version_number
        )

        ontology_version = OntologyVersion(
            pipeline_id=self.pipeline_id,
            version_number=version_number,
            input_merge_version_id=merge_version.version_id,
            input_group_version_id=group_version.version_id,
            status="processing",
            system_prompt=ONTOLOGY_SYSTEM_PROMPT,
            ontology_prompt=ONTOLOGY_PROMPT,
            custom_instructions=[],
            output_dir=output_dir,
            output_path=output_path,
        )
        db.add(ontology_version)
        db.commit()

        processor = OntologyProcessor(
            merge_version, group_version, ontology_version, self.config
        )
        result = await asyncio.to_thread(processor.process)

        if not result.success:
            raise Exception(f"Ontology processing failed: {result.error}")

        ontology_version.status = "completed"
        db.commit()

    async def process_pipeline(self, file_version_ids: List[UUID]):
        """Main method to process the entire pipeline."""
        db = self.SessionLocal()
        try:
            pipeline = db.query(ProcessingPipeline).get(self.pipeline_id)
            if not pipeline:
                raise Exception("Pipeline not found")

            if pipeline.status == PipelineStatus.COMPLETED:
                logger.info("Pipeline is already completed")
                return

            # Execute each stage
            parse_versions = await self._process_parse_stage(
                db, pipeline, file_version_ids
            )
            extract_versions = await self._process_extract_stage(
                db, pipeline, parse_versions
            )
            merge_version = await self._process_merge_stage(
                db, pipeline, extract_versions
            )
            group_version = await self._process_group_stage(db, pipeline, merge_version)
            await self._process_ontology_stage(
                db, pipeline, merge_version, group_version
            )

            # Mark pipeline as completed
            pipeline.stage = PipelineStage.COMPLETED
            pipeline.status = PipelineStatus.COMPLETED
            db.commit()
            logger.info("Pipeline completed successfully")

        except Exception as e:
            logger.error(f"Pipeline processing failed: {str(e)}")
            try:
                pipeline = db.query(ProcessingPipeline).get(self.pipeline_id)
                if pipeline:
                    pipeline.status = PipelineStatus.FAILED
                    pipeline.error = str(e)
                    db.commit()
            except Exception as commit_error:
                logger.error(f"Error updating pipeline status: {str(commit_error)}")
            raise
        finally:
            try:
                db.close()
            except Exception as close_error:
                logger.error(f"Error closing database connection: {str(close_error)}")
