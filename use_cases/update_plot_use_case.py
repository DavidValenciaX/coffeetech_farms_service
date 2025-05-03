from fastapi import HTTPException
from utils.response import create_response
from utils.state import get_state
from models.models import Plots, Farms, UserRoleFarm, CoffeeVarieties
import logging
from adapters.user_client import get_user_role_ids, get_role_permissions_for_user_role

logger = logging.getLogger(__name__)

def update_plot_general_info(request, user, db):
    # Obtener el estado "Activo" para Plots
    active_plot_state = get_state(db, "Activo", "Plots")
    if not active_plot_state:
        logger.error("No se encontró el estado 'Activo' para el tipo 'Plots'")
        return create_response("error", "No se encontró el estado 'Activo' para el tipo 'Plots'", status_code=400)

    # Obtener el lote
    plot = db.query(Plots).filter(Plots.plot_id == request.plot_id, Plots.plot_state_id == active_plot_state.plot_state_id).first()
    if not plot:
        logger.warning("El lote con ID %s no existe o no está activo", request.plot_id)
        return create_response("error", "El lote no existe o no está activo")

    # Obtener la finca asociada al lote
    farm = db.query(Farms).filter(Farms.farm_id == plot.farm_id).first()
    if not farm:
        logger.warning("La finca asociada al lote no existe")
        return create_response("error", "La finca asociada al lote no existe")

    # Obtener el estado "Activo" para UserRoleFarm
    active_urf_state = get_state(db, "Activo", "user_role_farm")
    if not active_urf_state:
        logger.error("No se encontró el estado 'Activo' para el tipo 'user_role_farm'")
        return create_response("error", "No se encontró el estado 'Activo' para el tipo 'user_role_farm'", status_code=400)

    # Obtener los user_role_ids del usuario desde el microservicio de usuarios
    try:
        user_role_ids = get_user_role_ids(user.user_id)
    except Exception as e:
        logger.error("No se pudieron obtener los user_role_ids: %s", str(e))
        return create_response("error", "No se pudieron obtener los roles del usuario", status_code=500)

    # Verificar si el usuario tiene un rol en la finca
    user_role_farm = db.query(UserRoleFarm).filter(
        UserRoleFarm.user_role_id.in_(user_role_ids),
        UserRoleFarm.farm_id == farm.farm_id,
        UserRoleFarm.user_role_farm_state_id == active_urf_state.user_role_farm_state_id
    ).first()
    if not user_role_farm:
        logger.warning("El usuario no está asociado con la finca con ID %s", farm.farm_id)
        return create_response("error", "No tienes permiso para editar un lote en esta finca")

    # Verificar permiso 'edit_plot' usando el microservicio de usuarios
    try:
        permissions = get_role_permissions_for_user_role(user_role_farm.user_role_id)
    except Exception as e:
        logger.error("No se pudieron obtener los permisos del rol: %s", str(e))
        return create_response("error", "No se pudieron obtener los permisos del rol", status_code=500)

    if "edit_plot" not in permissions:
        logger.warning("El rol del usuario no tiene permiso para editar el lote en la finca")
        return create_response("error", "No tienes permiso para editar un lote en esta finca")

    # Validar el nombre del lote
    if not request.name or not request.name.strip():
        logger.warning("El nombre del lote no puede estar vacío o solo contener espacios")
        return create_response("error", "El nombre del lote no puede estar vacío")
    if len(request.name) > 100:
        logger.warning("El nombre del lote es demasiado largo")
        return create_response("error", "El nombre del lote no puede tener más de 100 caracteres")

    # Verificar si ya existe un lote con el mismo nombre en la finca
    existing_plot = db.query(Plots).filter(
        Plots.name == request.name,
        Plots.farm_id == farm.farm_id,
        Plots.plot_id != request.plot_id,
        Plots.plot_state_id == active_plot_state.plot_state_id
    ).first()
    if existing_plot:
        logger.warning("Ya existe un lote con el nombre '%s' en la finca con ID %s", request.name, farm.farm_id)
        return create_response("error", f"Ya existe un lote con el nombre '{request.name}' en esta finca")

    # Obtener la variedad de café
    coffee_variety = db.query(CoffeeVarieties).filter(CoffeeVarieties.coffee_variety_id == request.coffee_variety_id).first()

    if not coffee_variety:
        logger.warning(f"La variedad de café con ID {request.coffee_variety_id} no existe")
        return create_response("error", f"La variedad de café con ID {request.coffee_variety_id} no existe", status_code=400)

    # Actualizar el lote
    try:
        plot.name = request.name
        plot.coffee_variety_id = coffee_variety.coffee_variety_id
        db.commit()
        db.refresh(plot)
        logger.info("Lote actualizado exitosamente con ID: %s", plot.plot_id)
        return create_response("success", "Información general del lote actualizada correctamente", {
            "plot_id": plot.plot_id,
            "name": plot.name,
            "coffee_variety_name": coffee_variety.name
        })
    except Exception as e:
        db.rollback()
        logger.error("Error al actualizar el lote: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Error al actualizar el lote: {str(e)}")

