from fastapi import APIRouter, Depends, HTTPException
from fastapi import Request
from typing import List
from src.auth.jwt import get_current_user
from src.models.schemas import DomainCreate, Domain
import uuid
from datetime import datetime
from src.db.domains import get_domains_by_owner
from src.db.rds import get_db_connection, commit_and_close

router = APIRouter()


# Route to create a domain
@router.post("/", response_model=Domain)
async def create_domain(
    domain_data: DomainCreate, current_user=Depends(get_current_user)
):
    user_id = current_user["sub"]
    domain_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO domains (DomainId, DomainName, OwnerUserId, Description, CreatedAt)
                VALUES (%s, %s, %s, %s, %s);
                """,
                (
                    domain_id,
                    domain_data.domain_name,
                    user_id,
                    domain_data.description,
                    now,
                ),
            )
        commit_and_close(conn)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create domain: {str(e)}"
        )

    return Domain(
        domain_id=domain_id,
        domain_name=domain_data.domain_name,
        owner_user_id=user_id,
        description=domain_data.description,
        created_at=now,
    )


# Route to get all domains owned by the current user
@router.get("/", response_model=List[Domain])
async def get_my_domains(current_user=Depends(get_current_user)):
    user_id = current_user["sub"]

    try:
        domains = get_domains_by_owner(user_id)
        if not domains:
            raise HTTPException(
                status_code=404, detail="No domains found for this user"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch domains: {str(e)}"
        )

    return domains
