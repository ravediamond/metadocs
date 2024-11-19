from dataclasses import dataclass
from typing import Optional, Dict, Any
from langchain_anthropic import ChatAnthropic
from langchain_aws.chat_models import ChatBedrock


@dataclass
class LLMConfig:
    provider: str = "bedrock"  # "bedrock" or "anthropic"
    model_id: str = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    region_name: str = "us-east-1"
    profile_name: Optional[str] = None
    temperature: float = 0
    max_tokens: int = 4096
    anthropic_api_key: Optional[str] = None
    model_kwargs: Optional[Dict[str, Any]] = None


class LLMFactory:
    def __init__(self, config: LLMConfig):
        self.config = config

    def create_model(self):
        if self.config.provider == "bedrock":
            kwargs = {
                "model_id": self.config.model_id,
                "region_name": self.config.region_name,
                "model_kwargs": {
                    "temperature": self.config.temperature,
                    "max_tokens": self.config.max_tokens,
                    **(self.config.model_kwargs or {}),
                },
            }
            if self.config.profile_name:
                kwargs["profile_name"] = self.config.profile_name
            return ChatBedrock(**kwargs)

        elif self.config.provider == "anthropic":
            if not self.config.anthropic_api_key:
                raise ValueError(
                    "Anthropic API key is required when using Anthropic provider"
                )
            return ChatAnthropic(
                anthropic_api_key=self.config.anthropic_api_key,
                model=self.config.model_id,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                **(self.config.model_kwargs or {}),
            )
        else:
            raise ValueError(f"Unsupported provider: {self.config.provider}")
