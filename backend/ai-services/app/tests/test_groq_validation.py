import pytest
from pydantic import BaseModel, ValidationError
from app.services.groq_client import GroqClientWrapper


class SampleOutput(BaseModel):
    summary: str
    confidence: float


@pytest.mark.asyncio
async def test_unconfigured_groq_returns_none_safely():
    client = GroqClientWrapper()
    client.api_key = ""  # Force unconfigured

    result = await client.generate_structured(
        messages=[{"role": "user", "content": "hello"}],
        response_model=SampleOutput,
    )
    assert result is None
    assert client.is_configured() is False


def test_pydantic_structured_model_validation():
    valid_payload = {"summary": "Safe coastal zone", "confidence": 0.95}
    obj = SampleOutput.model_validate(valid_payload)
    assert obj.summary == "Safe coastal zone"
    assert obj.confidence == 0.95

    with pytest.raises(ValidationError):
        SampleOutput.model_validate({"summary": "Incomplete"})
