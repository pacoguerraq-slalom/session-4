from fastapi.testclient import TestClient

from src.app import app, audit_log, sessions


client = TestClient(app)


def setup_function():
    sessions.clear()
    audit_log.clear()


def login():
    response = client.post("/auth/login", json={
        "username": "practice-lead",
        "password": "change-me-now",
    })
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def login_as_consultant():
    response = client.post("/auth/login", json={
        "username": "consultant",
        "password": "consultant-demo",
    })
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_invalid_login_is_rejected():
    response = client.post("/auth/login", json={
        "username": "practice-lead",
        "password": "wrong-password",
    })

    assert response.status_code == 401


def test_registration_requires_authentication():
    response = client.post(
        "/capabilities/Cloud%20Architecture/register",
        params={"email": "new.consultant@slalom.com"},
    )

    assert response.status_code == 401


def test_consultant_cannot_change_capability_registrations():
    headers = login_as_consultant()
    response = client.post(
        "/capabilities/Cloud%20Architecture/register",
        params={"email": "new.consultant@slalom.com"},
        headers=headers,
    )

    assert response.status_code == 403


def test_practice_lead_can_register_and_audit_action():
    headers = login()
    response = client.post(
        "/capabilities/Cloud%20Architecture/register",
        params={"email": "new.consultant@slalom.com"},
        headers=headers,
    )

    assert response.status_code == 200
    assert audit_log[-1] == {
        "username": "practice-lead",
        "action": "register",
        "capability": "Cloud Architecture",
    }


def test_logout_invalidates_session():
    headers = login()
    assert client.post("/auth/logout", headers=headers).status_code == 200

    response = client.get("/auth/me", headers=headers)

    assert response.status_code == 401