from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_events():
    response = client.get("/events/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_invalid_team():
    response = client.get("/teams/999999")
    assert response.status_code == 404
    # This verifies your custom error handler works!
    assert response.json()["error"] == "Resource Error"
    