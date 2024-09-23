from fastapi import FastAPI
from mangum import Mangum

from routers import users, domains, invitations

app = FastAPI()

# Include Routers
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(domains.router, prefix="/domains", tags=["Domains"])
app.include_router(invitations.router, prefix="/invitations", tags=["Invitations"])


@app.get("/")
async def root():
    return {
        "message": "Hello, this is a dummy function for testing FastAPI with AWS Lambda URLs!"
    }


# For AWS Lambda deployment
handler = Mangum(app)
