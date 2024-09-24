from pydantic import BaseModel, EmailStr
from typing import Optional, List


# User Models
class UserLogin(BaseModel):
    email: str
    password: str


class User(BaseModel):
    user_id: str
    email: str
    name: str


# Domain Models
class DomainCreate(BaseModel):
    domain_name: str
    description: Optional[str] = None


class Domain(BaseModel):
    domain_id: str
    domain_name: str
    owner_user_id: str
    description: Optional[str] = None
