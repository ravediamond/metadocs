from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from src.routers import (
    auth,
    domains,
    users,
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

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(domains.router, prefix="/domains", tags=["Domains"])


@app.get("/")
async def root():
    return {
        "message": "Hello, this is a dummy function for testing FastAPI with AWS Lambda URLs!"
    }


# For AWS Lambda deployment
handler = Mangum(app)
