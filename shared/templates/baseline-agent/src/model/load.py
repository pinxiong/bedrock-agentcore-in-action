"""Model selection for {{UC_ID}}.

MODEL_ID decides which Bedrock model this deployment calls. The default is
DeepSeek because Anthropic and OpenAI models are refused from some countries
and territories:

    ValidationException: Access to Anthropic models is not allowed from
    unsupported countries, regions, or territories.

Amazon and DeepSeek models are not restricted that way. Verified callable from
us-east-1 on 2026-10-14: deepseek.v3.2, amazon.nova-pro-v1:0,
amazon.nova-lite-v1:0.
"""

from __future__ import annotations

import os

from strands.models.bedrock import BedrockModel

DEFAULT_MODEL_ID = "{{MODEL_ID}}"
REGION = os.environ.get("AWS_REGION", "us-east-1")


def model_id() -> str:
    """Return the model id this deployment should call."""
    return os.environ.get("MODEL_ID", DEFAULT_MODEL_ID)


def load_model() -> BedrockModel:
    """Build a Bedrock model client using the runtime's IAM credentials."""
    return BedrockModel(model_id=model_id(), region_name=REGION)
