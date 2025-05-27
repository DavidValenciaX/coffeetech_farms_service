from sqlalchemy.orm import Session
from domain.schemas import EditCollaboratorRoleRequest, EditCollaboratorRoleResponse
from models.models import Farms, UserRoleFarm
from utils.response import create_response
from utils.state import get_state
import logging
from adapters.user_client import (
    get_user_role_ids,
    get_role_name_for_user_role,
    get_role_permissions_for_user_role,
    get_collaborators_info,
    get_user_role_id_for_farm,
    get_role_name_by_id,
    create_user_role_for_farm  # Import the new function
)

logger = logging.getLogger(__name__)

# Define role name constants
ADMINISTRADOR_DE_FINCA_ROLE_NAME = "Administrador de finca"
OPERADOR_DE_CAMPO_ROLE_NAME = "Operador de campo"
PROPIETARIO_ROLE_NAME = "Propietario"

def _validate_farm_exists(farm_id: int, db: Session):
    """Validate that the farm exists."""
    farm = db.query(Farms).filter(Farms.farm_id == farm_id).first()
    if not farm:
        logger.error(f"Finca con ID {farm_id} no encontrada")
        return None, create_response("error", "Finca no encontrada", status_code=404)
    
    logger.info(f"Finca encontrada: {farm.name} (ID: {farm.farm_id})")
    return farm, None

def _validate_user_farm_association(user, farm_id: int, db: Session):
    """Validate user is associated with the farm and get their role."""
    urf_active_state = get_state(db, "Activo", "user_role_farm")
    if not urf_active_state:
        logger.error("Estado 'Activo' no encontrado para 'user_role_farm'")
        return None, None, create_response("error", "Estado 'Activo' no encontrado para 'user_role_farm'", status_code=400)

    try:
        user_role_ids = get_user_role_ids(user.user_id)
    except Exception as e:
        logger.error("No se pudieron obtener los user_role_ids: %s", str(e))
        return None, None, create_response("error", "No se pudieron obtener los roles del usuario", status_code=500)

    user_role_farm = db.query(UserRoleFarm).filter(
        UserRoleFarm.user_role_id.in_(user_role_ids),
        UserRoleFarm.farm_id == farm_id,
        UserRoleFarm.user_role_farm_state_id == urf_active_state.user_role_farm_state_id
    ).first()
    
    if not user_role_farm:
        logger.warning(f"Usuario no está asociado a la finca ID {farm_id}")
        return None, None, create_response("error", "No estás asociado a esta finca", status_code=403)

    current_user_role_name = get_role_name_for_user_role(user_role_farm.user_role_id)
    if not current_user_role_name or current_user_role_name == "Unknown":
        logger.error(f"Rol del usuario no encontrado para user_role_id {user_role_farm.user_role_id}")
        return None, None, create_response("error", "Rol del usuario no encontrado", status_code=500)

    logger.info(f"Rol del usuario: {current_user_role_name}")
    return user_role_farm, current_user_role_name, None

def _validate_collaborator(edit_request: EditCollaboratorRoleRequest, farm_id: int, user_role_farm, db: Session):
    """Validate collaborator exists and get their info."""
    collaborator_user_role_id = get_user_role_id_for_farm(edit_request.collaborator_id, farm_id, db)
    if not collaborator_user_role_id:
        logger.error(f"No se encontró el rol del colaborador con ID {edit_request.collaborator_id} en la finca {farm_id}")
        return None, None, None, create_response("error", "Colaborador no encontrado en esta finca", status_code=404)

    try:
        collaborator_info_list = get_collaborators_info([collaborator_user_role_id])
        collaborator_info = collaborator_info_list[0] if collaborator_info_list else None
    except Exception as e:
        logger.error(f"Error al obtener info del colaborador: {str(e)}")
        collaborator_info = None

    if not collaborator_info:
        logger.error(f"Colaborador con user_role_id {collaborator_user_role_id} no encontrado")
        return None, None, None, create_response("error", "Colaborador no encontrado", status_code=404)

    # Check if user is trying to change their own role
    if user_role_farm.user_role_id == collaborator_user_role_id:
        logger.warning("Intento de cambiar el propio rol")
        return None, None, None, create_response("error", "No puedes cambiar tu propio rol", status_code=403)

    urf_active_state = get_state(db, "Activo", "user_role_farm")
    collaborator_role_farm = db.query(UserRoleFarm).filter(
        UserRoleFarm.user_role_id == collaborator_user_role_id,
        UserRoleFarm.farm_id == farm_id,
        UserRoleFarm.user_role_farm_state_id == urf_active_state.user_role_farm_state_id
    ).first()
    
    if not collaborator_role_farm:
        logger.error(f"Colaborador no está asociado a la finca ID {farm_id}")
        return None, None, None, create_response("error", "El colaborador no está asociado a esta finca", status_code=404)

    return collaborator_user_role_id, collaborator_info, collaborator_role_farm, None

