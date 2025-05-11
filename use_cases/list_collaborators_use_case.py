from typing import Dict, Any
from sqlalchemy.orm import Session
from models.models import Farms, UserRoleFarm
from utils.response import create_response
from utils.state import get_state
import logging
from adapters.user_client import (
    get_user_role_ids,
    get_role_permissions_for_user_role,
    get_collaborators_info
)

logger = logging.getLogger(__name__)

def list_collaborators(farm_id: int, user, db: Session) -> Dict[str, Any]:
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

    # Obtener los user_role_ids del usuario desde el microservicio de usuarios
    try:
        user_role_ids = get_user_role_ids(user.user_id)
    except Exception as e:
        logger.error("No se pudieron obtener los user_role_ids: %s", str(e))
        return create_response("error", "No se pudieron obtener los roles del usuario", status_code=500)

    # Verificar si el usuario tiene un rol en la finca
    user_role_farm = db.query(UserRoleFarm).filter(
        UserRoleFarm.user_role_id.in_(user_role_ids),
        UserRoleFarm.farm_id == farm_id,
        UserRoleFarm.user_role_farm_state_id == urf_active_state.user_role_farm_state_id
    ).first()
    if not user_role_farm:
        logger.warning(f"El usuario no está asociado con la finca con ID {farm_id}")
        return create_response(
            "error",
            "No tienes permiso para ver los colaboradores de esta finca",
            status_code=403
        )

    # Verificar permiso 'read_collaborators' usando el microservicio de usuarios
    try:
        permissions = get_role_permissions_for_user_role(user_role_farm.user_role_id)
    except Exception as e:
        logger.error("No se pudieron obtener los permisos del rol: %s", str(e))
        return create_response("error", "No se pudieron obtener los permisos del rol", status_code=500)

    if "read_collaborators" not in permissions:
        logger.warning("El rol del usuario no tiene permiso para ver los colaboradores en la finca")
        return create_response(
            "error",
            "No tienes permiso para ver los colaboradores de esta finca",
            status_code=403
        )

    # Obtener todos los user_role_farm activos de la finca
    user_role_farms = db.query(UserRoleFarm).filter(
        UserRoleFarm.farm_id == farm_id,
        UserRoleFarm.user_role_farm_state_id == urf_active_state.user_role_farm_state_id
    ).all()
    user_role_ids_farm = [urf.user_role_id for urf in user_role_farms]

    # Consultar la información de los colaboradores al microservicio de usuarios usando la función dedicada
    try:
        collaborators_list = get_collaborators_info(user_role_ids_farm)
    except Exception as e:
        logger.error("No se pudo obtener la información de los colaboradores desde el microservicio de usuarios: %s", str(e))
        return create_response(
            "error",
            "No se pudo obtener la información de los colaboradores",
            status_code=500
        )

    return create_response(
        "success",
        "Colaboradores obtenidos exitosamente",
        data=collaborators_list,
        status_code=200
    )
