# src/main.py

from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello, this is a dummy function for testing FastAPI with AWS Lambda URLs!"}