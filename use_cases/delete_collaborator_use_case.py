from sqlalchemy.orm import Session
from sqlalchemy import func
from models.models import Farms, UserRoleFarm
from utils.response import create_response
from utils.state import get_state
import logging

logger = logging.getLogger(__name__)

def delete_collaborator(delete_request, farm_id: int, user, db: Session):
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

    # Obtener la asociación UserRoleFarm del usuario con la finca
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

    # Obtener el colaborador a eliminar
    collaborator = db.query(Users).filter(Users.user_id == delete_request.collaborator_user_id).first()
    if not collaborator:
        logger.error(f"Colaborador con ID {delete_request.collaborator_user_id} no encontrado")
        return create_response(
            "error",
            "Colaborador no encontrado",
            status_code=404
        )

    logger.info(f"Colaborador a eliminar: {collaborator.name} (ID: {collaborator.user_id})")

    # Verificar que el colaborador esté asociado activamente a la finca
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

    # Verificar que el usuario no esté intentando eliminar su propia asociación
    if user.user_id == collaborator.user_id:
        logger.warning(f"Usuario {user.name} intentó eliminar su propia asociación con la finca")
        return create_response(
            "error",
            "No puedes eliminar tu propia asociación con la finca",
            status_code=403
        )

    # Determinar el permiso requerido basado en el rol del colaborador
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

    # Obtener el permiso requerido
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

    # Verificar si el usuario tiene el permiso necesario
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

    # Eliminar la asociación del colaborador con la finca (Actualizar el estado a 'Inactivo')
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

    # Devolver la respuesta exitosa
    return create_response(
        "success",
        f"Colaborador '{collaborator.name}' eliminado exitosamente de la finca '{farm.name}'",
        status_code=200
    )
