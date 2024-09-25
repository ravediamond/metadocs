from fastapi import APIRouter, Depends, HTTPException
from typing import List
from src.auth.jwt import get_current_user
from src.models.schemas import Concept, DomainCreate
from src.db.concepts import get_concepts_by_domain, create_concept
import uuid

router = APIRouter()


# Route to create a new concept
@router.post("/", response_model=Concept)
async def create_new_concept(
    domain_id: str, concept_data: DomainCreate, current_user=Depends(get_current_user)
):
    user_id = current_user["sub"]

    concept_id = str(uuid.uuid4())
    new_concept = create_concept(
        domain_id=domain_id,
        name=concept_data.domain_name,
        description=concept_data.description,
        concept_type=concept_data.type,
    )

    if not new_concept:
        raise HTTPException(status_code=500, detail="Failed to create concept")

    return new_concept


# Route to get all concepts for a domain
@router.get("/{domain_id}", response_model=List[Concept])
async def get_concepts(domain_id: str, current_user=Depends(get_current_user)):
    concepts = get_concepts_by_domain(domain_id)

    if not concepts:
        raise HTTPException(status_code=404, detail="No concepts found for this domain")

    return concepts
