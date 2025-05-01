from sqlalchemy.orm import Session
from sqlalchemy import func
from models.models import Farms, UserRoleFarm, Users, Roles, Permissions, RolePermission
from utils.response import create_response
from utils.state import get_state
import logging

logger = logging.getLogger(__name__)

def edit_collaborator_role(edit_request, farm_id: int, user, db: Session):

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
    urf_active_state = get_state(db, "Activo", "user_role_farm") # Use get_state

    if not urf_active_state:
        logger.error("Estado 'Activo' no encontrado para 'user_role_farm'")
        return create_response(
            "error",
            "Estado 'Activo' no encontrado para 'user_role_farm'",
            status_code=400
        )

    logger.info(f"Estado 'Activo' encontrado: {urf_active_state.name} (ID: {urf_active_state.user_role_farm_state_id})") # Use correct ID field

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

    # Obtener el colaborador a editar
    collaborator = db.query(Users).filter(Users.user_id == edit_request.collaborator_user_id).first()
    if not collaborator:
        logger.error(f"Colaborador con ID {edit_request.collaborator_user_id} no encontrado")
        return create_response(
            "error",
            "Colaborador no encontrado",
            status_code=404
        )

    logger.info(f"Colaborador a editar: {collaborator.name} (ID: {collaborator.user_id})")

    # Verificar que el usuario no esté intentando cambiar su propio rol
    if user.user_id == collaborator.user_id:
        logger.warning(f"Usuario {user.name} intentó cambiar su propio rol")
        return create_response(
            "error",
            "No puedes cambiar tu propio rol",
            status_code=403
        )

    # Obtener el estado 'Activo' para el colaborador
    collaborator_role_farm = db.query(UserRoleFarm).filter(
        UserRoleFarm.user_id == collaborator.user_id,
        UserRoleFarm.farm_id == farm_id,
        UserRoleFarm.user_role_farm_state_id == urf_active_state.user_role_farm_state_id
    ).first()

    if not collaborator_role_farm:
        logger.error(f"Colaborador {collaborator.name} no está asociado a la finca ID {farm_id}")
        return create_response(
            "error",
            "El colaborador no está asociado a esta finca",
            status_code=404
        )

    # Obtener el rol actual del colaborador
    collaborator_current_role = db.query(Roles).filter(Roles.role_id == collaborator_role_farm.role_id).first()
    if not collaborator_current_role:
        logger.error(f"Rol con ID {collaborator_role_farm.role_id} no encontrado para el colaborador")
        return create_response(
            "error",
            "Rol actual del colaborador no encontrado",
            status_code=500
        )

    logger.info(f"Rol actual del colaborador: {collaborator_current_role.name}")

    # Verificar si el colaborador ya tiene el rol deseado
    if collaborator_current_role.name == edit_request.new_role:
        logger.info(f"El colaborador {collaborator.name} ya tiene el rol '{edit_request.new_role}'")
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

    # Obtener el permiso requerido
    required_permission = db.query(Permissions).filter(
        func.lower(Permissions.name) == permission_name.lower()
    ).first()

    if not required_permission:
        logger.error(f"Permiso '{permission_name}' no encontrado en la base de datos")
        return create_response(
            "error",
            f"Permiso '{permission_name}' no encontrado en la base de datos",
            status_code=500
        )

    logger.info(f"Permiso requerido para asignar '{edit_request.new_role}': {required_permission.name}")

    # Verificar si el usuario tiene el permiso necesario
    has_permission = db.query(RolePermission).filter(
        RolePermission.role_id == user_role_farm.role_id,
        RolePermission.permission_id == required_permission.permission_id
    ).first()

    if not has_permission:
        logger.warning(f"Usuario {user.name} no tiene permiso '{permission_name}'")
        return create_response(
            "error",
            f"No tienes permiso para asignar el rol '{edit_request.new_role}'",
            status_code=403
        )

    logger.info(f"Usuario {user.name} tiene permiso '{permission_name}'")

    # Verificar la jerarquía de roles
    # Definir la jerarquía
    hierarchy = {
        "Propietario": ["Administrador de finca", "Operador de campo"],
        "Administrador de finca": ["Operador de campo"],
        "Operador de campo": []
    }

    if current_user_role.name not in hierarchy:
        logger.error(f"Rol del usuario '{current_user_role.name}' no está definido en la jerarquía")
        return create_response(
            "error",
            "Rol del usuario no está definido en la jerarquía",
            status_code=500
        )

    allowed_roles_to_assign = hierarchy.get(current_user_role.name, [])

    if edit_request.new_role not in allowed_roles_to_assign:
        logger.warning(f"Rol '{edit_request.new_role}' no puede ser asignado por un usuario con rol '{current_user_role.name}'")
        return create_response(
            "error",
            f"No tienes permiso para asignar el rol '{edit_request.new_role}'",
            status_code=403
        )

    logger.info(f"Rol '{edit_request.new_role}' puede ser asignado por un usuario con rol '{current_user_role.name}'")

    # Obtener el rol objetivo
    target_role = db.query(Roles).filter(Roles.name == edit_request.new_role).first()
    if not target_role:
        logger.error(f"Rol '{edit_request.new_role}' no encontrado en la base de datos")
        return create_response(
            "error",
            f"Rol '{edit_request.new_role}' no encontrado en la base de datos",
            status_code=500
        )

    logger.info(f"Rol objetivo encontrado: {target_role.name} (ID: {target_role.role_id})")

    # Actualizar el rol del colaborador
    try:
        collaborator_role_farm.role_id = target_role.role_id
        db.commit()
        logger.info(f"Rol del colaborador {collaborator.name} actualizado a '{target_role.name}'")
    except Exception as e:
        db.rollback()
        logger.error(f"Error al actualizar el rol del colaborador: {str(e)}")
        return create_response(
            "error",
            "Error al actualizar el rol del colaborador",
            status_code=500
        )

    # Devolver la respuesta exitosa
    return create_response(
        "success",
        f"Rol del colaborador '{collaborator.name}' actualizado a '{target_role.name}' exitosamente",
        status_code=200
    )
