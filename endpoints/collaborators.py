from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any
from pydantic import BaseModel, EmailStr, Field
from models.models import Farms, UserRoleFarm
from dataBase import get_db_session
from utils.response import create_response, session_token_invalid_response
from sqlalchemy import func
from utils.state import get_state
from adapters.user_client import verify_session_token
import logging
from use_cases.list_collaborators_use_case import list_collaborators
from use_cases.edit_collaborator_role_use_case import edit_collaborator_role

logger = logging.getLogger(__name__)

router = APIRouter()

# Modelo Pydantic actualizado para la respuesta de colaborador
class Collaborator(BaseModel):
    """
    Modelo Pydantic para representar un colaborador.

    Attributes:
        user_id (int): ID del usuario del colaborador.
        name (str): Nombre del colaborador.
        email (EmailStr): Correo electrónico del colaborador.
        role (str): Rol del colaborador.
    """
    user_id: int
    name: str
    email: EmailStr
    role: str

    class Config:
        from_attributes = True
        
# Modelo Pydantic para la solicitud de edición de rol
class EditCollaboratorRoleRequest(BaseModel):
    """
    Modelo Pydantic para la solicitud de edición de rol de un colaborador.

    Attributes:
        collaborator_user_id (int): ID del usuario colaborador cuyo rol se desea editar.
        new_role (str): Nuevo rol que se asignará al colaborador.
    """
    collaborator_user_id: int = Field(..., alias="collaborator_user_id")
    new_role: str

    class Config:
        populate_by_name = True
        from_attributes = True

    def validate_input(self):
        """Valida que el nuevo rol sea válido."""
        if self.new_role not in ["Administrador de finca", "Operador de campo"]:
            raise ValueError("El rol debe ser 'Administrador de finca' o 'Operador de campo'.")
        
# Modelo Pydantic para la solicitud de eliminación de colaborador
class DeleteCollaboratorRequest(BaseModel):
    """
    Modelo Pydantic para la solicitud de eliminación de un colaborador.

    Attributes:
        collaborator_user_id (int): ID del usuario colaborador que se desea eliminar.
    """
    collaborator_user_id: int = Field(..., alias="collaborator_user_id")

    class Config:
        populate_by_name = True
        from_attributes = True

    def validate_input(self):
        if self.collaborator_user_id <= 0:
            raise ValueError("El `collaborator_user_id` debe ser un entero positivo.")

@router.get("/list-collaborators", response_model=Dict[str, Any])
def list_collaborators_endpoint(
    farm_id: int,
    session_token: str,
    db: Session = Depends(get_db_session)
):
    """
    Endpoint para listar los colaboradores de una finca específica.
    """
    # 1. Verificar el session_token y obtener el usuario autenticado
    user = verify_session_token(session_token)
    if not user:
        return session_token_invalid_response()
    logger.info(f"Usuario autenticado: {user.name} (ID: {user.user_id})")
    return list_collaborators(farm_id, user, db=db)

@router.post("/edit-collaborator-role", response_model=Dict[str, Any])
def edit_collaborator_role_endpoint(
    edit_request: EditCollaboratorRoleRequest,
    farm_id: int,
    session_token: str,
    db: Session = Depends(get_db_session)
):
    """
    ### Descripción:
    Endpoint para editar el rol de un colaborador en una finca específica.

    ### Parámetros:
    - **edit_request (EditCollaboratorRoleRequest)**: Objeto con los campos `collaborator_user_id` y `new_role`, que contiene la información del colaborador y el nuevo rol que se le asignará.
    - **farm_id (int)**: ID de la finca donde se cambiará el rol del colaborador.
    - **session_token (str)**: Token de sesión del usuario autenticado que está realizando la acción.
    - **db (Session)**: Sesión de la base de datos obtenida mediante la dependencia `get_db_session`.

    ### Proceso:
    1. **Validación de entrada**: Se valida la solicitud recibida.
    2. **Autenticación**: Se verifica el `session_token` para autenticar al usuario.
    3. **Verificación de la finca**: Se comprueba si la finca existe.
    4. **Estado 'Activo'**: Se busca el estado 'Activo' para roles en fincas (`user_role_farm`).
    5. **Rol actual del usuario**: Se verifica el rol del usuario que realiza la acción en la finca.
    6. **Verificación del colaborador**: Se obtiene al colaborador cuyo rol se desea editar.
    7. **Evitar auto-cambio de rol**: El usuario no puede cambiar su propio rol.
    8. **Rol del colaborador actual**: Se comprueba el rol actual del colaborador en la finca.
    9. **Permisos necesarios**: Se verifican los permisos del usuario para asignar el nuevo rol.
    10. **Jerarquía de roles**: Se valida la jerarquía de roles para determinar si el usuario puede asignar el nuevo rol.
    11. **Rol objetivo**: Se obtiene el rol que se desea asignar al colaborador.
    12. **Actualización del rol**: Se actualiza el rol del colaborador en la base de datos.
    
    ### Respuestas:
    - **200 (success)**: El rol del colaborador ha sido actualizado exitosamente.
    - **400 (error)**: Error de validación de entrada o intento de asignar el mismo rol.
    - **403 (error)**: El usuario no tiene permisos suficientes o intentó cambiar su propio rol.
    - **404 (error)**: La finca o el colaborador no existen.
    - **500 (error)**: Error interno del servidor al procesar la solicitud.

    """

    # Validar la entrada
    try:
        edit_request.validate_input()
    except ValueError as e:
        logger.error(f"Validación de entrada fallida: {str(e)}")
        return create_response(
            "error",
            str(e),
            status_code=400
        )
        
    user = verify_session_token(session_token)
    if not user:
        return session_token_invalid_response()

    logger.info(f"Usuario autenticado: {user.name} (ID: {user.user_id})")

    # Lógica de negocio delegada al use case
    return edit_collaborator_role(edit_request, farm_id, user, db)

