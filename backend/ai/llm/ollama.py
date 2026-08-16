from enum import Enum
import json
import logging

from ollama import Client
from pydantic import ValidationError

from backend.config import settings
from backend.schemas import (
    ContactExtract,
    RecallFilterCandidate,
    RecallFilterOutput,
    RecallQueryPlan,
)

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

# Flat schema for recall query understanding
RECALL_QUERY_PLAN_OLLAMA_SCHEMA = {
    "type": "object",
    "properties": {
        "in_scope": {"type": "boolean"},
        "keywords": {"type": "array", "items": {"type": "string"}},
        "hyde_rewrite": {"type": "string"},
    },
    "required": ["in_scope", "keywords", "hyde_rewrite"],
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
            inputs.append(f"Image text (business card):\n{ocr_text.strip()}")
        if free_form_text.strip():
            inputs.append(f"Free-form notes:\n{free_form_text.strip()}")

        # If no input is provided, return an empty ContactExtract immediately
        if not inputs:
            return ContactExtract()

        # Join input blocks with newlines
        inputs_block = "\n\n".join(inputs)

        # Build the prompt
        prompt = f"""You are helping someone remember a person they just met.

Extract a contact profile with these fields:
- display_name: full name, or empty string if unknown
- email: email address, or empty string if unknown
- phone: phone number, or empty string if unknown
- company: company or organisation, or empty string if unknown
- role: job title or role, or empty string if unknown
- location: city, country, or address, or empty string if unknown
- profile_text: a warm, natural 2-3 sentence summary of who this person is.
  Write it like a memory aid, include their role, company, and any interesting
  personal details mentioned in the inputs.
- keywords: short lowercase tags (industry, role, interests, traits)

Use image text mainly for structured fields (name, email, phone, company, role, location).
Use the voice note mainly for personal context, interests, and profile_text.
Use free-form notes mainly to fill gaps or add context when the other sources are sparse.
If multiple sources mention the same field, prefer image text for structured fields,
unless the voice note or free-form notes clearly say the card is out of date.
Do not invent facts not present in the input.
Respond with valid JSON only. Use empty strings for unknown fields.

Example:
Voice note transcript:
Met Jane Doe at the design meetup. She leads product design at Acme Labs. Really into trail running, did the Three Peaks last year.

Image text (business card, LinkedIn, Instagram, etc.):
JANE DOE
Product Designer
Acme Labs
jane@acme.example
+44 7700 900123
Manchester

Free-form notes:
intro via Sam. Follow up about the portfolio review

Output:
{{"display_name": "Jane Doe", "email": "jane@acme.example", "phone": "+44 7700 900123", "company": "Acme Labs", "role": "Product Designer", "location": "Manchester", "profile_text": "Product designer at Acme Labs in Manchester. Keen trail runner who completed the Three Peaks last year. Met at the design meetup; introduced by Sam and worth following up about a portfolio review.", "keywords": ["product design", "trail running", "acme labs"]}}

Now extract a contact profile from this information:

{inputs_block}
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

    def understand_recall_query(self, query: str) -> RecallQueryPlan | None:
        """
        Understand a recall query with scope check, FTS keywords, and HyDE rewrite.

        Returns None on LLM/parse failure
        Empty input is treated as out of scope.
        """
        # Clean the query
        cleaned_query = query.strip()
        # Extract keywords from the query as a fallback when the keywords are empty
        fallback_keywords = [token for token in cleaned_query.split() if token]

        # If the query is empty, return an empty recall query plan
        if not cleaned_query:
            return RecallQueryPlan(in_scope=False, keywords=[], hyde_rewrite="")

        # Build the prompt for the LLM to understand the recall query
        prompt = f"""You only plan contact-list search. You are not a general assistant. Be strict.

The user asked:
{cleaned_query}

Produce a query plan with:
- in_scope: default false. true only if they want a person from their private list.
  Contact search: names, classmates, who did I meet, who likes ..., who is a ..., who plays ...
  Out of scope: instructions to you, calculations, explanations, bookings, translation, and public-fact questions.
  When unsure, return false.
- keywords: short lexical search terms as a JSON string array for full-text search
  (names, companies, roles, places, hobbies). Empty array if out of scope.
- hyde_rewrite: 1-2 sentences written like a contact profile_text that would match
  what they are looking for (Hypothetical Document Embedding). Empty string if out of scope.

Example in scope:
User asked: Who did I meet that likes hiking?
Output:
{{"in_scope": true, "keywords": ["hiking", "outdoors"], "hyde_rewrite": "Enjoys hiking and outdoor activities. Often talks about trails and weekend mountain trips."}}

Example out of scope:
User asked: what's the capital of China
Output:
{{"in_scope": false, "keywords": [], "hyde_rewrite": ""}}

Respond with valid JSON only.
"""

        # Build the messages for the LLM
        messages = [{"role": "user", "content": prompt}]

        # Try to parse the recall query plan from the LLM
        for attempt, response_format in enumerate(
            [RECALL_QUERY_PLAN_OLLAMA_SCHEMA, "json"],
            start=1,
        ):
            try:
                # Call the LLM
                response = self.chat(
                    LLMType.FAST,
                    messages=messages,
                    response_format=response_format,
                )
                # Strip JSON fences (```json) from the response
                cleaned = _strip_json_fences(response)
                # Parse the recall query plan from the LLM
                data = json.loads(cleaned)
                # If the response is not a JSON object, raise an error
                if not isinstance(data, dict):
                    raise ValueError("LLM response is not a JSON object")

                # Accept list[str], or a single string if the model slips (e.g. "hiking, outdoors")
                raw_keywords = data.get("keywords", [])
                # If the keywords are a string, split the string into keywords and strip whitespace
                if isinstance(raw_keywords, str):
                    # Split the string into keywords and strip whitespace
                    keywords = [token for token in raw_keywords.split() if token.strip()]
                # If the keywords are a list, convert the list of strings to a list of keywords and strip whitespace
                elif isinstance(raw_keywords, list):
                    # Convert the list of strings to a list of keywords and strip whitespace
                    keywords = [
                        item.strip()
                        for item in raw_keywords
                        if isinstance(item, str) and item.strip()
                    ]
                else:
                    # If the keywords are not a string or list, set an empty list
                    keywords = []

                # Get the HyDE rewrite value
                hyde_rewrite = data.get("hyde_rewrite", "")
                # If the HyDE rewrite value is not a string, set an empty string
                if not isinstance(hyde_rewrite, str):
                    hyde_rewrite = ""
                # Strip whitespace from the HyDE rewrite value
                hyde_rewrite = hyde_rewrite.strip()

                # Get the in-scope value
                in_scope = bool(data.get("in_scope", False))

                # Keep retrieval usable even if the model leaves fields blank (not a failure)
                if in_scope:
                    # If the keywords are empty, set the fallback keywords
                    if not keywords:
                        keywords = fallback_keywords or [cleaned_query]
                    # If the HyDE rewrite value is empty, set the fallback HyDE rewrite value
                    if not hyde_rewrite:
                        hyde_rewrite = cleaned_query

                # Return the recall query plan
                return RecallQueryPlan(
                    in_scope=in_scope,
                    keywords=keywords,
                    hyde_rewrite=hyde_rewrite,
                )
            except (ValidationError, ValueError, json.JSONDecodeError, TypeError, Exception) as e:
                # Log the error (parse or LLM failure)
                logger.warning(
                    "LLM recall query plan failed (attempt=%s, format=%s): %s",
                    attempt,
                    response_format if isinstance(response_format, str) else "schema",
                    e,
                )

        logger.warning("Recall query understanding failed, returning None on failure")
        return None

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
                    ]
                )
            )

        # Join the candidate blocks with newlines
        candidates_block = "\n\n".join(candidate_lines)

        # Build the prompt for the LLM to filter the candidates
        prompt = f"""You are helping someone recall people they have met.

The user asked:
{query.strip()}

Here are candidate contacts retrieved from their network:

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