from fastapi import APIRouter, Depends, HTTPException
from typing import List
from src.auth.jwt import get_current_user
from src.models.schemas import Methodology
from src.db.methodologies import get_methodologies_by_domain, create_methodology
import uuid

router = APIRouter()


# Route to create a new methodology
@router.post("/", response_model=Methodology)
async def create_new_methodology(
    domain_id: str,
    methodology_data: Methodology,
    current_user=Depends(get_current_user),
):
    user_id = current_user["sub"]

    methodology_id = str(uuid.uuid4())
    new_methodology = create_methodology(
        domain_id=domain_id,
        name=methodology_data.name,
        description=methodology_data.description,
        steps=methodology_data.steps,
    )

    if not new_methodology:
        raise HTTPException(status_code=500, detail="Failed to create methodology")

    return new_methodology


# Route to get all methodologies for a domain
@router.get("/{domain_id}", response_model=List[Methodology])
async def get_methodologies(domain_id: str, current_user=Depends(get_current_user)):
    methodologies = get_methodologies_by_domain(domain_id)

    if not methodologies:
        raise HTTPException(
            status_code=404, detail="No methodologies found for this domain"
        )

    return methodologies
