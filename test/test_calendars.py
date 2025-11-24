from fastapi.testclient import TestClient
from servicios.calendar_service.app.main import app
import json

client = TestClient(app)

def test_list_calendars():
    response = client.get("/calendars/")
    data = response.json()
    print(f"==>> test_list_calendars: {json.dumps(data, indent=4)}")
    assert response.status_code == 200
    assert isinstance(data, list)
    assert len(data) == 0  # Asumimos que la BBDD de test está vacía al inicio

def test_create_calendar():
    new_calendar_data = {
        "titulo": "Calendario de prueba",
        "organizador": "Test de Pytest",
        "palabras_clave": ["testing", "fastapi"],
        "es_publico": True,
        "idCalendarioPadre": None
    }
    response = client.post("/calendars/", json=new_calendar_data)
    assert response.status_code == 201
    data = response.json()
    print(f"==>> test_create_calendar: {json.dumps(data, indent=4)}")
    assert data["titulo"] == new_calendar_data["titulo"]
    assert data["organizador"] == new_calendar_data["organizador"]
    assert data["_id"] is not None

# --- Tests para GET /calendars/{id} ---

def test_get_calendar_by_id():
    # Primero, creamos un calendario para tener un ID con el que trabajar
    new_calendar_data = {
        "titulo": "Calendario para GET",
        "organizador": "Test GET",
        "palabras_clave": [],
        "es_publico": False
    }
    create_response = client.post("/calendars/", json=new_calendar_data)
    assert create_response.status_code == 201
    created_calendar = create_response.json()
    calendar_id = created_calendar["_id"]

    # Ahora, lo solicitamos por su ID
    response = client.get(f"/calendars/{calendar_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["_id"] == calendar_id
    assert data["titulo"] == "Calendario para GET"

def test_get_calendar_not_found():
    # Usamos un UUID que sabemos que no existe
    non_existent_id = "12345678-1234-5678-1234-567812345678"
    response = client.get(f"/calendars/{non_existent_id}")
    assert response.status_code == 404

# --- Tests para PUT /calendars/{id} ---

def test_update_calendar():
    # Creamos un calendario
    new_calendar_data = {"titulo": "Original", "organizador": "Test PUT"}
    create_response = client.post("/calendars/", json=new_calendar_data)
    calendar_id = create_response.json()["_id"]

    # Lo actualizamos
    update_data = {"titulo": "Actualizado", "organizador": "Test PUT", "es_publico": False}
    response = client.put(f"/calendars/{calendar_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["titulo"] == "Actualizado"
    assert data["es_publico"] is False

def test_update_calendar_not_found():
    non_existent_id = "12345678-1234-5678-1234-567812345678"
    update_data = {"titulo": "No existo", "organizador": "Test"}
    response = client.put(f"/calendars/{non_existent_id}", json=update_data)
    assert response.status_code == 404

# --- Tests para DELETE /calendars/{id} ---

def test_delete_calendar():
    # Creamos un calendario
    new_calendar_data = {"titulo": "Para Borrar", "organizador": "Test DELETE"}
    create_response = client.post("/calendars/", json=new_calendar_data)
    calendar_id = create_response.json()["_id"]

    # Lo eliminamos
    delete_response = client.delete(f"/calendars/{calendar_id}")
    assert delete_response.status_code == 204

    # Verificamos que ya no existe (debería dar 404)
    get_response = client.get(f"/calendars/{calendar_id}")
    assert get_response.status_code == 404

def test_delete_calendar_not_found():
    non_existent_id = "12345678-1234-5678-1234-567812345678"
    response = client.delete(f"/calendars/{non_existent_id}")
    assert response.status_code == 404




