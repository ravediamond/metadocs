import os
import json
import requests
from jose import jwt
from functools import lru_cache
from fastapi import Request, HTTPException, status, Depends
from typing import List

AUTH0_DOMAIN = os.environ.get("AUTH0_DOMAIN")
API_AUDIENCE = os.environ.get("API_AUDIENCE")
NAMESPACE = os.environ.get("NAMESPACE")
ALGORITHMS = ["RS256"]

if not AUTH0_DOMAIN or not API_AUDIENCE or not NAMESPACE:
    raise Exception("Auth0 domain or API audience not set in environment variables.")


@lru_cache()
def get_jwks():
    jwks_url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
    jwks = requests.get(jwks_url).json()
    return jwks


def get_token_auth_header(request: Request):
    auth = request.headers.get("Authorization", None)
    if not auth:
        raise HTTPException(status_code=401, detail="Authorization header is missing")

    parts = auth.split()
    if parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401, detail="Authorization header must start with Bearer"
        )
    elif len(parts) == 1:
        raise HTTPException(status_code=401, detail="Token not found")
    elif len(parts) > 2:
        raise HTTPException(
            status_code=401, detail="Authorization header must be Bearer token"
        )

    token = parts[1]
    return token


def verify_token(token: str):
    jwks = get_jwks()
    unverified_header = jwt.get_unverified_header(token)
    rsa_key = {}
    for key in jwks["keys"]:
        if key["kid"] == unverified_header["kid"]:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"],
            }
    if rsa_key:
        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=ALGORITHMS,
                audience=API_AUDIENCE,
                issuer=f"https://{AUTH0_DOMAIN}/",
            )
            # Extract roles using the namespace
            namespace = "https://{NAMESPACE}/"  # Replace with your actual namespace
            roles = payload.get(f"{namespace}roles", [])
            payload["roles"] = roles  # Add roles to the payload
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.JWTClaimsError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect claims, please check the audience and issuer",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Unable to parse authentication token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to find appropriate key",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(request: Request):
    token = get_token_auth_header(request)
    payload = verify_token(token)
    return payload  # Contains user information and roles


def require_roles(required_roles: List[str]):
    def role_checker(current_user=Depends(get_current_user)):
        user_roles = current_user.get("roles", [])
        if not set(required_roles).intersection(user_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient permissions",
            )
        return current_user  # User is authorized

    return role_checker
