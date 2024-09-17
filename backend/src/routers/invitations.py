from fastapi import APIRouter, Depends, HTTPException, status
from auth.auth0 import get_current_user
from models.schemas import InvitationCreate, Invitation
from db.dynamodb import invitations_table, domains_table
import uuid
from datetime import datetime

router = APIRouter()

@router.post("/{domain_id}", response_model=Invitation)
async def invite_user(domain_id: str, invitation_data: InvitationCreate, current_user=Depends(get_current_user)):
    user_id = current_user["sub"]
    now = datetime.utcnow().isoformat()

    # Check if current user is the owner of the domain
    domain_response = domains_table.get_item(Key={"DomainId": domain_id})
    if "Item" not in domain_response:
        raise HTTPException(status_code=404, detail="Domain not found")

    domain = domain_response["Item"]
    if domain["OwnerUserId"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to invite users to this domain")

    invitation_id = str(uuid.uuid4())

    invitation_item = {
        "InvitationId": invitation_id,
        "DomainId": domain_id,
        "InviterUserId": user_id,
        "InviteeEmail": invitation_data.invitee_email,
        "Role": invitation_data.role,
        "InvitationStatus": "pending",
        "SentAt": now,
    }

    # Save invitation to InvitationsTable
    invitations_table.put_item(Item=invitation_item)

    # Optionally, send an email to the invitee with an invitation link
    # send_invitation_email(invitation_data.invitee_email, invitation_id)

    return Invitation(
        invitation_id=invitation_id,
        domain_id=domain_id,
        inviter_user_id=user_id,
        invitee_email=invitation_data.invitee_email,
        role=invitation_data.role,
        invitation_status="pending",
    )

@router.post("/accept/{invitation_id}")
async def accept_invitation(invitation_id: str, current_user=Depends(get_current_user)):
    user_id = current_user["sub"]
    user_email = current_user.get("email")
    now = datetime.utcnow().isoformat()

    # Get the invitation
    response = invitations_table.get_item(Key={"InvitationId": invitation_id})
    if "Item" not in response:
        raise HTTPException(status_code=404, detail="Invitation not found")

    invitation = response["Item"]

    if invitation["InvitationStatus"] != "pending":
        raise HTTPException(status_code=400, detail="Invitation is not pending")

    if invitation["InviteeEmail"] != user_email:
        raise HTTPException(status_code=403, detail="This invitation is not for your email")

    # Update the invitation status
    invitations_table.update_item(
        Key={"InvitationId": invitation_id},
        UpdateExpression="SET InvitationStatus = :status, AcceptedAt = :acceptedAt, InviteeUserId = :userId",
        ExpressionAttributeValues={
            ":status": "accepted",
            ":acceptedAt": now,
            ":userId": user_id,
        },
    )

    # Add user to DomainMembershipsTable
    membership_item = {
        "DomainId": invitation["DomainId"],
        "UserId": user_id,
        "Role": invitation["Role"],
        "MembershipStatus": "active",
        "JoinedAt": now,
    }
    memberships_table.put_item(Item=membership_item)

    return {"message": "Invitation accepted and you have joined the domain"}

@router.get("/", response_model=List[Invitation])
async def get_my_invitations(current_user=Depends(get_current_user)):
    user_email = current_user.get("email")

    # Query invitations by InviteeEmail
    response = invitations_table.query(
        IndexName="InviteeEmailIndex",
        KeyConditionExpression="InviteeEmail = :email",
        ExpressionAttributeValues={":email": user_email},
    )

    invitations = response.get("Items", [])
    return invitations