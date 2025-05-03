from fastapi import HTTPException
from models.models import Farms, UserRoleFarm, AreaUnits
from utils.response import create_response
from utils.state import get_state
import logging
from adapters.user_client import get_user_role_ids, get_role_name_for_user_role, get_role_permissions_for_user_role

logger = logging.getLogger(__name__)

def update_farm(request, user, db):
    # Obtener el state "Activo" para la finca y la relación user_role_farm
    active_farm_state = get_state(db, "Activo", "Farms")
    active_urf_state = get_state(db, "Activo", "user_role_farm")

    # Obtener los user_role_ids del usuario desde el microservicio de usuarios
    try:
        user_role_ids = get_user_role_ids(user.user_id)
    except Exception as e:
        logger.error("No se pudieron obtener los user_role_ids: %s", str(e))
        return create_response("error", "No se pudieron obtener los roles del usuario", status_code=500)

    # Verificar si el usuario está asociado con la finca y si tanto la finca como la relación están activas
    user_role_farm = db.query(UserRoleFarm).join(Farms).filter(
        UserRoleFarm.farm_id == request.farm_id,
        UserRoleFarm.user_role_id.in_(user_role_ids),
        UserRoleFarm.user_role_farm_state_id == active_urf_state.user_role_farm_state_id,
        Farms.farm_state_id == active_farm_state.farm_state_id
    ).first()

    if not user_role_farm:
        logger.warning("El usuario no está asociado con la finca activa que intenta editar")
        return create_response("error", "No tienes permiso para editar esta finca porque no estás asociado con una finca activa")

    # Verificar permisos para el rol del usuario usando el microservicio de usuarios
    try:
        permissions = get_role_permissions_for_user_role(user_role_farm.user_role_id)
    except Exception as e:
        logger.error("No se pudieron obtener los permisos del rol: %s", str(e))
        return create_response("error", "No se pudieron obtener los permisos del rol", status_code=500)

    if "edit_farm" not in permissions:
        logger.warning("El rol del usuario no tiene permiso para editar la finca")
        return create_response("error", "No tienes permiso para editar esta finca")

    # Validaciones del nombre y área
    if not request.name or not request.name.strip():
        logger.warning("El nombre de la finca no puede estar vacío o solo contener espacios")
        return create_response("error", "El nombre de la finca no puede estar vacío")
    
    if len(request.name) > 50:
        logger.warning("El nombre de la finca es demasiado largo")
        return create_response("error", "El nombre de la finca no puede tener más de 50 caracteres")
    
    if request.area <= 0:
        logger.warning("El área de la finca debe ser mayor que cero")
        return create_response("error", "El área de la finca debe ser un número positivo mayor que cero")

    # Buscar la unidad de medida (areaUnit)
    area_unit = db.query(AreaUnits).filter(AreaUnits.area_unit_id == request.area_unit_id).first()
    if not area_unit:
        logger.warning("Unidad de medida no válida: %s", request.area_unit_id)
        return create_response("error", "Unidad de medida no válida")

    try:
        # Buscar la finca que se está intentando actualizar
        farm = db.query(Farms).filter(Farms.farm_id == request.farm_id).first()
        if not farm:
            logger.warning("Finca no encontrada")
            return create_response("error", "Finca no encontrada")

        # Verificar si el nuevo nombre ya está en uso por otra finca en la que el usuario es propietario
        if farm.name != request.name:  # Solo validar el nombre si se está intentando cambiar
            existing_farm = db.query(Farms).join(UserRoleFarm).filter(
                Farms.name == request.name,
                Farms.farm_id != request.farm_id,
                UserRoleFarm.user_role_id.in_(user_role_ids),
                Farms.farm_state_id == active_farm_state.farm_state_id,
                UserRoleFarm.user_role_farm_state_id == active_urf_state.user_role_farm_state_id
            ).first()

            if existing_farm:
                logger.warning("El nombre de la finca ya está en uso por otra finca del usuario")
                return create_response("error", "El nombre de la finca ya está en uso por otra finca del propietario")

        # Actualizar la finca
        farm.name = request.name
        farm.area = request.area
        farm.area_unit_id = area_unit.area_unit_id

        db.commit()
        db.refresh(farm)
        logger.info("Finca actualizada exitosamente con ID: %s", farm.farm_id)

        return create_response("success", "Finca actualizada correctamente", {
            "farm_id": farm.farm_id,
            "name": farm.name,
            "area": farm.area,
            "area_unit": request.area_unit_id
        })
    except Exception as e:
        db.rollback()
        logger.error("Error al actualizar la finca: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Error al actualizar la finca: {str(e)}")