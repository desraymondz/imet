# Integration tests for auth:
# - Protected routes reject anonymous requests
# - Register and login set a session cookie
# - Email case and whitespace do not create a second account

import pytest

# Routes that require a session cookie
PROTECTED_ROUTES = [
    ("GET", "/auth/me", None),
    ("GET", "/contacts/", None),
    ("POST", "/contacts/", {"display_name": "Desmond"}),
    ("GET", "/contacts/1", None),
    ("PATCH", "/contacts/1", {"display_name": "Desmond"}),
    ("POST", "/recall/search", {"query": "who likes hiking?"}),
    ("POST", "/recall/fts", {"query": "hiking"}),
    ("POST", "/captures/build-contact", {"transcript": "Met Desmond"}),
]


@pytest.mark.parametrize(("method", "path", "body"), PROTECTED_ROUTES)
def test_protected_routes(client, method, path, body):
    """Ensure an anonymous request to a protected route is rejected."""
    response = client.request(method, path, json=body)

    assert response.status_code == 401


def test_register_sets_session_cookie(client):
    """Ensure register sets an HttpOnly session cookie."""
    response = client.post(
        "/auth/register", json={"email": "alice@test.com", "password": "password123"}
    )
    assert response.status_code == 200

    # The browser must not be able to read the token from JavaScript
    cookie_header = response.headers["set-cookie"].lower()
    assert "httponly" in cookie_header
    assert "samesite=lax" in cookie_header
    assert "path=/" in cookie_header
    assert client.get("/auth/me").json()["email"] == "alice@test.com"


def test_login_with_correct_password_starts_session(client, make_user):
    """Ensure login with the correct password starts a session."""
    make_user("alice@test.com")
    # A fresh client with no cookie
    response = client.post(
        "/auth/login", data={"username": "alice@test.com", "password": "password123"}
    )

    assert response.status_code == 200
    assert "httponly" in response.headers["set-cookie"].lower()
    assert client.get("/auth/me").json()["email"] == "alice@test.com"


@pytest.mark.parametrize(
    ("username", "password"),
    [
        ("alice@test.com", "wrong-password"),  # wrong password
        ("nobody@test.com", "password123"),  # unknown email
    ],
)
def test_login_failures_are_rejected(client, make_user, username, password):
    """Ensure a wrong password and an unknown email get the same rejection feedback."""
    make_user("alice@test.com")

    response = client.post("/auth/login", data={"username": username, "password": password})

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"
    assert client.get("/auth/me").status_code == 401


def test_email_case_and_whitespace(client, make_user):
    """Ensure email case and whitespace do not create a second account."""
    make_user("  Alice@Test.COM  ")

    # Registering the same email in another case is refused
    duplicate = client.post(
        "/auth/register", json={"email": "ALICE@test.com", "password": "password123"}
    )
    assert duplicate.status_code == 400

    # Logging in with a different case still finds the account
    login = client.post(
        "/auth/login", data={"username": "ALICE@TEST.com", "password": "password123"}
    )
    assert login.status_code == 200
    assert client.get("/auth/me").json()["email"] == "alice@test.com"

def test_login_with_overlong_password(client, make_user):
    """Ensure a password over bcrypt's 72-byte limit is rejected."""
    make_user("alice@test.com")

    response = client.post("/auth/login", data={"username": "alice@test.com", "password": "a" * 100})

    assert response.status_code == 401