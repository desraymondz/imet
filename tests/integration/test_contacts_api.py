# Integration tests for contacts:
# - Storing a profile embedding on create
# - Re-embedding and clearing it on update
# - Deleting a contact removes it

from backend.models import Contact
from tests.mock_embedder import topic_vector


def get_stored_contact(db_session, contact_id: int) -> Contact:
    """Read a contact from the database and reload it."""
    db_session.expire_all()
    return db_session.get(Contact, contact_id)


def test_storing_embedding(alice, db_session):
    """Ensure creating a contact stores an embedding of its profile text."""
    response = alice.post(
        "/contacts/",
        json={"display_name": "Desmond", "profile_text": "Loves hiking in the Peak District"},
    )
    assert response.status_code == 201

    stored = get_stored_contact(db_session, response.json()["id"])
    assert list(stored.profile_embedding) == topic_vector("Loves hiking in the Peak District")


def test_reembedding_and_clearing(alice, db_session):
    """Ensure updating profile text re-embeds it, and clearing the text removes the embedding."""
    contact_id = alice.post(
        "/contacts/",
        json={"display_name": "Desmond", "profile_text": "Loves hiking in the Peak District"},
    ).json()["id"]

    # A new profile_text is re-embedded
    updated = alice.patch(f"/contacts/{contact_id}", json={"profile_text": "Works in finance"})
    assert updated.status_code == 200
    stored = get_stored_contact(db_session, contact_id)
    assert list(stored.profile_embedding) == topic_vector("Works in finance")

    # Clear the embedding on empty text
    cleared = alice.patch(f"/contacts/{contact_id}", json={"profile_text": ""})
    assert cleared.status_code == 200
    assert get_stored_contact(db_session, contact_id).profile_embedding is None


def test_deleting_contact(alice, db_session):
    """Ensure deleting a contact removes it from the database."""
    contact_id = alice.post(
        "/contacts/",
        json={"display_name": "Desmond", "profile_text": "Loves hiking in the Peak District"},
    ).json()["id"]

    deleted = alice.delete(f"/contacts/{contact_id}")
    assert deleted.status_code == 204

    # The row is gone, so reading it back is a 404
    assert get_stored_contact(db_session, contact_id) is None
    assert alice.get(f"/contacts/{contact_id}").status_code == 404


def test_deleting_missing_contact(alice):
    """Ensure deleting a contact that does not exist is not found."""
    assert alice.delete("/contacts/999").status_code == 404
