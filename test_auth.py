import pytest

from app import app, db, User, limiter


@pytest.fixture
def client(tmp_path):
    # Configure the application for testing.
    app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret-key",
        SESSION_COOKIE_SECURE=False,
        SQLALCHEMY_DATABASE_URI=(
            f"sqlite:///{tmp_path / 'test_auth.db'}"
        ),
    )

    # Clear rate-limit counters so tests don't affect one another.
    limiter.reset()

    with app.app_context():
        db.drop_all()
        db.create_all()

    with app.test_client() as test_client:
        yield test_client

    with app.app_context():
        db.session.remove()
        db.drop_all()


def register_user(client):
    return client.post(
        "/register",
        json={
            "username": "student123",
            "password": "StrongPassword123!",
        },
    )


def login_user(client):
    return client.post(
        "/login",
        json={
            "username": "student123",
            "password": "StrongPassword123!",
        },
    )


def test_home_page(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json["message"] == (
        "Secure Authentication Lab is running."
    )


def test_successful_registration(client):
    response = register_user(client)

    assert response.status_code == 201
    assert response.json["message"] == (
        "Account created successfully."
    )


def test_duplicate_registration(client):
    first_response = register_user(client)
    second_response = register_user(client)

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_password_is_hashed(client):
    register_user(client)

    with app.app_context():
        user = User.query.filter_by(
            username="student123"
        ).first()

        assert user is not None
        assert user.password_hash != "StrongPassword123!"
        assert user.password_hash.startswith("scrypt:")


def test_login_success(client):
    register_user(client)

    response = login_user(client)

    assert response.status_code == 200
    assert response.json["message"] == "Login successful."


def test_login_with_wrong_password(client):
    register_user(client)

    response = client.post(
        "/login",
        json={
            "username": "student123",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json["error"] == (
        "Invalid username or password."
    )


def test_protected_route_requires_login(client):
    response = client.get("/me")

    assert response.status_code == 401
    assert response.json["error"] == "Authentication required."


def test_authenticated_user_can_access_profile(client):
    register_user(client)

    login_response = login_user(client)
    assert login_response.status_code == 200

    response = client.get("/me")

    assert response.status_code == 200
    assert response.json["username"] == "student123"


def test_logout(client):
    register_user(client)
    login_user(client)

    logout_response = client.post("/logout")

    assert logout_response.status_code == 200
    assert logout_response.json["message"] == (
        "Logged out successfully."
    )

    profile_response = client.get("/me")

    assert profile_response.status_code == 401


def test_short_password_is_rejected(client):
    response = client.post(
        "/register",
        json={
            "username": "student123",
            "password": "short",
        },
    )

    assert response.status_code == 400
    assert "password" in response.json["error"].lower()


def test_invalid_username_is_rejected(client):
    response = client.post(
        "/register",
        json={
            "username": "ab",
            "password": "StrongPassword123!",
        },
    )

    assert response.status_code == 400


def test_invalid_json_body_is_rejected(client):
    response = client.post(
        "/register",
        data="not json",
        content_type="application/json",
    )

    assert response.status_code == 400


def test_login_rate_limit(client):
    register_user(client)

    responses = [
        client.post(
            "/login",
            json={
                "username": "student123",
                "password": "WrongPassword123!",
            },
        )
        for _ in range(6)
    ]

    assert all(response.status_code == 401 for response in responses[:5])
    assert responses[5].status_code == 429
