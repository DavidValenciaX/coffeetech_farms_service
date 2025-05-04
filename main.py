from fastapi import FastAPI
from endpoints import farms, utils, collaborators, plots
from utils.logger import setup_logger

# Setup logging for the entire application
logger = setup_logger()
logger.info("Starting CoffeeTech Farms Service")

app = FastAPI()

# Incluir las rutas de gestión de fincas
app.include_router(farms.router, prefix="/farm", tags=["Fincas"])

# Incluir las rutas de gestión de lotes
app.include_router(plots.router, prefix="/plots", tags=["Lotes"])

# Incluir las rutas de colaboradores
app.include_router(collaborators.router, prefix="/collaborators", tags=["Colaboradores"])

# Incluir las rutas de utilidades (roles y unidades de medida)
app.include_router(utils.router, prefix="/utils", tags=["Utilidades"])

@app.get("/", include_in_schema=False)
def read_root():
    """
    Ruta raíz que retorna un mensaje de bienvenida.

    Returns:
        dict: Un diccionario con un mensaje de bienvenida.
    """
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to the FastAPI application CoffeeTech Farms Service!"}