from enum import Enum
import json
import logging

from ollama import Client
from pydantic import ValidationError

from backend.config import settings
from backend.schemas import ContactExtract, RecallFilterCandidate, RecallFilterOutput

logger = logging.getLogger(__name__)

# Flat schema for contact extraction
CONTACT_OLLAMA_SCHEMA = {
    "type": "object",
    "properties": {
        "display_name": {"type": "string"},
        "email": {"type": "string"},
        "phone": {"type": "string"},
        "company": {"type": "string"},
        "role": {"type": "string"},
        "location": {"type": "string"},
        "profile_text": {"type": "string"},
        "keywords": {"type": "array", "items": {"type": "string"}},
    },
}

# Flat schema for recall filter
RECALL_FILTER_OLLAMA_SCHEMA = {
    "type": "object",
    "properties": {
        "contact_ids": {"type": "array", "items": {"type": "integer"}},
    },
    "required": ["contact_ids"],
}

# Strings that are considered null or empty
_NULL_STRINGS = {"", "null", "none", "unknown", "n/a"}

def _strip_json_fences(content: str) -> str:
    """Helper function to strip JSON fences (```json) from the response"""
    text = content.strip()
    if not text.startswith("```"):
        return text
    text = text.removeprefix("```json").removeprefix("```").strip()
    if text.endswith("```"):
        text = text[:-3].strip()
    return text


def _normalise_contact_data(data: dict) -> dict:
    """Helper function to normalise contact data (convert to lowercase, strip whitespace, etc.)"""
    # Initialise an empty dictionary to store the normalised data
    normalised: dict = {}
    # Iterate over the fields in the ContactExtract schema
    for field in ContactExtract.model_fields:
        value = data.get(field)
        # If the field is keywords, normalise the list of keywords
        if field == "keywords":
            if isinstance(value, list):
                keywords = [item.strip() for item in value if isinstance(item, str) and item.strip()]
                normalised[field] = keywords or None
            else:
                normalised[field] = None
            continue
        # If the field is a string, normalise the string
        if isinstance(value, str):
            cleaned = value.strip()
            normalised[field] = None if cleaned.lower() in _NULL_STRINGS else cleaned
        else:
            normalised[field] = value
    return normalised


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
        response_format: dict | str | None = None,
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
        # Set the temperature to 0.1 for more deterministic responses
        # TODO: explore stream response
        response = self.client.chat(
            model=self.models[llm_type],
            messages=messages,
            format=response_format,
            think=False,
            options={"temperature": 0.1} if response_format is not None else None,
        )
        
        # Log the response message content
        content = response.message.content or ""
        logger.info(
            "LLM response (model=%s, structured=%s):\n%s",
            self.models[llm_type],
            response_format is not None,
            content or "(empty)",
        )
        return content

    def _parse_contact_response(self, response: str) -> ContactExtract:
        """Helper function to parse the contact response from the LLM"""
        # Strip JSON fences (```json) from the response
        cleaned = _strip_json_fences(response)
        if cleaned.strip() in ("", "{}", "{ }"):
            raise ValueError("LLM returned empty JSON object")

        # Load the response as a JSON object
        data = json.loads(cleaned)
        # If the response is not a JSON object, raise an error
        if not isinstance(data, dict):
            raise ValueError("LLM response is not a JSON object")

        # Normalise the contact data and return the ContactExtract schema
        return ContactExtract.model_validate(_normalise_contact_data(data))

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
Respond with valid JSON only. Use empty strings for unknown fields.
"""

        # Build the messages for the LLM
        messages = [{"role": "user", "content": prompt}]

        # Try to parse the contact response from the LLM
        for attempt, response_format in enumerate([CONTACT_OLLAMA_SCHEMA, "json"], start=1):
            # Call the LLM
            response = self.chat(
                LLMType.FAST,
                messages=messages,
                response_format=response_format,
            )
            try:
                # Parse the contact response from the LLM
                return self._parse_contact_response(response)
            except (ValidationError, ValueError, json.JSONDecodeError) as e:
                # Log the error
                logger.warning(
                    "LLM contact parse failed",
                    attempt,
                    response_format if isinstance(response_format, str) else "schema",
                    e,
                )

        return ContactExtract()

    def filter_recall_matches(
        self,
        query: str,
        candidates: list[RecallFilterCandidate],
    ) -> list[int] | None:
        """
        Filter recall candidates with the LLM.
        Returns a list of contact IDs in the order of LLM filter
        """
        # Return early if there are no candidates
        if not candidates:
            return []

        # Build the prompt for each candidate and its fields
        candidate_lines: list[str] = []
        for candidate in candidates:
            name = (candidate.display_name or "").strip() or "Unknown"
            company = (candidate.company or "").strip() or "none"
            role = (candidate.role or "").strip() or "none"
            location = (candidate.location or "").strip() or "none"
            keywords = ", ".join(candidate.keywords or []) or "none"
            profile_text = (candidate.profile_text or "").strip() or "none"
            candidate_lines.append(
                "\n".join(
                    [
                        f"- id: {candidate.id}",
                        f"  name: {name}",
                        f"  company: {company}",
                        f"  role: {role}",
                        f"  location: {location}",
                        f"  keywords: {keywords}",
                        f"  profile_text: {profile_text}",
                        f"  vector_score: {candidate.score:.4f}",
                    ]
                )
            )

        # Join the candidate blocks with newlines
        candidates_block = "\n\n".join(candidate_lines)

        # Build the prompt for the LLM to filter the candidates
        prompt = f"""You are helping someone recall people they have met.

The user asked:
{query.strip()}

Here are semantic-search candidates retrieved from their contacts:

{candidates_block}

Return contact_ids for the candidates that genuinely match the user's question.
- Return IDs in best-match order.
- Return an empty list if none of the candidates truly match.
- Only use IDs from the candidate list above.
- Do not invent contacts or facts not supported by the candidate summaries.
Respond with valid JSON only.
"""

        # Build the messages for the LLM
        messages = [{"role": "user", "content": prompt}]

        # Try to parse the recall filter response from the LLM
        for attempt, response_format in enumerate([RECALL_FILTER_OLLAMA_SCHEMA, "json"], start=1):
            # Call the LLM
            response = self.chat(
                LLMType.FAST,
                messages=messages,
                response_format=response_format,
            )
            try:
                # Strip JSON fences (```json) from the response
                cleaned = _strip_json_fences(response)
                # Parse the recall filter response from the LLM
                parsed = RecallFilterOutput.model_validate_json(cleaned)
                break
            except ValidationError as e:
                # Log the error
                logger.warning(
                    "LLM recall parse failed",
                    attempt,
                    response_format if isinstance(response_format, str) else "schema",
                    e,
                )
                parsed = None
        else:
            return None

        
        if parsed is None:
            return None

        # Keep only IDs that were in the candidate list, skip any hallucinated IDs
        matched_ids: list[int] = []
        for contact_id in parsed.contact_ids:
            for candidate in candidates:
                if candidate.id == contact_id:
                    matched_ids.append(contact_id)
                    break

        return matched_ids


# Shared LLM instance
_llm: OllamaLLM | None = None


def get_llm() -> OllamaLLM:
    """Return the shared LLM instance."""
    global _llm
    if _llm is None:
        # Create the LLM instance
        _llm = OllamaLLM()
    return _llm