from uuid import UUID
from sqlalchemy.orm import Session
from typing import List

from ..models.models import (
    ParseVersion,
    ExtractVersion,
    MergeVersion,
    GroupVersion,
    OntologyVersion,
    GraphVersion,
)


class VersionManager:
    def __init__(self, pipeline_id: UUID, db: Session):
        self.pipeline_id = pipeline_id
        self.db = db

    def _get_next_version(self, version_class) -> int:
        latest = (
            self.db.query(version_class)
            .filter(version_class.pipeline_id == self.pipeline_id)
            .order_by(version_class.version_number.desc())
            .first()
        )
        return (latest.version_number + 1) if latest else 1

    def create_parse_version(self, input_path: str) -> ParseVersion:
        version = ParseVersion(
            pipeline_id=self.pipeline_id,
            version_number=self._get_next_version(ParseVersion),
            input_path=input_path,
            status="processing",
        )
        self.db.add(version)
        self.db.commit()
        return version

    def create_extract_version(self, input_path: str) -> ExtractVersion:
        version = ExtractVersion(
            pipeline_id=self.pipeline_id,
            version_number=self._get_next_version(ExtractVersion),
            input_path=input_path,
            status="processing",
        )
        self.db.add(version)
        self.db.commit()
        return version

    def create_merge_version(self, input_paths: List[str]) -> MergeVersion:
        version = MergeVersion(
            pipeline_id=self.pipeline_id,
            version_number=self._get_next_version(MergeVersion),
            input_path=",".join(input_paths),
            status="processing",
        )
        self.db.add(version)
        self.db.commit()
        return version

    def create_group_version(self, input_path: str) -> GroupVersion:
        version = GroupVersion(
            pipeline_id=self.pipeline_id,
            version_number=self._get_next_version(GroupVersion),
            input_path=input_path,
            status="processing",
        )
        self.db.add(version)
        self.db.commit()
        return version

    def create_ontology_version(self, input_path: str) -> OntologyVersion:
        version = OntologyVersion(
            pipeline_id=self.pipeline_id,
            version_number=self._get_next_version(OntologyVersion),
            input_path=input_path,
            status="processing",
        )
        self.db.add(version)
        self.db.commit()
        return version

    def create_graph_version(self, input_path: str) -> GraphVersion:
        version = GraphVersion(
            pipeline_id=self.pipeline_id,
            version_number=self._get_next_version(GraphVersion),
            input_path=input_path,
            status="processing",
        )
        self.db.add(version)
        self.db.commit()
        return version
