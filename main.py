from fastapi import FastAPI
from endpoints import farms, utils, collaborators, plots
from dataBase import engine
from models.models import Base
import logging

app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Incluir las rutas de utilidades (roles y unidades de medida)
app.include_router(utils.router, prefix="/utils", tags=["Utilidades"])

# Incluir las rutas de gestión de fincas
app.include_router(farms.router, prefix="/farm", tags=["Fincas"])

# Incluir las rutas de gestión de lotes
app.include_router(plots.router, prefix="/plots", tags=["Lotes"])

# Incluir las rutas de colaboradores
app.include_router(collaborators.router, prefix="/collaborators", tags=["Collaborators"])

@app.get("/")
def read_root():
    """
    Ruta raíz que retorna un mensaje de bienvenida.

    Returns:
        dict: Un diccionario con un mensaje de bienvenida.
    """
    return {"message": "Welcome to the FastAPI application CoffeeTech!"}