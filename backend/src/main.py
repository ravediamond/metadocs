from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from mangum import Mangum

# Import your routers
from src.routers import (
    auth,
    domains,
    users,
)
from src.middleware.api_key_middleware import APIKeyMiddleware
from src.core.database import (
    get_db,
)

app = FastAPI()

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


# Dummy route for testing the setup
@app.get("/")
async def root():
    return {
        "message": "Hello, this is a dummy function for testing FastAPI with AWS Lambda URLs!"
    }


# AWS Lambda handler for serverless deployment
handler = Mangum(app)