def _validate_role_change(collaborator_user_role_id: int, edit_request: EditCollaboratorRoleRequest, current_user_role_name: str, user_role_farm):
    """Validate the role change is allowed."""
    collaborator_current_role_name = get_role_name_for_user_role(collaborator_user_role_id)
    if not collaborator_current_role_name or collaborator_current_role_name == "Unknown":
        logger.error(f"Rol actual del colaborador no encontrado para user_role_id {collaborator_user_role_id}")
        return None, None, create_response("error", "Rol actual del colaborador no encontrado", status_code=500)

    new_role_name = get_role_name_by_id(edit_request.new_role_id)
    if not new_role_name:
        logger.error(f"Rol con ID {edit_request.new_role_id} no encontrado")
        return None, None, create_response("error", f"Rol con ID {edit_request.new_role_id} no encontrado", status_code=400)
    
    if collaborator_current_role_name == new_role_name:
        logger.info(f"El colaborador ya tiene el rol '{new_role_name}'")
        return None, None, create_response("error", f"El colaborador ya tiene el rol '{new_role_name}'", status_code=400)

    # Check permissions and hierarchy
    permission_name = ""
    if new_role_name == ADMINISTRADOR_DE_FINCA_ROLE_NAME:
        permission_name = "edit_administrator_farm"
    elif new_role_name == OPERADOR_DE_CAMPO_ROLE_NAME:
        permission_name = "edit_operator_farm"

    if not permission_name:
        logger.error(f"Rol deseado '{new_role_name}' no es válido")
        return None, None, create_response("error", "Rol deseado no válido", status_code=400)

    permissions = get_role_permissions_for_user_role(user_role_farm.user_role_id)
    if permission_name not in permissions:
        logger.warning(f"Usuario no tiene permiso '{permission_name}'")
        return None, None, create_response("error", f"No tienes permiso para asignar el rol '{new_role_name}'", status_code=403)

    # Check role hierarchy
    hierarchy = {
        PROPIETARIO_ROLE_NAME: [ADMINISTRADOR_DE_FINCA_ROLE_NAME, OPERADOR_DE_CAMPO_ROLE_NAME],
        ADMINISTRADOR_DE_FINCA_ROLE_NAME: [OPERADOR_DE_CAMPO_ROLE_NAME],
        OPERADOR_DE_CAMPO_ROLE_NAME: []
    }

    allowed_roles_to_assign = hierarchy.get(current_user_role_name, [])
    if new_role_name not in allowed_roles_to_assign:
        logger.warning(f"Rol '{new_role_name}' no puede ser asignado por un usuario con rol '{current_user_role_name}'")
        return None, None, create_response("error", f"No tienes permiso para asignar el rol '{new_role_name}'", status_code=403)

    return collaborator_current_role_name, new_role_name, None

def edit_collaborator_role(edit_request: EditCollaboratorRoleRequest, farm_id: int, user, db: Session) -> EditCollaboratorRoleResponse:
    # Validate farm exists
    _, error = _validate_farm_exists(farm_id, db)
    if error:
        return error

    # Validate user farm association
    user_role_farm, current_user_role_name, error = _validate_user_farm_association(user, farm_id, db)
    if error:
        return error

    # Validate collaborator
    collaborator_user_role_id, collaborator_info, collaborator_role_farm, error = _validate_collaborator(
        edit_request, farm_id, user_role_farm, db
    )
    if error:
        return error

    # Validate role change
    _, new_role_name, error = _validate_role_change(
        collaborator_user_role_id, edit_request, current_user_role_name, user_role_farm
    )
    if error:
        return error

    # Update collaborator role
    try:
        collaborator_user_id = collaborator_info['user_id']
        new_user_role_id = create_user_role_for_farm(collaborator_user_id, edit_request.new_role_id)
        collaborator_role_farm.user_role_id = new_user_role_id
        db.commit()
        
        logger.info(f"Rol del colaborador actualizado a '{new_role_name}' solo para la finca {farm_id}")
    except Exception as e:
        logger.error(f"Error al actualizar el rol del colaborador: {str(e)}")
        db.rollback()
        return create_response("error", "Error al actualizar el rol del colaborador", status_code=500)

    return EditCollaboratorRoleResponse(
        status="success",
        message=f"Rol del colaborador '{collaborator_info['user_name']}' actualizado a '{new_role_name}' exitosamente"
    )
