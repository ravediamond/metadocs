from fastapi import APIRouter, Depends, HTTPException, status
from auth.jwt import get_current_user
from models.schemas import DomainCreate, Domain
from db.dynamodb import domains_table, memberships_table
import uuid
from datetime import datetime

router = APIRouter()


@router.post("/", response_model=Domain)
async def create_domain(
    domain_data: DomainCreate, current_user=Depends(get_current_user)
):
    user_id = current_user["sub"]
    domain_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    # Create domain item
    domain_item = {
        "DomainId": domain_id,
        "DomainName": domain_data.domain_name,
        "OwnerUserId": user_id,
        "Description": domain_data.description,
        "CreatedAt": now,
    }

    # Save domain to DomainsTable
    domains_table.put_item(Item=domain_item)

    # Add the owner to DomainMembershipsTable
    membership_item = {
        "DomainId": domain_id,
        "UserId": user_id,
        "Role": "owner",
        "MembershipStatus": "active",
        "JoinedAt": now,
    }
    memberships_table.put_item(Item=membership_item)

    return Domain(
        domain_id=domain_id,
        domain_name=domain_data.domain_name,
        owner_user_id=user_id,
        description=domain_data.description,
    )


@router.get("/", response_model=List[Domain])
async def get_my_domains(current_user=Depends(get_current_user)):
    user_id = current_user["sub"]

    # Query DomainMembershipsTable to get domains where the user is a member
    response = memberships_table.query(
        IndexName="UserIdIndex",
        KeyConditionExpression="UserId = :uid",
        ExpressionAttributeValues={":uid": user_id},
    )

    domain_ids = [item["DomainId"] for item in response.get("Items", [])]

    # Batch get domains from DomainsTable
    if not domain_ids:
        return []

    keys = [{"DomainId": domain_id} for domain_id in domain_ids]
    response = dynamodb.batch_get_item(
        RequestItems={
            domains_table.name: {
                "Keys": keys,
            }
        }
    )

    domains = response["Responses"].get(domains_table.name, [])
    return domains
