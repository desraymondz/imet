# Integration tests for ownership:
# - Another user's contact cannot be read, updated or deleted
# - List and recall return only your own contacts

# Mock user
DESMOND = {"display_name": "Desmond", "profile_text": "Loves hiking in the Peak District"}
DAVE = {"display_name": "Dave", "profile_text": "Also loves hiking every weekend"}


def create_contact(user_client, payload) -> int:
    """Create a contact and return its id."""
    response = user_client.post("/contacts/", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_reading_another_users_contact(alice, bob):
    """Ensure reading another user's contact is not found."""
    contact_id = create_contact(alice, DESMOND)
    assert bob.get(f"/contacts/{contact_id}").status_code == 404

def test_updating_another_users_contact(alice, bob):
    """Ensure updating another user's contact is not found and leaves it unchanged."""
    contact_id = create_contact(alice, DESMOND)
    assert bob.patch(f"/contacts/{contact_id}", json={"display_name": "Hacked"}).status_code == 404
    assert alice.get(f"/contacts/{contact_id}").json()["display_name"] == "Desmond"

def test_deleting_another_users_contact(alice, bob):
    """Ensure deleting another user's contact is not found and leaves it in place."""
    contact_id = create_contact(alice, DESMOND)
    assert bob.delete(f"/contacts/{contact_id}").status_code == 404
    assert alice.get(f"/contacts/{contact_id}").status_code == 200

def test_listing_contacts(alice, bob):
    """Ensure listing contacts returns only your own."""
    create_contact(alice, DESMOND)
    create_contact(bob, DAVE)
    assert [c["display_name"] for c in alice.get("/contacts/").json()] == ["Desmond"]
    assert [c["display_name"] for c in bob.get("/contacts/").json()] == ["Dave"]

def test_recall_search(alice, bob):
    """Ensure recall search returns only your own contacts."""
    create_contact(alice, DESMOND)
    create_contact(bob, DAVE)
    results = bob.post("/recall/search", json={"query": "who likes hiking?"}).json()["results"]

    assert [r["contact"]["display_name"] for r in results] == ["Dave"]