from sqlalchemy.orm import Session
from domain.schemas import EditCollaboratorRoleRequest
from models.models import Farms, UserRoleFarm
from utils.response import create_response
from utils.state import get_state
import logging
from adapters.user_client import (
    get_user_role_ids,
    get_role_name_for_user_role,
    get_role_permissions_for_user_role,
    get_collaborators_info,
    update_user_role,
    get_user_role_id_for_farm
)

logger = logging.getLogger(__name__)

def edit_collaborator_role(edit_request: EditCollaboratorRoleRequest, farm_id: int, user, db: Session):
    # Verificar que la finca exista
    farm = db.query(Farms).filter(Farms.farm_id == farm_id).first()
    if not farm:
        logger.error(f"Finca con ID {farm_id} no encontrada")
        return create_response(
            "error",
            "Finca no encontrada",
            status_code=404
        )

    logger.info(f"Finca encontrada: {farm.name} (ID: {farm.farm_id})")

    # Obtener el estado 'Activo' para 'user_role_farm'
    urf_active_state = get_state(db, "Activo", "user_role_farm")
    if not urf_active_state:
        logger.error("Estado 'Activo' no encontrado para 'user_role_farm'")
        return create_response(
            "error",
            "Estado 'Activo' no encontrado para 'user_role_farm'",
            status_code=400
        )

    # Obtener los user_role_ids del usuario autenticado
    try:
        user_role_ids = get_user_role_ids(user.user_id)
    except Exception as e:
        logger.error("No se pudieron obtener los user_role_ids: %s", str(e))
        return create_response("error", "No se pudieron obtener los roles del usuario", status_code=500)

    # Verificar si el usuario tiene un user_role_farm activo en la finca
    user_role_farm = db.query(UserRoleFarm).filter(
        UserRoleFarm.user_role_id.in_(user_role_ids),
        UserRoleFarm.farm_id == farm_id,
        UserRoleFarm.user_role_farm_state_id == urf_active_state.user_role_farm_state_id
    ).first()
    if not user_role_farm:
        logger.warning(f"Usuario no está asociado a la finca ID {farm_id}")
        return create_response(
            "error",
            "No estás asociado a esta finca",
            status_code=403
        )

    # Obtener el nombre del rol del usuario autenticado
    current_user_role_name = get_role_name_for_user_role(user_role_farm.user_role_id)
    if not current_user_role_name or current_user_role_name == "Unknown":
        logger.error(f"Rol del usuario no encontrado para user_role_id {user_role_farm.user_role_id}")
        return create_response(
            "error",
            "Rol del usuario no encontrado",
            status_code=500
        )

    logger.info(f"Rol del usuario: {current_user_role_name}")

    # Get the user_role_id for the collaborator in this farm
    collaborator_user_role_id = get_user_role_id_for_farm(edit_request.collaborator_id, farm_id, db)
    if not collaborator_user_role_id:
        logger.error(f"No se encontró el rol del colaborador con ID {edit_request.collaborator_id} en la finca {farm_id}")
        return create_response(
            "error",
            "Colaborador no encontrado en esta finca",
            status_code=404
        )

    # Obtener info del colaborador a editar usando get_collaborators_info
    try:
        collaborator_info_list = get_collaborators_info([collaborator_user_role_id])
        collaborator_info = collaborator_info_list[0] if collaborator_info_list else None
    except Exception as e:
        logger.error(f"Error al obtener info del colaborador: {str(e)}")
        collaborator_info = None

    if not collaborator_info:
        logger.error(f"Colaborador con user_role_id {collaborator_user_role_id} no encontrado")
        return create_response(
            "error",
            "Colaborador no encontrado",
            status_code=404
        )

    logger.info(f"Colaborador a editar: {collaborator_info['user_name']} (user_role_id: {collaborator_user_role_id})")

    # Verificar que el usuario no esté intentando cambiar su propio rol
    if user_role_farm.user_role_id == collaborator_user_role_id:
        logger.warning("Intento de cambiar el propio rol")
        return create_response(
            "error",
            "No puedes cambiar tu propio rol",
            status_code=403
        )

    # Verificar que el colaborador esté asociado a la finca y activo
    collaborator_role_farm = db.query(UserRoleFarm).filter(
        UserRoleFarm.user_role_id == collaborator_user_role_id,
        UserRoleFarm.farm_id == farm_id,
        UserRoleFarm.user_role_farm_state_id == urf_active_state.user_role_farm_state_id
    ).first()
    if not collaborator_role_farm:
        logger.error(f"Colaborador no está asociado a la finca ID {farm_id}")
        return create_response(
            "error",
            "El colaborador no está asociado a esta finca",
            status_code=404
        )

    # Obtener el rol actual del colaborador
    collaborator_current_role_name = get_role_name_for_user_role(collaborator_user_role_id)
    if not collaborator_current_role_name or collaborator_current_role_name == "Unknown":
        logger.error(f"Rol actual del colaborador no encontrado para user_role_id {collaborator_user_role_id}")
        return create_response(
            "error",
            "Rol actual del colaborador no encontrado",
            status_code=500
        )

    logger.info(f"Rol actual del colaborador: {collaborator_current_role_name}")

    # Verificar si el colaborador ya tiene el rol deseado
    if collaborator_current_role_name == edit_request.new_role:
        logger.info(f"El colaborador ya tiene el rol '{edit_request.new_role}'")
        return create_response(
            "error",
            f"El colaborador ya tiene el rol '{edit_request.new_role}'",
            status_code=400
        )

    # Verificar permisos necesarios para cambiar al nuevo rol
    permission_name = ""
    if edit_request.new_role == "Administrador de finca":
        permission_name = "edit_administrator_farm"
    elif edit_request.new_role == "Operador de campo":
        permission_name = "edit_operator_farm"

    if not permission_name:
        logger.error(f"Rol deseado '{edit_request.new_role}' no es válido")
        return create_response(
            "error",
            "Rol deseado no válido",
            status_code=400
        )

    # Verificar si el usuario tiene el permiso necesario
    permissions = get_role_permissions_for_user_role(user_role_farm.user_role_id)
    if permission_name not in permissions:
        logger.warning(f"Usuario no tiene permiso '{permission_name}'")
        return create_response(
            "error",
            f"No tienes permiso para asignar el rol '{edit_request.new_role}'",
            status_code=403
        )

    logger.info(f"Usuario tiene permiso '{permission_name}'")

    # Verificar la jerarquía de roles
    hierarchy = {
        "Propietario": ["Administrador de finca", "Operador de campo"],
        "Administrador de finca": ["Operador de campo"],
        "Operador de campo": []
    }

    if current_user_role_name not in hierarchy:
        logger.error(f"Rol del usuario '{current_user_role_name}' no está definido en la jerarquía")
        return create_response(
            "error",
            "Rol del usuario no está definido en la jerarquía",
            status_code=500
        )

    allowed_roles_to_assign = hierarchy.get(current_user_role_name, [])

    if edit_request.new_role not in allowed_roles_to_assign:
        logger.warning(f"Rol '{edit_request.new_role}' no puede ser asignado por un usuario con rol '{current_user_role_name}'")
        return create_response(
            "error",
            f"No tienes permiso para asignar el rol '{edit_request.new_role}'",
            status_code=403
        )

    logger.info(f"Rol '{edit_request.new_role}' puede ser asignado por un usuario con rol '{current_user_role_name}'")

    # Actualizar el rol del colaborador llamando al microservicio de usuarios
    try:
        update_user_role(collaborator_user_role_id, edit_request.new_role)
        logger.info(f"Rol del colaborador actualizado a '{edit_request.new_role}'")
    except Exception as e:
        logger.error(f"Error al actualizar el rol del colaborador: {str(e)}")
        return create_response(
            "error",
            "Error al actualizar el rol del colaborador",
            status_code=500
        )

    # Devolver la respuesta exitosa
    return create_response(
        "success",
        f"Rol del colaborador '{collaborator_info['user_name']}' actualizado a '{edit_request.new_role}' exitosamente",
        status_code=200
    )
