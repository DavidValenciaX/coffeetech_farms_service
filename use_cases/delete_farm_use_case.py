from fastapi import HTTPException
from sqlalchemy.orm import Session
from models.models import Farms, UserRoleFarm
from utils.response import create_response
from utils.state import get_state
import logging
from adapters.user_client import get_user_role_ids, get_role_permissions_for_user_role

logger = logging.getLogger(__name__)

def delete_farm(farm_id: int, user, db: Session):

    # Obtener el state "Activo" para la finca y user_role_farm
    active_farm_state = get_state(db, "Activo", "Farms")
    if not active_farm_state:
        logger.error("No se encontró el estado 'Activo' para el tipo 'Farms'")
        return create_response("error", "Estado 'Activo' no encontrado para Farms", status_code=400)

    active_urf_state = get_state(db, "Activo", "user_role_farm")
    if not active_urf_state:
        logger.error("No se encontró el estado 'Activo' para el tipo 'user_role_farm'")
        return create_response("error", "Estado 'Activo' no encontrado para user_role_farm", status_code=400)

    # Obtener los user_role_ids del usuario desde el microservicio de usuarios
    try:
        user_role_ids = get_user_role_ids(user.user_id)
    except Exception as e:
        logger.error("No se pudieron obtener los user_role_ids: %s", str(e))
        return create_response("error", "No se pudieron obtener los roles del usuario", status_code=500)

    # Verificar si el usuario está asociado con la finca activa
    user_role_farm = db.query(UserRoleFarm).join(Farms).filter(
        UserRoleFarm.farm_id == farm_id,
        UserRoleFarm.user_role_id.in_(user_role_ids),
        UserRoleFarm.user_role_farm_state_id == active_urf_state.user_role_farm_state_id,
        Farms.farm_state_id == active_farm_state.farm_state_id
    ).first()

    if not user_role_farm:
        logger.warning("El usuario no está asociado con la finca que intenta eliminar")
        return create_response("error", "No tienes permiso para eliminar esta finca")

    # Verificar permisos para eliminar la finca usando el microservicio de usuarios
    try:
        permissions = get_role_permissions_for_user_role(user_role_farm.user_role_id)
    except Exception as e:
        logger.error("No se pudieron obtener los permisos del rol: %s", str(e))
        return create_response("error", "No se pudieron obtener los permisos del rol", status_code=500)

    if "delete_farm" not in permissions:
        logger.warning("El rol del usuario no tiene permiso para eliminar la finca")
        return create_response("error", "No tienes permiso para eliminar esta finca")

    try:
        farm = db.query(Farms).filter(Farms.farm_id == farm_id).first()

        if not farm:
            logger.warning("Finca no encontrada")
            return create_response("error", "Finca no encontrada")

        # Cambiar el estado de la finca a "Inactivo"
        inactive_farm_state = get_state(db, "Inactivo", "Farms")

        if not inactive_farm_state:
            logger.error("No se encontró el estado 'Inactivo' para el tipo 'Farms'")
            raise HTTPException(status_code=400, detail="No se encontró el estado 'Inactivo' para el tipo 'Farms'.")

        farm.farm_state_id = inactive_farm_state.farm_state_id

        # Cambiar el estado de todas las relaciones en user_role_farm a "Inactivo"
        inactive_urf_state = get_state(db, "Inactivo", "user_role_farm")

        if not inactive_urf_state:
            logger.error("No se encontró el estado 'Inactivo' para el tipo 'user_role_farm'")
            raise HTTPException(status_code=400, detail="No se encontró el estado 'Inactivo' para el tipo 'user_role_farm'.")

        user_role_farms = db.query(UserRoleFarm).filter(UserRoleFarm.farm_id == farm_id).all()
        for urf in user_role_farms:
            urf.user_role_farm_state_id = inactive_urf_state.user_role_farm_state_id

        db.commit()
        logger.info("Finca y relaciones en user_role_farm puestas en estado 'Inactivo' para la finca con ID %s", farm_id)
        return create_response("success", "Finca puesta en estado 'Inactivo' correctamente")

    except Exception as e:
        db.rollback()
        logger.error("Error al desactivar la finca: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Error al desactivar la finca: {str(e)}")