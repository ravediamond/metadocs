import os
from pydantic import BaseModel

SYSTEM_MODE = os.getenv("SYSTEM_MODE", "open_source")


class Settings(BaseModel):
    # Base processing settings
    PROCESSING_DIR: str = "processing_output"
    PROCESSING_TIMEOUT: int = 3600
    PROCESSING_BATCH_SIZE: int = 5

    # PDF processing settings
    PDF_QUALITY_THRESHOLD: float = 75.0
    PDF_MAX_ITERATIONS: int = 3

    # Entity extraction settings
    ENTITY_MAX_ITERATIONS: int = 3
    ENTITY_BATCH_SIZE: int = 5

    # AWS Bedrock settings
    AWS_REGION: str = "us-east-1"
    AWS_MODEL_ID: str = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"

    class Config:
        env_file = ".env"


settings = Settings()
