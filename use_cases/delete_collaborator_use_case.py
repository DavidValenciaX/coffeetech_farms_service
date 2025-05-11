from sqlalchemy.orm import Session
from models.models import Farms, UserRoleFarm
from utils.response import create_response
from utils.state import get_state
import logging
from adapters.user_client import (
    get_user_role_ids,
    get_role_name_for_user_role,
    get_role_permissions_for_user_role,
    get_collaborators_info,
    delete_user_role,
    get_user_role_id_for_farm
)
from domain.schemas import DeleteCollaboratorResponse

logger = logging.getLogger(__name__)

def delete_collaborator(delete_request, farm_id: int, user, db: Session) -> DeleteCollaboratorResponse:
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

    # Obtener el user_role_id del colaborador en esta finca
    collaborator_user_role_id = get_user_role_id_for_farm(delete_request.collaborator_id, farm_id, db)
    if not collaborator_user_role_id:
        logger.error(f"No se encontró el rol del colaborador con ID {delete_request.collaborator_id} en la finca {farm_id}")
        return create_response(
            "error",
            "Colaborador no encontrado en esta finca",
            status_code=404
        )

    # Obtener info del colaborador a eliminar usando get_collaborators_info
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

    logger.info(f"Colaborador a eliminar: {collaborator_info['user_name']} (user_role_id: {collaborator_user_role_id})")

    # Verificar que el colaborador esté asociado activamente a la finca
    collaborator_role_farm = db.query(UserRoleFarm).filter(
        UserRoleFarm.user_role_id == collaborator_user_role_id,
        UserRoleFarm.farm_id == farm_id,
        UserRoleFarm.user_role_farm_state_id == urf_active_state.user_role_farm_state_id
    ).first()
    if not collaborator_role_farm:
        logger.error(f"Colaborador no está asociado activamente a la finca ID {farm_id}")
        return create_response(
            "error",
            "El colaborador no está asociado activamente a esta finca",
            status_code=404
        )

    # Verificar que el usuario no esté intentando eliminar su propia asociación
    if user_role_farm.user_role_id == collaborator_user_role_id:
        logger.warning("Intento de eliminar su propia asociación con la finca")
        return create_response(
            "error",
            "No puedes eliminar tu propia asociación con la finca",
            status_code=403
        )

    # Obtener el rol del colaborador
    collaborator_role_name = get_role_name_for_user_role(collaborator_user_role_id)
    if not collaborator_role_name or collaborator_role_name == "Unknown":
        logger.error(f"Rol del colaborador no encontrado para user_role_id {collaborator_user_role_id}")
        return create_response(
            "error",
            "Rol del colaborador no encontrado",
            status_code=500
        )

    logger.info(f"Rol del colaborador: {collaborator_role_name}")

    # Determinar el permiso requerido basado en el rol del colaborador
    if collaborator_role_name == "Administrador de finca":
        required_permission_name = "delete_administrator_farm"
    elif collaborator_role_name == "Operador de campo":
        required_permission_name = "delete_operator_farm"
    else:
        logger.error(f"Rol '{collaborator_role_name}' no reconocido para eliminación")
        return create_response(
            "error",
            f"Rol '{collaborator_role_name}' no reconocido para eliminación",
            status_code=400
        )

    # Verificar si el usuario tiene el permiso necesario
    permissions = get_role_permissions_for_user_role(user_role_farm.user_role_id)
    if required_permission_name not in permissions:
        logger.warning(f"Usuario no tiene permiso '{required_permission_name}'")
        return create_response(
            "error",
            f"No tienes permiso para eliminar a un colaborador con rol '{collaborator_role_name}'",
            status_code=403
        )

    logger.info(f"Usuario tiene permiso '{required_permission_name}'")

    # Eliminar la asociación del colaborador con la finca y en el microservicio de usuarios
    try:
        # Cambiar el estado a 'Inactivo' en UserRoleFarm
        urf_inactive_state = get_state(db, "Inactivo", "user_role_farm")
        if not urf_inactive_state:
            logger.error("Estado 'Inactivo' no encontrado para 'user_role_farm'")
            return create_response(
                "error",
                "Estado 'Inactivo' no encontrado para 'user_role_farm'",
                status_code=500
            )
        collaborator_role_farm.user_role_farm_state_id = urf_inactive_state.user_role_farm_state_id
        db.commit()
        # Eliminar la relación user_role en el microservicio de usuarios
        delete_user_role(collaborator_user_role_id)
        logger.info(f"Colaborador eliminado de la finca y del microservicio de usuarios exitosamente")
    except Exception as e:
        db.rollback()
        logger.error(f"Error al eliminar el colaborador: {str(e)}")
        return create_response(
            "error",
            "Error al eliminar el colaborador",
            status_code=500
        )

    # Devolver la respuesta exitosa
    return DeleteCollaboratorResponse(
        status="success",
        message=f"Colaborador '{collaborator_info['user_name']}' eliminado exitosamente de la finca '{farm.name}'"
    )
