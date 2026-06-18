from enum import Enum
import logging

from ollama import Client
from pydantic import ValidationError

from backend.config import settings
from backend.schemas import ContactExtract

logger = logging.getLogger(__name__)


class LLMType(str, Enum):
    """Model types for different tasks."""

    FAST = "fast"
    QUALITY = "quality"


class OllamaLLM:
    def __init__(self):
        # Using Ollama server locally for inference from environment variables
        # Reference: https://github.com/ollama/ollama/blob/main/docs/api.md
        self.client = Client(host=settings.ollama_host)
        
        # Model types from environment variables
        self.models = {
            LLMType.FAST: settings.ollama_model_fast,
            LLMType.QUALITY: settings.ollama_model_quality,
        }

    def chat(
        self,
        llm_type: LLMType,
        messages: list[dict[str, str]],
        *,
        response_format: dict | None = None,
    ) -> str:
        """
        Chat with the LLM using Ollama API and return the response message content.

        Args:
            llm_type: The type of LLM to use (FAST or QUALITY).
            messages: List of messages to send to the LLM.
            response_format: Optional JSON schema for structured output.

        Returns:
            The response from the LLM.
        """

        # Call Ollama API to generate a chat completion
        # Reference: https://github.com/ollama/ollama/blob/main/docs/api.md#generate-a-chat-completion
        # TODO: explore stream response
        response = self.client.chat(
            model=self.models[llm_type],
            messages=messages,
            format=response_format,
        )
        return response.message.content

    def build_contact(
        self,
        transcript: str = "",
        ocr_text: str = "",
        free_form_text: str = "",
    ) -> ContactExtract:
        """
        Build a contact from ASR transcript, OCR text, and free-form text.
        If no input is provided, return an empty ContactExtract.
        """
        inputs: list[str] = []

        # Add input blocks to the prompt if its not empty
        if transcript.strip():
            inputs.append(f"Voice note transcript:\n{transcript.strip()}")
        if ocr_text.strip():
            inputs.append(f"Image text (business card, LinkedIn, Instagram, etc.):\n{ocr_text.strip()}")
        if free_form_text.strip():
            inputs.append(f"Free-form notes:\n{free_form_text.strip()}")

        # If no input is provided, return an empty ContactExtract immediately
        if not inputs:
            return ContactExtract()

        # Join input blocks with newlines
        inputs_block = "\n\n".join(inputs)

        # Build the prompt
        prompt = f"""You are helping someone remember a person they just met.

Here is the raw information captured about this person:

{inputs_block}

Extract a contact profile with these fields:
- display_name: full name, or null if unknown
- email: email address, or null if unknown
- phone: phone number, or null if unknown
- company: company or organisation, or null if unknown
- role: job title or role, or null if unknown
- location: city, country, or address, or null if unknown
- profile_text: a warm, natural 2-3 sentence summary of who this person is.
  Write it like a memory aide — include their role, company, and any interesting
  personal details mentioned in the inputs.
- keywords: short lowercase tags (industry, role, interests, traits)

Use image text mainly for structured fields (name, email, phone, company, role, location).
Use the voice note mainly for personal context, interests, and profile_text.
Use free-form notes mainly to fill gaps or add context when the other sources are sparse.
If multiple sources mention the same field, prefer image text for structured fields.
Do not invent facts not present in the input. Use null for unknown fields.
"""

        # Call the LLM to extract the contact
        response = self.chat(
            LLMType.FAST,
            messages=[{"role": "user", "content": prompt}],
            response_format=ContactExtract.model_json_schema(),
        )

        # Parse the response
        try:
            return ContactExtract.model_validate_json(response)
        except ValidationError as e:
            logger.warning("LLM returned invalid contact: %s", e)
            return ContactExtract()


# Shared LLM instance
_llm: OllamaLLM | None = None


def get_llm() -> OllamaLLM:
    """Return the shared LLM instance."""
    global _llm
    if _llm is None:
        # Create the LLM instance
        _llm = OllamaLLM()
    return _llm
