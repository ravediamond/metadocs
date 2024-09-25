from fastapi import APIRouter, Depends, HTTPException
from typing import List
from src.auth.jwt import get_current_user
from src.models.schemas import Source
from src.db.sources import get_sources_by_domain, create_source
import uuid

router = APIRouter()


# Route to create a new source
@router.post("/", response_model=Source)
async def create_new_source(
    domain_id: str, source_data: Source, current_user=Depends(get_current_user)
):
    user_id = current_user["sub"]

    source_id = str(uuid.uuid4())
    new_source = create_source(
        domain_id=domain_id,
        name=source_data.name,
        source_type=source_data.source_type,
        location=source_data.location,
        description=source_data.description,
    )

    if not new_source:
        raise HTTPException(status_code=500, detail="Failed to create source")

    return new_source


# Route to get all sources for a domain
@router.get("/{domain_id}", response_model=List[Source])
async def get_sources(domain_id: str, current_user=Depends(get_current_user)):
    sources = get_sources_by_domain(domain_id)

    if not sources:
        raise HTTPException(status_code=404, detail="No sources found for this domain")

    return sources
