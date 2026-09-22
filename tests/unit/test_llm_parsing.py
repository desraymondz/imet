# Unit tests for the LLM, with mock Ollama chat() data
# backend/ai/llm/ollama.py:
# - Contact extraction (build_contact)
# - Recall query understanding (understand_recall_query)
# - Recall filtering (filter_recall_matches)

from unittest.mock import Mock

import pytest

from backend.ai.llm.ollama import OllamaLLM, _normalise_contact_data
from backend.schemas import ContactExtract, RecallFilterCandidate

# Set up
@pytest.fixture
def llm():
    """A fake LLM client."""
    return OllamaLLM()


def script(llm: OllamaLLM, *responses) -> Mock:
    """Replace llm.chat with scripted responses and return the fake to inspect calls."""
    fake = Mock(side_effect=responses)
    llm.chat = fake
    return fake


def candidate(contact_id: int) -> RecallFilterCandidate:
    """A fake candidate with only the id field set."""
    return RecallFilterCandidate(
        id=contact_id,
        display_name="Test",
        company=None,
        role=None,
        location=None,
        profile_text=None,
        keywords=None,
    )


# Contact extraction

@pytest.mark.parametrize("null_like", ["", "null", "UNKNOWN", "N/A"])
def test_normalise_turns_null_like_strings_into_none(null_like):
    """Ensure null-like strings become None."""
    assert _normalise_contact_data({"company": null_like})["company"] is None


def test_normalise_cleans_keywords():
    """Ensure keywords are stripped, and blanks and non-strings are dropped."""
    data = _normalise_contact_data({"keywords": [" hiking ", "", 3, None, "design"]})
    assert data["keywords"] == ["hiking", "design"]

@pytest.mark.parametrize(
    "bad",
    [
        "{}",
        '["Jane"]',
        "{display_name: Jane",
    ],
)
def test_parse_contact_response_rejects_unusable_output(llm, bad):
    """Ensure empty, non-object, and invalid JSON raise a ValueError."""
    with pytest.raises(ValueError):
        llm._parse_contact_response(bad)


def test_build_contact_with_no_input(llm):
    """Ensure blank input skips the LLM and returns an empty contact."""
    fake = script(llm)
    # Whitespace-only fields count as no input
    assert llm.build_contact(transcript=" ", ocr_text="", free_form_text="\n") == ContactExtract()
    assert fake.call_count == 0


def test_build_contact_retries_after_bad_response(llm):
    """Ensure a bad first response is retried and the second parse is used."""
    # Fail once, then succeed
    script(llm, "not json", '{"display_name": "Jane"}')
    assert llm.build_contact(transcript="Met Jane").display_name == "Jane"


def test_build_contact_returns_empty_when_both_attempts_fail(llm):
    """Ensure two failed parses return an empty contact."""
    script(llm, "not json", "{}")
    assert llm.build_contact(transcript="Met Jane") == ContactExtract()


# Recall query understanding

@pytest.mark.parametrize(
    ("response", "in_scope", "keywords"),
    [
        ('{"in_scope": true, "keywords": ["hiking", " outdoors "]}', True, ["hiking", "outdoors"]),
        ('{"in_scope": false, "keywords": []}', False, []),
    ],
)
def test_query_plan_parses_scope_and_keywords(llm, response, in_scope, keywords):
    """Ensure the query plan keeps in_scope and cleaned keywords."""
    script(llm, response)
    plan = llm.understand_recall_query("who likes hiking?")
    assert plan.in_scope is in_scope
    assert plan.keywords == keywords


def test_query_plan_accepts_keywords_as_a_single_string(llm):
    """Ensure a single keyword string is split into words."""
    script(llm, '{"in_scope": true, "keywords": "hiking outdoors"}')
    assert llm.understand_recall_query("who likes hiking?").keywords == ["hiking", "outdoors"]


def test_query_plan_fall_back(llm):
    """Ensure an empty keyword list falls back to the words in the query."""
    script(llm, '{"in_scope": true, "keywords": []}')
    # Leading and trailing space is stripped before splitting
    assert llm.understand_recall_query("  who likes hiking ").keywords == ["who", "likes", "hiking"]


def test_query_plan_retries_after_llm_error(llm):
    """Ensure a failed LLM call is retried and the second plan is used."""
    script(llm, ConnectionError("ollama down"), '{"in_scope": true, "keywords": ["hiking"]}')
    assert llm.understand_recall_query("who likes hiking?").keywords == ["hiking"]


@pytest.mark.parametrize(
    "responses",
    [
        ("not json", '["hiking"]'),
        (ConnectionError("down"), ConnectionError("down")),
    ],
)
def test_query_plan_returns_none_when_both_fail(llm, responses):
    """Ensure two failed attempts return no query plan."""
    script(llm, *responses)
    assert llm.understand_recall_query("who likes hiking?") is None


# Recall filter

def test_filter_keeps_llm_order(llm):
    """Ensure kept contact ids stay in the order the LLM returned."""
    script(llm, '{"contact_ids": [3, 1]}')
    # 2 is dropped
    # 3 ahead of 1
    assert llm.filter_recall_matches("q", [candidate(1), candidate(2), candidate(3)]) == [3, 1]


def test_filter_drops_non_candidates(llm):
    """Ensure ids that were not in the candidate list are dropped."""
    script(llm, '{"contact_ids": [67, 1, 76]}')
    # 67 and 76 were not candidates
    assert llm.filter_recall_matches("q", [candidate(1), candidate(2)]) == [1]


def test_filter_drops_repeated_ids(llm):
    """Ensure an id the LLM repeats is only returned once."""
    script(llm, '{"contact_ids": [2, 1, 2]}')
    # Small models sometimes repeat an id in their JSON output
    assert llm.filter_recall_matches("q", [candidate(1), candidate(2)]) == [2, 1]


def test_filter_retries_after_llm_error(llm):
    """Ensure a failed LLM call is retried and the second filter result is used."""
    # Fail once, then succeed
    script(llm, ConnectionError("ollama down"), '{"contact_ids": [1]}')
    assert llm.filter_recall_matches("q", [candidate(1)]) == [1]


@pytest.mark.parametrize(
    "responses",
    [
        ("not json", '{"contact_ids": ["abc"]}'),
        (ConnectionError("down"), TimeoutError("slow")),
    ],
)
def test_filter_returns_none_when_both_attempts_fail(llm, responses):
    """Ensure two failed attempts return no filter result."""
    script(llm, *responses)
    assert llm.filter_recall_matches("q", [candidate(1)]) is None