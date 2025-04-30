from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from models.models import Farms, UserRoleFarm, AreaUnits, FarmStates, UserRoleFarmStates
from dataBase import get_db_session
from utils.response import session_token_invalid_response
from utils.response import create_response
from utils.state import get_state
from use_cases.create_farm_use_case import create_farm_use_case
from use_cases.verify_session_token_use_case import verify_session_token
from use_cases.list_farms_use_case import list_farms_use_case
from use_cases.update_farm_use_case import update_farm_use_case
from use_cases.get_farm_use_case import get_farm_use_case
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class CreateFarmRequest(BaseModel):
    """
    Modelo de datos para la creación de una finca.

    **Atributos**:
    - **name**: Nombre de la finca (cadena de texto). Debe ser un valor no vacío ni contener solo espacios.
    - **area**: Área de la finca (float). Debe ser un número positivo mayor que cero.
    - **areaUnit**: Unidad de medida del área (cadena de texto). Debe ser una unidad de medida válida como 'hectáreas' o 'metros cuadrados'.
    """
    name: str
    area: float
    areaUnit: str
    
class ListFarmResponse(BaseModel):
    """
    Modelo de datos para la respuesta al listar fincas.

    **Atributos**:
    - **farm_id**: ID único de la finca (entero).
    - **name**: Nombre de la finca (cadena de texto).
    - **area**: Área de la finca (float), representada en la unidad de medida especificada.
    - **area_unit**: Unidad de medida del área (cadena de texto).
    - **farm_state**: Estado actual de la finca (cadena de texto), por ejemplo, 'Activo' o 'Inactivo'.
    - **role**: Rol del usuario en relación a la finca (cadena de texto), como 'Propietario' o 'Administrador'.
    """
    farm_id: int
    name: str
    area: float
    area_unit: str
    farm_state: str
    role: str
    
class UpdateFarmRequest(BaseModel):
    """
    Modelo de datos para la actualización de una finca existente.

    **Atributos**:
    - **farm_id**: ID de la finca a actualizar (entero). Debe existir una finca con este ID.
    - **name**: Nuevo nombre de la finca (cadena de texto). No puede estar vacío ni contener solo espacios.
    - **area**: Nueva área de la finca (float). Debe ser un número positivo mayor que cero.
    - **areaUnit**: Nueva unidad de medida del área (cadena de texto). Debe ser una unidad de medida válida como 'hectáreas' o 'metros cuadrados'.
    """
    farm_id: int
    name: str
    area: float
    areaUnit: str

@router.post("/create-farm")
def create_farm(request: CreateFarmRequest, session_token: str, db: Session = Depends(get_db_session)):
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
    return create_farm_use_case(request, user, db)

@router.post("/list-farm")
def list_farm(session_token: str, db: Session = Depends(get_db_session)):
    """
    Endpoint para listar las fincas activas asociadas a un usuario autenticado mediante un token de sesión.
    """
    user = verify_session_token(session_token)
    if not user:
        logger.warning("Token de sesión inválido o usuario no encontrado")
        return session_token_invalid_response()
    return list_farms_use_case(user, db, ListFarmResponse)

@router.post("/update-farm")
def update_farm(request: UpdateFarmRequest, session_token: str, db: Session = Depends(get_db_session)):
    """
    Endpoint para actualizar la información de una finca asociada a un usuario autenticado.
    """
    user = verify_session_token(session_token)
    if not user:
        logger.warning("Token de sesión inválido o usuario no encontrado")
        return session_token_invalid_response()
    return update_farm_use_case(request, user, db)

@router.get("/get-farm/{farm_id}")
def get_farm(farm_id: int, session_token: str, db: Session = Depends(get_db_session)):
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
    return get_farm_use_case(farm_id, user, db, ListFarmResponse)

@router.post("/delete-farm/{farm_id}")
def delete_farm(farm_id: int, session_token: str, db: Session = Depends(get_db_session)):
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

    # Obtener el state "Activo" para la finca y user_role_farm
    active_farm_state = get_state(db, "Activo", "Farms")
    if not active_farm_state:
        logger.error("No se encontró el estado 'Activo' para el tipo 'Farms'")
        return create_response("error", "Estado 'Activo' no encontrado para Farms", status_code=400)

    active_urf_state = get_state(db, "Activo", "user_role_farm")
    if not active_urf_state:
        logger.error("No se encontró el estado 'Activo' para el tipo 'user_role_farm'")
        return create_response("error", "Estado 'Activo' no encontrado para user_role_farm", status_code=400)

    # Verificar si el usuario está asociado con la finca activa
    user_role_farm = db.query(UserRoleFarm).join(Farms).filter(
        UserRoleFarm.user_id == user.user_id,
        UserRoleFarm.farm_id == farm_id,
        UserRoleFarm.user_role_farm_state_id == active_urf_state.user_role_farm_state_id,
        Farms.farm_state_id == active_farm_state.farm_state_id
    ).first()

    if not user_role_farm:
        logger.warning("El usuario no está asociado con la finca que intenta eliminar")
        return create_response("error", "No tienes permiso para eliminar esta finca")

    # Verificar permisos para eliminar la finca
    role_permission = db.query(RolePermission).join(Permissions).filter(
        RolePermission.role_id == user_role_farm.role_id,
        Permissions.name == "delete_farm"
    ).first()

    if not role_permission:
        logger.warning("El rol del usuario no tiene permiso para eliminar la finca")
        return create_response("error", "No tienes permiso para eliminar esta finca")

    try:
        farm = db.query(Farms).filter(Farms.farm_id == farm_id).first()

        if not farm:
            logger.warning("Finca no encontrada")
            return create_response("error", "Finca no encontrada")

        # Cambiar el estado de la finca a "Inactiva"
        inactive_farm_state = get_state(db, "Inactiva", "Farms")

        if not inactive_farm_state:
            logger.error("No se encontró el estado 'Inactiva' para el tipo 'Farms'")
            raise HTTPException(status_code=400, detail="No se encontró el estado 'Inactiva' para el tipo 'Farms'.")

        farm.farm_state_id = inactive_farm_state.farm_state_id

        # Cambiar el estado de todas las relaciones en user_role_farm a "Inactiva"
        inactive_urf_state = get_state(db, "Inactiva", "user_role_farm")

        if not inactive_urf_state:
            logger.error("No se encontró el estado 'Inactiva' para el tipo 'user_role_farm'")
            raise HTTPException(status_code=400, detail="No se encontró el estado 'Inactiva' para el tipo 'user_role_farm'.")

        user_role_farms = db.query(UserRoleFarm).filter(UserRoleFarm.farm_id == farm_id).all()
        for urf in user_role_farms:
            urf.user_role_farm_state_id = inactive_urf_state.user_role_farm_state_id

        db.commit()
        logger.info("Finca y relaciones en user_role_farm puestas en estado 'Inactiva' para la finca con ID %s", farm_id)
        return create_response("success", "Finca puesta en estado 'Inactiva' correctamente")

    except Exception as e:
        db.rollback()
        logger.error("Error al desactivar la finca: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Error al desactivar la finca: {str(e)}")
