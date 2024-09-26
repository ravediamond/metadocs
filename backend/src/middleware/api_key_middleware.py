from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from src.models.models import APIKey, User


class APIKeyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, db_session: Session):
        super().__init__(app)
        self.db_session = db_session

    async def dispatch(self, request: Request, call_next):
        # Check if 'X-API-Key' header is present
        api_key = request.headers.get("X-API-Key")
        if api_key:
            # Validate the API key
            user = self.validate_api_key(api_key)
            if not user:
                raise HTTPException(
                    status_code=403, detail="Invalid or revoked API key"
                )
            request.state.user = (
                user  # Attach user to request.state, making it accessible in the route
            )
        # Proceed to the next middleware or the request handler
        response = await call_next(request)
        return response

    def validate_api_key(self, api_key: str) -> User:
        # Query the database to check if the API key is valid and not revoked
        db: Session = self.db_session()
        api_key_obj = (
            db.query(APIKey)
            .filter(APIKey.api_key == api_key, APIKey.revoked == None)
            .first()
        )
        if not api_key_obj:
            return None
        # Return the user associated with this API key
        return db.query(User).filter(User.user_id == api_key_obj.user_id).first()
