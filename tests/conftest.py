"""
Configuración global para pytest.
Este archivo se ejecuta antes de la recolección de tests y configura
las variables de entorno necesarias para evitar errores de conexión a la base de datos.
"""
import os
import pytest

# Configurar variables de entorno para tests antes de cualquier importación
os.environ.setdefault("PGHOST", "localhost")
os.environ.setdefault("PGPORT", "5432")
os.environ.setdefault("PGDATABASE", "test_db")
os.environ.setdefault("PGUSER", "test_user")
os.environ.setdefault("PGPASSWORD", "test_password")

# Configurar para que pytest no intente conectarse a una base de datos real
os.environ["TESTING"] = "true" 