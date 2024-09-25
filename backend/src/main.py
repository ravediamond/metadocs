from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from src.routers import (
    auth,
    domains,
    users,
    concepts,
    sources,
    methodologies,
    user_settings,
    user_domain_settings,
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

# Include Routers
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(domains.router, prefix="/domains", tags=["Domains"])
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(concepts.router, prefix="/concepts", tags=["concepts"])
app.include_router(sources.router, prefix="/sources", tags=["sources"])
app.include_router(
    methodologies.router, prefix="/methodologies", tags=["methodologies"]
)
app.include_router(
    user_settings.router, prefix="/user-settings", tags=["user-settings"]
)
app.include_router(
    user_domain_settings.router,
    prefix="/user-domain-settings",
    tags=["user-domain-settings"],
)


@app.get("/")
async def root():
    return {
        "message": "Hello, this is a dummy function for testing FastAPI with AWS Lambda URLs!"
    }


# For AWS Lambda deployment
handler = Mangum(app)
