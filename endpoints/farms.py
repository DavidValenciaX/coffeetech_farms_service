from fastapi import APIRouter, Depends
from pydantic import BaseModel
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

logger = logging.getLogger(__name__)

router = APIRouter()

class CreateFarmRequest(BaseModel):
    """
    Modelo de datos para la creación de una finca.

    **Atributos**:
    - **name**: Nombre de la finca (cadena de texto). Debe ser un valor no vacío ni contener solo espacios.
    - **area**: Área de la finca (float). Debe ser un número positivo mayor que cero.
    - **area_unit_id**: ID de la unidad de medida del área (entero). Debe ser un ID válido existente en la tabla area_units.
    """
    name: str
    area: float
    area_unit_id: int
    
class ListFarmResponse(BaseModel):
    """
    Modelo de datos para la respuesta al listar fincas.

    **Atributos**:
    - **farm_id**: ID único de la finca (entero).
    - **name**: Nombre de la finca (cadena de texto).
    - **area**: Área de la finca (float), representada en la unidad de medida especificada.
    - **area_unit_id**: ID de la unidad de medida del área (entero).
    - **area_unit**: Nombre de la unidad de medida (cadena de texto).
    - **farm_state_id**: ID del estado de la finca (entero).
    - **farm_state**: Nombre del estado actual de la finca (cadena de texto), por ejemplo, 'Activo' o 'Inactivo'.
    - **user_role_id**: ID del rol del usuario en relación a la finca (entero).
    - **role**: Nombre del rol del usuario en relación a la finca (cadena de texto).
    """
    farm_id: int
    name: str
    area: float
    area_unit_id: int
    area_unit: str  # Nombre descriptivo de la unidad
    farm_state_id: int
    farm_state: str  # Nombre descriptivo del estado
    user_role_id: int
    role: str  # Nombre descriptivo del rol
    
class UpdateFarmRequest(BaseModel):
    """
    Modelo de datos para la actualización de una finca existente.

    **Atributos**:
    - **farm_id**: ID de la finca a actualizar (entero). Debe existir una finca con este ID.
    - **name**: Nuevo nombre de la finca (cadena de texto). No puede estar vacío ni contener solo espacios.
    - **area**: Nueva área de la finca (float). Debe ser un número positivo mayor que cero.
    - **area_unit_id**: ID de la unidad de medida del área (entero). Debe ser un ID válido existente en la tabla area_units.
    """
    farm_id: int
    name: str
    area: float
    area_unit_id: int

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
