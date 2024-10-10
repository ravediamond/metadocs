from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from mangum import Mangum
import logging
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


# Import your routers
from src.routers import auth, domains, users, roles, config
from src.middleware.api_key_middleware import APIKeyMiddleware
from src.core.database import (
    get_db,
)

logging.basicConfig(level=logging.INFO)


app = FastAPI()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logging.error(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers (Authorization, etc.)
)

# Add the API Key Middleware
app.add_middleware(APIKeyMiddleware, db_session=get_db())

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(domains.router, prefix="/domains", tags=["Domains"])
app.include_router(roles.router, prefix="/roles", tags=["Roles"])
app.include_router(config.router, prefix="/config", tags=["Config"])

# AWS Lambda handler for serverless deployment
handler = Mangum(app)
