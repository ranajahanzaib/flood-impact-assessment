import pytest
from fastapi.testclient import TestClient

from services.api.database import init_db
from services.api.main import app


@pytest.fixture
def client():
    init_db()
    with TestClient(app) as test_client:
        yield test_client

def test_health_and_overview(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

    res_ov = client.get("/api/overview")
    assert res_ov.status_code == 200
    data = res_ov.json()
    assert "total_events" in data
    assert "total_newly_flooded_km2" in data

def test_event_crud_lifecycle(client):
    # 1. Create event
    create_payload = {
        "name": "Integration Test Flood Event",
        "country": "Germany",
        "description": "Validation testing event",
        "bounds_geojson": [7.0, 50.0, 7.1, 50.1]
    }
    res = client.post("/api/events", json=create_payload)
    assert res.status_code == 200
    created = res.json()
    event_id = created["id"]
    assert created["name"] == "Integration Test Flood Event"

    # 2. Retrieve event
    res_get = client.get(f"/api/events/{event_id}")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == event_id

    # 3. Update event
    res_patch = client.patch(f"/api/events/{event_id}", json={"description": "Updated description"})
    assert res_patch.status_code == 200
    assert res_patch.json()["description"] == "Updated description"

    # 4. List events
    res_list = client.get("/api/events")
    assert res_list.status_code == 200
    event_ids = [e["id"] for e in res_list.json()]
    assert event_id in event_ids

    # 5. Delete event
    res_del = client.delete(f"/api/events/{event_id}")
    assert res_del.status_code == 200
    res_get_del = client.get(f"/api/events/{event_id}")
    assert res_get_del.status_code == 404
