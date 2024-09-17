from pydantic import BaseModel, EmailStr
from typing import Optional, List

# User Models
class User(BaseModel):
    user_id: str
    email: EmailStr
    name: Optional[str] = None

# Domain Models
class DomainCreate(BaseModel):
    domain_name: str
    description: Optional[str] = None

class Domain(BaseModel):
    domain_id: str
    domain_name: str
    owner_user_id: str
    description: Optional[str] = None

# Invitation Models
class InvitationCreate(BaseModel):
    invitee_email: EmailStr
    role: Optional[str] = "member"

class Invitation(BaseModel):
    invitation_id: str
    domain_id: str
    inviter_user_id: str
    invitee_email: EmailStr
    role: str
    invitation_status: str

# Membership Models
class Membership(BaseModel):
    domain_id: str
    user_id: str
    role: str
    membership_status: str