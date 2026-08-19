from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from src import app as app_module


@pytest.fixture
def client():
    with TestClient(app_module.app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def isolated_activities():
    original_activities = deepcopy(app_module.activities)
    yield
    app_module.activities.clear()
    app_module.activities.update(original_activities)


def test_root_redirects_to_static_index(client):
    # Arrange
    redirect_path = "/"

    # Act
    response = client.get(redirect_path, follow_redirects=False)

    # Assert
    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_get_activities_returns_activity_data(client):
    # Arrange
    expected_activity = app_module.activities["Chess Club"]

    # Act
    response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    assert response.json()["Chess Club"] == expected_activity


def test_signup_adds_participant_and_rejects_duplicate(client):
    # Arrange
    activity_name = "Art Club"
    email = "student@example.com"

    # Act
    signup_response = client.post(
        f"/activities/{activity_name}/signup", params={"email": email}
    )
    duplicate_response = client.post(
        f"/activities/{activity_name}/signup", params={"email": email}
    )

    # Assert
    assert signup_response.status_code == 200
    assert email in app_module.activities[activity_name]["participants"]
    assert duplicate_response.status_code == 400
    assert duplicate_response.json()["detail"] == (
        "Student already signed up for this activity"
    )


def test_signup_rejects_unknown_activity(client):
    # Arrange
    activity_name = "Unknown Club"
    email = "student@example.com"

    # Act
    response = client.post(
        f"/activities/{activity_name}/signup", params={"email": email}
    )

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_unregister_removes_participant(client):
    # Arrange
    activity_name = "Art Club"
    email = "student@example.com"
    app_module.activities[activity_name]["participants"].append(email)

    # Act
    response = client.delete(
        f"/activities/{activity_name}/signup", params={"email": email}
    )

    # Assert
    assert response.status_code == 200
    assert email not in app_module.activities[activity_name]["participants"]
    assert response.json()["message"] == (
        f"Unregistered {email} from {activity_name}"
    )


@pytest.mark.parametrize(
    "activity_name,email,expected_detail",
    [
        ("Unknown Club", "student@example.com", "Activity not found"),
        (
            "Art Club",
            "student@example.com",
            "Student is not signed up for this activity",
        ),
    ],
)
def test_unregister_rejects_invalid_participant(client, activity_name, email, expected_detail):
    # Arrange
    endpoint = f"/activities/{activity_name}/signup"

    # Act
    response = client.delete(endpoint, params={"email": email})

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == expected_detail