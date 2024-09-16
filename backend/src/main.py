from fastapi import FastAPI
from mangum import Mangum

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello, this is a dummy function for testing FastAPI with AWS Lambda URLs!"}


handler = Mangum(app)