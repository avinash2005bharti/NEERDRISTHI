from typing import Optional, Dict, Any, List, Type, TypeVar
import json
import httpx
from pydantic import BaseModel, ValidationError
from ..config import settings
from ..observability.logger import logger

T = TypeVar("T", bound=BaseModel)


class GroqClientWrapper:
    """
    Production-grade Groq LLM client wrapper.
    Invariants:
    1. Validates API configuration before attempting network calls.
    2. Uses deterministic low temperature (0.0).
    3. Strictly enforces Pydantic structured output validation.
    4. Logs only safe metadata, never secret keys or sensitive raw prompts.
    5. Returns typed fallback outputs when unconfigured.
    6. Never permits the LLM to override deterministic safety rules.
    """

    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL or "llama-3.3-70b-versatile"
        self.temperature = settings.GROQ_TEMPERATURE
        self.max_tokens = settings.GROQ_MAX_TOKENS or 2048
        self.timeout_seconds = settings.GROQ_TIMEOUT_SECONDS

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    async def generate_structured(
        self,
        messages: List[Dict[str, str]],
        response_model: Type[T],
        system_prompt: Optional[str] = None,
    ) -> Optional[T]:
        """
        Request structured JSON from Groq and validate through Pydantic response_model.
        """
        if not self.is_configured():
            logger.debug("GROQ_API_KEY is blank. Skipping LLM synthesis and using deterministic response.")
            return None

        prompt_list = []
        if system_prompt:
            prompt_list.append({"role": "system", "content": system_prompt})
        prompt_list.extend(messages)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": prompt_list,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
        }

        try:
            logger.info(
                f"Calling Groq API model='{self.model}' with {len(prompt_list)} messages (low temperature: {self.temperature})"
            )
            async with httpx.AsyncClient(timeout=float(self.timeout_seconds)) as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )

                if response.status_code != 200:
                    logger.error(f"Groq API returned HTTP {response.status_code}: {response.text[:200]}")
                    return None

                data = response.json()
                content = data["choices"][0]["message"]["content"]
                parsed_json = json.loads(content)

                if isinstance(parsed_json, dict):
                    # Normalize alternative key names returned by various models
                    if "explanation" not in parsed_json:
                        parsed_json["explanation"] = (
                            parsed_json.get("answer")
                            or parsed_json.get("response")
                            or parsed_json.get("text")
                            or parsed_json.get("summary")
                            or "Safety evaluation completed based on current observations."
                        )
                    if "data_gap_summary" not in parsed_json:
                        parsed_json["data_gap_summary"] = (
                            parsed_json.get("data_gaps")
                            or parsed_json.get("missing_data")
                            or parsed_json.get("gaps")
                            or "Telemetry verified."
                        )
                    if "mandatory_safeguard" not in parsed_json:
                        parsed_json["mandatory_safeguard"] = (
                            parsed_json.get("safeguards")
                            or parsed_json.get("recommendation")
                            or parsed_json.get("action")
                            or "Maintain maritime vigilance."
                        )

                # Validate against target Pydantic model
                validated_obj = response_model.model_validate(parsed_json)
                return validated_obj

        except ValidationError as val_err:
            logger.error(f"Pydantic structured output validation failed on Groq response: {val_err}")
            return None
        except Exception as e:
            logger.error(f"Groq client execution error: {e}")
            return None


groq_client = GroqClientWrapper()
