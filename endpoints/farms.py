from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from dataBase import get_db_session
from utils.response import session_token_invalid_response
from utils.response import create_response
from use_cases.create_farm_use_case import create_farm
from adapters.user_client import verify_session_token
from use_cases.list_farms_use_case import list_farms
from use_cases.update_farm_use_case import update_farm
from use_cases.get_farm_use_case import get_farm
from use_cases.delete_farm_use_case import delete_farm
import logging
from domain.schemas import CreateFarmRequest, ListFarmResponse, UpdateFarmRequest

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/create-farm")
def create_farm_endpoint(request: CreateFarmRequest, session_token: str, db: Session = Depends(get_db_session)):
    """
    Crea una nueva finca y asigna al usuario como propietario.

    **Parámetros**:
    - **request**: Objeto que contiene los datos de la finca (nombre, área, y unidad de medida).
    - **session_token**: Token de sesión del usuario.
    - **db**: Sesión de base de datos, se obtiene automáticamente.

    **Respuestas**:
    - **200 OK**: Finca creada y usuario asignado correctamente.
    - **400 Bad Request**: Si los datos de la finca no son válidos o no se encuentra el estado requerido.
    - **401 Unauthorized**: Si el token de sesión es inválido o el usuario no tiene permisos.
    - **500 Internal Server Error**: Si ocurre un error al intentar crear la finca o asignar el usuario.
    """
    user = verify_session_token(session_token)
    if not user:
        logger.warning("Token de sesión inválido o usuario no encontrado")
        return session_token_invalid_response()
    return create_farm(request, user, db)

@router.post("/list-farm")
def list_farm_endpoint(session_token: str, db: Session = Depends(get_db_session)):
    """
    Endpoint para listar las fincas activas asociadas a un usuario autenticado mediante un token de sesión.
    """
    user = verify_session_token(session_token)
    if not user:
        logger.warning("Token de sesión inválido o usuario no encontrado")
        return session_token_invalid_response()
    return list_farms(user, db, ListFarmResponse)

@router.post("/update-farm")
def update_farm_endpoint(request: UpdateFarmRequest, session_token: str, db: Session = Depends(get_db_session)):
    """
    Endpoint para actualizar la información de una finca asociada a un usuario autenticado.
    """
    user = verify_session_token(session_token)
    if not user:
        logger.warning("Token de sesión inválido o usuario no encontrado")
        return session_token_invalid_response()
    return update_farm(request, user, db)

@router.get("/get-farm/{farm_id}")
def get_farm_endpoint(farm_id: int, session_token: str, db: Session = Depends(get_db_session)):
    """
    Obtiene los detalles de una finca específica en la que el usuario tiene permisos.
    
    **Parámetros:**
    - `farm_id` (int): ID de la finca a consultar.
    - `session_token` (str): Token de sesión del usuario que está haciendo la solicitud.

    **Respuesta exitosa (200):**
    - **Descripción**: Devuelve la información de la finca, incluyendo nombre, área, unidad de medida, estado y rol del usuario en relación a la finca.

    **Errores:**
    - **401 Unauthorized**: Si el token de sesión es inválido o el usuario no se encuentra.
    - **400 Bad Request**: Si no se encuentra el estado "Activo" para la finca o para la relación `user_role_farm`.
    - **404 Not Found**: Si la finca no se encuentra o no pertenece al usuario.
    """
    user = verify_session_token(session_token)
    if not user:
        logger.warning("Token de sesión inválido o usuario no encontrado")
        return session_token_invalid_response()
    return get_farm(farm_id, user, db, ListFarmResponse)

@router.post("/delete-farm/{farm_id}")
def delete_farm_endpoint(farm_id: int, session_token: str, db: Session = Depends(get_db_session)):
    """
    Elimina (inactiva) una finca específica.

    **Parámetros:**
    - `farm_id` (int): ID de la finca a eliminar.
    - `session_token` (str): Token de sesión del usuario que está haciendo la solicitud.

    **Respuesta exitosa (200):**
    - **Descripción**: Indica que la finca ha sido desactivada correctamente.

    **Errores:**
    - **401 Unauthorized**: Si el token de sesión es inválido o el usuario no se encuentra.
    - **400 Bad Request**: Si no se encuentra el estado "Activo" para la finca o para la relación `user_role_farm`.
    - **403 Forbidden**: Si el usuario no tiene permiso para eliminar la finca.
    - **404 Not Found**: Si la finca no se encuentra.
    - **500 Internal Server Error**: Si ocurre un error al desactivar la finca.

    """
    # Verificar el token de sesión
    user = verify_session_token(session_token)
    if not user:
        logger.warning("Token de sesión inválido o usuario no encontrado")
        return create_response("error", "Token de sesión inválido o usuario no encontrado")
    
    return delete_farm(farm_id, user, db)
