# Pydantic schemas for the API requests and responses

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

# Status of a recall search (success, out of scope, no matches, error)
RecallStatus = Literal["ok", "out_of_scope", "no_matches", "error"]


class ContactCreate(BaseModel):
    """Request schema for creating a contact"""
    display_name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    role: str | None = None
    location: str | None = None
    # LLM-generated natural language summary
    profile_text: str | None = None
    # Searchable tags, e.g. ["investor", "tech", "hiking"]
    keywords: list[str] | None = None


class ContactExtract(BaseModel):
    """Response schema for LLM-extracted contact fields from capture inputs"""
    display_name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    role: str | None = None
    location: str | None = None
    profile_text: str | None = None
    keywords: list[str] | None = None


class BuildContactRequest(BaseModel):
    """Request schema for building a contact from capture inputs"""
    transcript: str = ""
    ocr_text: str = ""
    free_form_text: str = ""


class ContactUpdate(BaseModel):
    """Request schema for updating a contact"""
    display_name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    role: str | None = None
    location: str | None = None
    profile_text: str | None = None
    keywords: list[str] | None = None


class ContactOut(BaseModel):
    """Response schema for a contact"""
    id: int
    display_name: str | None
    email: str | None
    phone: str | None
    company: str | None
    role: str | None
    location: str | None
    # LLM-generated natural language summary
    profile_text: str | None
    # Searchable tags, e.g. ["investor", "tech", "hiking"]
    keywords: list[str] | None
    created_at: datetime
    updated_at: datetime

    # Config for pydantic to convert database models to pydantic models
    model_config = {"from_attributes": True}


class RecallSearchRequest(BaseModel):
    """Request schema for semantic recall search"""
    query: str


class RecallResultItem(BaseModel):
    """A contact match returned from recall search"""
    contact: ContactOut
    score: float


class RecallSearchResponse(BaseModel):
    """Response schema for recall search results"""
    status: RecallStatus
    results: list[RecallResultItem]


class RecallFilterCandidate(BaseModel):
    """A contact candidate passed to the LLM recall filter to build the prompt"""
    id: int
    display_name: str | None
    company: str | None
    role: str | None
    location: str | None
    profile_text: str | None
    keywords: list[str] | None


class RecallFilterOutput(BaseModel):
    """LLM output for the recall filter step"""
    contact_ids: list[int]


class RecallQueryPlan(BaseModel):
    """LLM output for recall query understanding (Phase 1)"""
    # Whether the query is in scope for the current user
    in_scope: bool
    # Lexical terms for Postgres FTS
    keywords: list[str]
    # Hypothetical profile blurb to embed (HyDE) for semantic recall
    hyde_rewrite: str