def update_plot_location(request, user, db):
    # Obtener el estado "Activo" para Plots
    active_plot_state = get_state(db, "Activo", "Plots")
    if not active_plot_state:
        logger.error("No se encontró el estado 'Activo' para el tipo 'Plots'")
        return create_response("error", "No se encontró el estado 'Activo' para el tipo 'Plots'", status_code=400)

    # Obtener el lote
    plot = db.query(Plots).filter(Plots.plot_id == request.plot_id, Plots.plot_state_id == active_plot_state.plot_state_id).first()
    if not plot:
        logger.warning("El lote con ID %s no existe o no está activo", request.plot_id)
        return create_response("error", "El lote no existe o no está activo")

    # Obtener la finca asociada al lote
    farm = db.query(Farms).filter(Farms.farm_id == plot.farm_id).first()
    if not farm:
        logger.warning("La finca asociada al lote no existe")
        return create_response("error", "La finca asociada al lote no existe")

    # Obtener el estado "Activo" para UserRoleFarm
    active_urf_state = get_state(db, "Activo", "user_role_farm")
    if not active_urf_state:
        logger.error("No se encontró el estado 'Activo' para el tipo 'user_role_farm'")
        return create_response("error", "No se encontró el estado 'Activo' para el tipo 'user_role_farm'", status_code=400)

    # Obtener los user_role_ids del usuario desde el microservicio de usuarios
    try:
        user_role_ids = get_user_role_ids(user.user_id)
    except Exception as e:
        logger.error("No se pudieron obtener los user_role_ids: %s", str(e))
        return create_response("error", "No se pudieron obtener los roles del usuario", status_code=500)

    # Verificar si el usuario tiene un rol en la finca
    user_role_farm = db.query(UserRoleFarm).filter(
        UserRoleFarm.user_role_id.in_(user_role_ids),
        UserRoleFarm.farm_id == farm.farm_id,
        UserRoleFarm.user_role_farm_state_id == active_urf_state.user_role_farm_state_id
    ).first()
    if not user_role_farm:
        logger.warning("El usuario no está asociado con la finca con ID %s", farm.farm_id)
        return create_response("error", "No tienes permiso para editar un lote en esta finca")

    # Verificar permiso 'edit_plot' usando el microservicio de usuarios
    try:
        permissions = get_role_permissions_for_user_role(user_role_farm.user_role_id)
    except Exception as e:
        logger.error("No se pudieron obtener los permisos del rol: %s", str(e))
        return create_response("error", "No se pudieron obtener los permisos del rol", status_code=500)

    if "edit_plot" not in permissions:
        logger.warning("El rol del usuario no tiene permiso para editar el lote en la finca")
        return create_response("error", "No tienes permiso para editar un lote en esta finca")

    # Actualizar la ubicación del lote
    try:
        plot.latitude = request.latitude
        plot.longitude = request.longitude
        plot.altitude = request.altitude
        db.commit()
        db.refresh(plot)
        logger.info("Ubicación del lote actualizada exitosamente con ID: %s", plot.plot_id)
        return create_response("success", "Ubicación del lote actualizada correctamente", {
            "plot_id": plot.plot_id,
            "latitude": plot.latitude,
            "longitude": plot.longitude,
            "altitude": plot.altitude
        })
    except Exception as e:
        db.rollback()
        logger.error("Error al actualizar la ubicación del lote: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Error al actualizar la ubicación del lote: {str(e)}")
