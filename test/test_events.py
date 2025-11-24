from fastapi.testclient import TestClient
from servicios.calendar_service.app.main import app
import json

client = TestClient(app)

def test_list_events():
    response = client.get("/events/")
    data = response.json()
    print(f"==>> test_list_events: {json.dumps(data, indent=4)}")
    assert response.status_code == 200
    assert isinstance(data, list)

def test_create_event():
    new_event = {
        "title": "Test Event",
        "description": "This is a test event",
        "start_time": "2023-01-01T10:00:00",
        "end_time": "2023-01-01T12:00:00"
    }
    response = client.post("/events/", json=new_event)
    data = response.json()
    print(f"==>> test_create_event: {json.dumps(data, indent=4)}")
    assert response.status_code == 201
    assert data["id"] is not None
    assert data["title"] == new_event["title"]
    assert data["description"] == new_event["description"]
    
def test_get_event_by_id():
    # Primero, creamos un evento para tener un ID con el que trabajar
    new_event = {
        "title": "Event for GET",
        "description": "This event is for testing GET by ID",
        "start_time": "2023-02-01T10:00:00",
        "end_time": "2023-02-01T12:00:00"
    }
    create_response = client.post("/events/", json=new_event)
    assert create_response.status_code == 201
    created_event = create_response.json()
    event_id = created_event["id"]

    # Ahora, lo solicitamos por su ID
    response = client.get(f"/events/{event_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == event_id
    assert data["title"] == "Event for GET"
    assert data["description"] == "This event is for testing GET by ID"
    
def test_get_event_not_found():
    # Usamos un UUID que sabemos que no existe
    non_existent_id = "12345678-1234-5678-1234-567812345678"
    response = client.get(f"/events/{non_existent_id}")
    assert response.status_code == 404
    
def test_update_event():
    # Primero, creamos un evento para tener un ID con el que trabajar
    new_event = {
        "title": "Event to Update",
        "description": "This event will be updated",
        "start_time": "2023-03-01T10:00:00",
        "end_time": "2023-03-01T12:00:00"
    }
    create_response = client.post("/events/", json=new_event)
    assert create_response.status_code == 201
    created_event = create_response.json()
    event_id = created_event["id"]

    # Ahora, actualizamos el evento
    updated_event = {
        "title": "Updated Event Title",
        "description": "This event has been updated",
        "start_time": "2023-03-01T11:00:00",
        "end_time": "2023-03-01T13:00:00"
    }
    update_response = client.put(f"/events/{event_id}", json=updated_event)
    assert update_response.status_code == 200
    data = update_response.json()
    assert data["id"] == event_id
    assert data["title"] == updated_event["title"]
    assert data["description"] == updated_event["description"]
    
def test_update_event_not_found():
    non_existent_id = "12345678-1234-5678-1234-567812345678"
    updated_event = {
        "title": "Non-existent Event",
        "description": "Trying to update a non-existent event",
        "start_time": "2023-04-01T10:00:00",
        "end_time": "2023-04-01T12:00:00"
    }
    response = client.put(f"/events/{non_existent_id}", json=updated_event)
    assert response.status_code == 404
    
def test_delete_event():
    # Primero, creamos un evento para tener un ID con el que trabajar
    new_event = {
        "title": "Event to Delete",
        "description": "This event will be deleted",
        "start_time": "2023-05-01T10:00:00",
        "end_time": "2023-05-01T12:00:00"
    }
    create_response = client.post("/events/", json=new_event)
    assert create_response.status_code == 201
    created_event = create_response.json()
    event_id = created_event["id"]

    # Ahora, eliminamos el evento
    delete_response = client.delete(f"/events/{event_id}")
    assert delete_response.status_code == 204

    # Verificamos que ya no existe
    get_response = client.get(f"/events/{event_id}")
    assert get_response.status_code == 404
    
def test_delete_event_not_found():
    non_existent_id = "12345678-1234-5678-1234-567812345678"
    response = client.delete(f"/events/{non_existent_id}")
    assert response.status_code == 404
