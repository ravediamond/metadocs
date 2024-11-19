# routes.py

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime
from typing import List

from ..models.models import Domain, File as FileModel
from ..models.schemas import FileResponse
from ..core.database import get_db

import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Existing endpoints...


def process_file(file: FileModel):
    """
    Placeholder function to process a file.
    Implement your actual processing logic here.
    """
    logger.info(f"Processing file: {file.filename}")
    # Example processing logic
    # ...
    # After processing, update the last_processed_at timestamp
    file.last_processed_at = datetime.utcnow()


@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/process_files",
    status_code=status.HTTP_200_OK,
    summary="Process all files in a domain",
)
def process_files(
    tenant_id: UUID,
    domain_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Processes all files associated with a specific domain.
    Updates last_processed_at for each processed file.
    """
    # Validate the domain exists and belongs to the tenant
    domain = (
        db.query(Domain)
        .filter(Domain.domain_id == domain_id, Domain.tenant_id == tenant_id)
        .first()
    )
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    # Retrieve all files linked to the domain
    files = db.query(FileModel).filter(FileModel.domain_id == domain_id).all()

    if not files:
        return {"message": "No files to process."}

    try:
        for file in files:
            process_file(file)
        db.commit()
        logger.info(f"Processed {len(files)} files for domain {domain_id}")
        return {"message": f"Processed {len(files)} files."}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to process files for domain {domain_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to process files.")
