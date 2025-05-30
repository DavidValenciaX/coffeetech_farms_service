from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from dataBase import get_db_session
from adapters.user_client import verify_session_token
from utils.response import session_token_invalid_response
from utils.response import create_response
from use_cases.create_plot_use_case import create_plot
from use_cases.update_plot_use_case import (
    update_plot_general_info,
    update_plot_location,
)
from use_cases.list_plots_use_case import list_plots
from use_cases.get_plot_use_case import get_plot
from use_cases.delete_plot_use_case import delete_plot
import logging
from domain.schemas import (
    CreatePlotRequest,
    UpdatePlotGeneralInfoRequest,
    UpdatePlotLocationRequest,
)

router = APIRouter()

logger = logging.getLogger(__name__)

INVALID_SESSION_TOKEN_MESSAGE = "Token de sesión inválido o usuario no encontrado"

# Endpoint para crear un lote
@router.post("/create-plot")
def create_plot_endpoint(request: CreatePlotRequest, session_token: str, db: Session = Depends(get_db_session)):
    """
    Crea un nuevo lote (plot) en una finca.
    """
    user = verify_session_token(session_token)
    if not user:
        logger.warning(INVALID_SESSION_TOKEN_MESSAGE)
        return session_token_invalid_response()
    return create_plot(request, user, db)

# Endpoint para actualizar información general del lote
@router.post("/update-plot-general-info", summary="Actualizar información general del lote", description="Actualiza el nombre y la variedad de café de un lote específico.")
def update_plot_general_info_endpoint(request: UpdatePlotGeneralInfoRequest, session_token: str, db: Session = Depends(get_db_session)):
    """
    Actualiza el nombre y la variedad de café de un lote específico.
    """
    user = verify_session_token(session_token)
    if not user:
        logger.warning(INVALID_SESSION_TOKEN_MESSAGE)
        return session_token_invalid_response()
    return update_plot_general_info(request, user, db)

# Endpoint para actualizar la ubicación del lote
@router.post("/update-plot-location", summary="Actualizar ubicación del lote", description="Actualiza las coordenadas geográficas (latitud, longitud, altitud) de un lote específico.")
def update_plot_location_endpoint(request: UpdatePlotLocationRequest, session_token: str, db: Session = Depends(get_db_session)):
    """
    Actualiza las coordenadas geográficas (latitud, longitud, altitud) de un lote específico.
    """
    user = verify_session_token(session_token)
    if not user:
        logger.warning(INVALID_SESSION_TOKEN_MESSAGE)
        return session_token_invalid_response()
    return update_plot_location(request, user, db)

# Endpoint para listar todos los lotes de una finca
@router.get("/list-plots/{farm_id}", summary="Listar los lotes de una finca")
def list_plots_endpoint(farm_id: int, session_token: str, db: Session = Depends(get_db_session)):
    """
    Obtiene una lista de todos los lotes activos de una finca específica.

    - **farm_id**: ID de la finca.
    - **session_token**: Token de sesión del usuario autenticado.

    **Respuestas**:
    - **200**: Lista de lotes obtenida exitosamente.
    - **400**: Token inválido o falta de permisos para ver los lotes.
    - **404**: Finca no encontrada o inactiva.
    - **500**: Error al obtener la lista de lotes.
    """
    user = verify_session_token(session_token)
    if not user:
        logger.warning(INVALID_SESSION_TOKEN_MESSAGE)
        return session_token_invalid_response()
    return list_plots(farm_id, user, db)

# Endpoint para obtener la información de un lote específico
@router.get("/get-plot/{plot_id}", summary="Obtener información de un lote")
def get_plot_endpoint(plot_id: int, session_token: str, db: Session = Depends(get_db_session)):
    """
    Obtiene la información detallada de un lote específico.

    - **plot_id**: ID del lote.
    - **session_token**: Token de sesión del usuario autenticado.

    **Respuestas**:
    - **200**: Información del lote obtenida exitosamente.
    - **400**: Token inválido o falta de permisos para ver el lote.
    - **404**: Lote no encontrado o inactivo.
    - **500**: Error al obtener la información del lote.
    """

    user = verify_session_token(session_token)
    if not user:
        logger.warning(INVALID_SESSION_TOKEN_MESSAGE)
        return session_token_invalid_response()

    return get_plot(plot_id, user, db)

# Endpoint para eliminar un lote (poner en estado 'Inactivo')
@router.post("/delete-plot/{plot_id}", summary="Eliminar un lote (estado inactivo)")
def delete_plot_endpoint(plot_id: int, session_token: str, db: Session = Depends(get_db_session)):
    """
    Elimina un lote (cambia su estado a 'Inactivo').

    - **plot_id**: ID del lote.
    - **session_token**: Token de sesión del usuario autenticado.

    **Respuestas**:
    - **200**: Lote eliminado exitosamente (estado 'Inactivo').
    - **400**: Token inválido o falta de permisos para eliminar el lote.
    - **404**: Lote no encontrado o ya inactivo.
    - **500**: Error al eliminar el lote.
    """

    user = verify_session_token(session_token)
    if not user:
        logger.warning(INVALID_SESSION_TOKEN_MESSAGE)
        return create_response("error", INVALID_SESSION_TOKEN_MESSAGE)

    return delete_plot(plot_id, user, db)
