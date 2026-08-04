import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.ai.embeddings.bge import get_embedder
from backend.db import get_db
from backend.dependencies import get_current_user
from backend.models import Contact, User
from backend.schemas import ContactCreate, ContactOut, ContactUpdate

logger = logging.getLogger(__name__)

# Define the prefix and tags for the contacts router
router = APIRouter(prefix="/contacts", tags=["contacts"])


def _get_owned_contact(db: Session, contact_id: int, user_id: int) -> Contact:
    """Get a specific contact owned by the current user"""
    # Get the contact from the database
    contact = (
        db.query(Contact)
        .filter(Contact.id == contact_id, Contact.owner_id == user_id)
        .first()
    )
    # If the contact is not found, raise an exception
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return contact


@router.post("/", response_model=ContactOut, status_code=status.HTTP_201_CREATED)
def create_contact(
    payload: ContactCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new contact for the current user"""
    profile_text = (payload.profile_text or "").strip()

    new_contact = Contact(
        owner_id=current_user.id,
        display_name=payload.display_name,
        email=payload.email,
        phone=payload.phone,
        company=payload.company,
        role=payload.role,
        location=payload.location,
        profile_text=payload.profile_text,
        keywords=payload.keywords,
    )

    # Embed profile text for recall search if it exists
    if profile_text:
        try:
            new_contact.profile_embedding = get_embedder().embed_text(profile_text)
        except Exception as e:
            logger.warning("Failed to embed profile text for new contact: %s", e)
    # TODO: handle embedding errors

    db.add(new_contact)
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
    return _get_owned_contact(db, contact_id, current_user.id)


@router.patch("/{contact_id}", response_model=ContactOut)
def update_contact(
    contact_id: int,
    payload: ContactUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a specific contact for the current user"""
    contact = _get_owned_contact(db, contact_id, current_user.id)

    # Update the contact with the new values
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(contact, field, value)

    # Re-embed or clear profile embedding when updated
    if "profile_text" in updates:
        profile_text = (contact.profile_text or "").strip()
        if profile_text:
            try:
                contact.profile_embedding = get_embedder().embed_text(profile_text)
            except Exception as e:
                logger.warning(
                    "Failed to re-embed profile text for contact %s: %s",
                    contact_id,
                    e,
                )
                # TODO: handle embedding errors
        else:
            contact.profile_embedding = None

    db.commit()
    db.refresh(contact)
    return contact