from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.dependencies import get_current_user
from backend.models import Capture, CaptureStatus, Contact, Modality, User
from backend.schemas import ContactCreate, ContactOut

# Define the prefix and tags for the contacts router
router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.post("/", response_model=ContactOut, status_code=status.HTTP_201_CREATED)
def create_contact(
    payload: ContactCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new contact"""
    # Create the contact row in the database
    new_contact = Contact(
        owner_id=current_user.id,
        display_name=payload.display_name,
        email=payload.email,
        phone=payload.phone,
        company=payload.company,
        role=payload.role,
        location=payload.location,
        # TODO: add profile_tags after implementing AI
        profile_text=payload.profile_text,
    )
    db.add(new_contact)

    # Get new_contact.id first
    db.flush()

    # If raw ASR output provided, create a voice capture
    if payload.raw_transcript:
        new_capture = Capture(
            contact_id=new_contact.id,
            modality=Modality.voice,
            raw_text=payload.raw_transcript,
            status=CaptureStatus.done,
        )
        db.add(new_capture)

    # If raw OCR output provided, create an image capture
    if payload.raw_ocr:
        new_capture = Capture(
            contact_id=new_contact.id,
            modality=Modality.image,
            raw_text=payload.raw_ocr,
            status=CaptureStatus.done,
        )
        db.add(new_capture)

    db.commit()
    db.refresh(new_contact)
    return new_contact


@router.get("/", response_model=list[ContactOut])
def list_contacts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all contacts for the current user"""
    return (
        db.query(Contact)
        .filter(Contact.owner_id == current_user.id)
        .order_by(Contact.created_at.desc())
        .all()
    )


@router.get("/{contact_id}", response_model=ContactOut)
def get_contact(
    contact_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific contact for the current user"""
    contact = (
        db.query(Contact)
        .filter(Contact.id == contact_id, Contact.owner_id == current_user.id)
        .first()
    )
    # If the contact is not found, raise a 404 Not Found exception
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    
    return contact