@router.post("/delete-collaborator", response_model=Dict[str, Any])
def delete_collaborator_endpoint(
    delete_request: DeleteCollaboratorRequest,
    farm_id: int,
    session_token: str,
    db: Session = Depends(get_db_session)
):
    """
    Elimina un colaborador de una finca específica.

    Parámetros:
    - delete_request (DeleteCollaboratorRequest): Cuerpo de la solicitud que contiene el ID del colaborador a eliminar.
    - farm_id (int): ID de la finca desde la que se eliminará al colaborador.
    - session_token (str): Token de sesión del usuario que realiza la solicitud.
    - db (Session): Sesión de la base de datos proporcionada por FastAPI con `Depends`.

    Retornos:
    - Dict[str, Any]: Respuesta indicando éxito o error con el mensaje adecuado.

    Posibles Respuestas:
    - 200: Colaborador eliminado exitosamente.
    - 400: Error en la validación de la solicitud o algún otro fallo.
    - 403: El usuario no tiene permisos o está intentando eliminarse a sí mismo.
    - 404: Finca o colaborador no encontrado.
    - 500: Error en el servidor o al actualizar la base de datos.
    """

    # 1. Validar la entrada
    try:
        delete_request.validate_input()
    except ValueError as e:
        logger.error(f"Validación de entrada fallida: {str(e)}")
        return create_response(
            "error",
            str(e),
            status_code=400
        )

    # 2. Verificar el session_token y obtener el usuario autenticado
    user = verify_session_token(session_token)
    if not user:
        return session_token_invalid_response()

    logger.info(f"Usuario autenticado: {user.name} (ID: {user.user_id})")

    # 3. Verificar que la finca exista
    farm = db.query(Farms).filter(Farms.farm_id == farm_id).first()
    if not farm:
        logger.error(f"Finca con ID {farm_id} no encontrada")
        return create_response(
            "error",
            "Finca no encontrada",
            status_code=404
        )

    logger.info(f"Finca encontrada: {farm.name} (ID: {farm.farm_id})")

    # 4. Obtener el estado 'Activo' para 'user_role_farm'
    urf_active_state = get_state(db, "Activo", "user_role_farm") # Use get_state

    if not urf_active_state:
        logger.error("Estado 'Activo' no encontrado para 'user_role_farm'")
        return create_response(
            "error",
            "Estado 'Activo' no encontrado para 'user_role_farm'",
            status_code=400
        )

    logger.info(f"Estado 'Activo' encontrado: {urf_active_state.name} (ID: {urf_active_state.user_role_farm_state_id})") # Use correct ID field

    # 5. Obtener la asociación UserRoleFarm del usuario con la finca
    user_role_farm = db.query(UserRoleFarm).filter(
        UserRoleFarm.user_id == user.user_id,
        UserRoleFarm.farm_id == farm_id,
        UserRoleFarm.user_role_farm_state_id == urf_active_state.user_role_farm_state_id
    ).first()

    if not user_role_farm:
        logger.warning(f"Usuario {user.name} no está asociado a la finca ID {farm_id}")
        return create_response(
            "error",
            "No estás asociado a esta finca",
            status_code=403
        )

    # Obtener el rol del usuario que realiza la acción
    current_user_role = db.query(Roles).filter(Roles.role_id == user_role_farm.role_id).first()
    if not current_user_role:
        logger.error(f"Rol con ID {user_role_farm.role_id} no encontrado")
        return create_response(
            "error",
            "Rol del usuario no encontrado",
            status_code=500
        )

    logger.info(f"Rol del usuario: {current_user_role.name}")

    # 6. Obtener el colaborador a eliminar
    collaborator = db.query(Users).filter(Users.user_id == delete_request.collaborator_user_id).first()
    if not collaborator:
        logger.error(f"Colaborador con ID {delete_request.collaborator_user_id} no encontrado")
        return create_response(
            "error",
            "Colaborador no encontrado",
            status_code=404
        )

    logger.info(f"Colaborador a eliminar: {collaborator.name} (ID: {collaborator.user_id})")

    # 7. Verificar que el colaborador esté asociado activamente a la finca
    collaborator_role_farm = db.query(UserRoleFarm).filter(
        UserRoleFarm.user_id == collaborator.user_id,
        UserRoleFarm.farm_id == farm_id,
        UserRoleFarm.user_role_farm_state_id == urf_active_state.user_role_farm_state_id
    ).first()

    if not collaborator_role_farm:
        logger.error(f"Colaborador {collaborator.name} no está asociado activamente a la finca ID {farm_id}")
        return create_response(
            "error",
            "El colaborador no está asociado activamente a esta finca",
            status_code=404
        )

    # 8. Verificar que el usuario no esté intentando eliminar su propia asociación
    if user.user_id == collaborator.user_id:
        logger.warning(f"Usuario {user.name} intentó eliminar su propia asociación con la finca")
        return create_response(
            "error",
            "No puedes eliminar tu propia asociación con la finca",
            status_code=403
        )

    # 9. Determinar el permiso requerido basado en el rol del colaborador
    collaborator_role = db.query(Roles).filter(Roles.role_id == collaborator_role_farm.role_id).first()
    if not collaborator_role:
        logger.error(f"Rol con ID {collaborator_role_farm.role_id} no encontrado para el colaborador")
        return create_response(
            "error",
            "Rol del colaborador no encontrado",
            status_code=500
        )

    logger.info(f"Rol del colaborador: {collaborator_role.name}")

    if collaborator_role.name == "Administrador de finca":
        required_permission_name = "delete_administrator_farm"
    elif collaborator_role.name == "Operador de campo":
        required_permission_name = "delete_operator_farm"
    else:
        logger.error(f"Rol '{collaborator_role.name}' no reconocido para eliminación")
        return create_response(
            "error",
            f"Rol '{collaborator_role.name}' no reconocido para eliminación",
            status_code=400
        )

    # 10. Obtener el permiso requerido
    required_permission = db.query(Permissions).filter(
        func.lower(Permissions.name) == required_permission_name.lower()
    ).first()

    if not required_permission:
        logger.error(f"Permiso '{required_permission_name}' no encontrado en la base de datos")
        return create_response(
            "error",
            f"Permiso '{required_permission_name}' no encontrado en la base de datos",
            status_code=500
        )

    logger.info(f"Permiso requerido para eliminar '{collaborator_role.name}': {required_permission.name}")

    # 11. Verificar si el usuario tiene el permiso necesario
    has_permission = db.query(RolePermission).filter(
        RolePermission.role_id == user_role_farm.role_id,
        RolePermission.permission_id == required_permission.permission_id
    ).first()

    if not has_permission:
        logger.warning(f"Usuario {user.name} no tiene permiso '{required_permission.name}'")
        return create_response(
            "error",
            f"No tienes permiso para eliminar a un colaborador con rol '{collaborator_role.name}'",
            status_code=403
        )

    logger.info(f"Usuario {user.name} tiene permiso '{required_permission.name}'")

    # 12. Eliminar la asociación del colaborador con la finca (Actualizar el estado a 'Inactivo')
    try:
        # Obtener el estado 'Inactivo' para 'user_role_farm'
        urf_inactive_state = get_state(db, "Inactivo", "user_role_farm") # Use get_state

        if not urf_inactive_state:
            logger.error("Estado 'Inactivo' no encontrado para 'user_role_farm'")
            return create_response(
                "error",
                "Estado 'Inactivo' no encontrado para 'user_role_farm'",
                status_code=500
            )

        collaborator_role_farm.user_role_farm_state_id = urf_inactive_state.user_role_farm_state_id
        db.commit()
        logger.info(f"Colaborador {collaborator.name} eliminado de la finca ID {farm_id} exitosamente")
    except Exception as e:
        db.rollback()
        logger.error(f"Error al eliminar el colaborador: {str(e)}")
        return create_response(
            "error",
            "Error al eliminar el colaborador",
            status_code=500
        )

    # 13. Devolver la respuesta exitosa
    return create_response(
        "success",
        f"Colaborador '{collaborator.name}' eliminado exitosamente de la finca '{farm.name}'",
        status_code=200
    )
