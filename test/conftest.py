import pytest
from pymongo import MongoClient
import os

# Importamos las colecciones que serán "monkeypatched"
from app.database import calendarios_collection, eventos_collection

# Cambiamos el scope a "function". Esta fixture se ejecutará ANTES de CADA test.
@pytest.fixture(scope="function", autouse=True)
def test_db(monkeypatch):
    # Nombre para la base de datos de prueba
    test_db_name = "KalendasDB_Test"
    uri = os.getenv('MONGODB_URI')
    if not uri:
        raise ValueError("La variable de entorno MONGODB_URI no está configurada.")

    # Creamos un cliente que apunta a la BBDD de test
    test_client = MongoClient(uri, uuidRepresentation='standard')
    test_db = test_client[test_db_name]

    # Reemplazamos los objetos de la BBDD en app.database con los de test
    monkeypatch.setattr("app.database.client", test_client)
    monkeypatch.setattr("app.database.db", test_db)
    monkeypatch.setattr("app.database.calendarios_collection", test_db["calendarios"])
    monkeypatch.setattr("app.database.eventos_collection", test_db["eventos"])

    print(f"\n--- Usando BBDD de test: {test_db_name} ---")

    # Ejecutar tests
    yield

    test_client.drop_database(test_db_name)
    test_client.close()