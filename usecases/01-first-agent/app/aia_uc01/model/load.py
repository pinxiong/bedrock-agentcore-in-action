"""Model selection for every use case in this series.

One environment variable decides the model:

    MODEL_ID    default: deepseek.v3.2

Anthropic and OpenAI models on Bedrock are refused from some countries and
territories with a ValidationException about "unsupported countries, regions,
or territories". Amazon and DeepSeek models are not. The series default is a
model that answers from anywhere, so the first run is never blocked by where
you sit.

Verified callable from us-east-1 on 2026-10-14:

    deepseek.v3.2        (default, OpenAI-compatible response shape)
    amazon.nova-pro-v1:0
    amazon.nova-lite-v1:0

Not callable on-demand (needs an inference profile):

    deepseek.r1-v1:0
    amazon.nova-2-lite-v1:0
"""

from __future__ import annotations

import os

from strands.models.bedrock import BedrockModel

DEFAULT_MODEL_ID = "deepseek.v3.2"
REGION = os.environ.get("AWS_REGION", "us-east-1")


def model_id() -> str:
    """Return the model id this deployment should call."""
    return os.environ.get("MODEL_ID", DEFAULT_MODEL_ID)


def load_model() -> BedrockModel:
    """Build a Bedrock model client using the runtime's IAM credentials."""
    return BedrockModel(model_id=model_id(), region_name=REGION)
