# Pydantic schemas for the API requests and responses

from datetime import datetime
from pydantic import BaseModel, EmailStr


class ContactCreate(BaseModel):
    """Request schema for creating a contact"""
    display_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    company: str | None = None
    role: str | None = None
    location: str | None = None
    # LLM-generated natural language summary
    profile_text: str | None = None 
    # Raw ASR output (stored as Capture)
    raw_transcript: str | None = None
    # Raw OCR output (stored as Capture)
    raw_ocr: str | None = None



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
    # TODO: add profile_tags after implementing AI
    
    created_at: datetime
    updated_at: datetime

    # Config for pydantic to convert database models to pydantic models
    model_config = {"from_attributes": True}