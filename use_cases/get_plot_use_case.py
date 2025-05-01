from models.models import Farms, UserRoleFarm, Plots, CoffeeVarieties
from utils.response import create_response
from utils.state import get_state
import logging

logger = logging.getLogger(__name__)

def get_plot(plot_id: int, user, db):
    # Obtener los estados "Activo"
    active_plot_state = get_state(db, "Activo", "Plots")
    active_farm_state = get_state(db, "Activo", "Farms")
    active_urf_state = get_state(db, "Activo", "user_role_farm")

    # Obtener el lote
    plot = db.query(Plots).filter(
        Plots.plot_id == plot_id,
        Plots.plot_state_id == active_plot_state.plot_state_id
    ).first()
    if not plot:
        logger.warning("El lote con ID %s no existe o no está activo", plot_id)
        return create_response("error", "El lote no existe o no está activo")

    # Obtener la finca asociada al lote
    farm = db.query(Farms).filter(
        Farms.farm_id == plot.farm_id,
        Farms.farm_state_id == active_farm_state.farm_state_id
    ).first()
    if not farm:
        logger.warning("La finca asociada al lote no existe o no está activa")
        return create_response("error", "La finca asociada al lote no existe o no está activa")

    # Verificar si el usuario tiene un rol en la finca
    user_role_farm = db.query(UserRoleFarm).filter(
        UserRoleFarm.user_id == user.user_id,
        UserRoleFarm.farm_id == farm.farm_id,
        UserRoleFarm.user_role_farm_state_id == active_urf_state.user_role_farm_state_id
    ).first()
    if not user_role_farm:
        logger.warning("El usuario no está asociado con la finca con ID %s", farm.farm_id)
        return create_response("error", "No tienes permiso para ver este lote")

    # Verificar permiso 'read_plots'
    role_permission = db.query(RolePermission).join(Permissions).filter(
        RolePermission.role_id == user_role_farm.role_id,
        Permissions.name == "read_plots"
    ).first()
    if not role_permission:
        logger.warning("El rol del usuario no tiene permiso para ver los lotes en la finca")
        return create_response("error", "No tienes permiso para ver este lote")

    # Obtener la variedad de café
    coffee_variety = db.query(CoffeeVarieties).filter(
        CoffeeVarieties.coffee_variety_id == plot.coffee_variety_id
    ).first()

    # Devolver la información del lote
    plot_info = {
        "plot_id": plot.plot_id,
        "name": plot.name,
        "coffee_variety_name": coffee_variety.name if coffee_variety else None,
        "latitude": plot.latitude,
        "longitude": plot.longitude,
        "altitude": plot.altitude,
        "farm_id": plot.farm_id
    }

    return create_response("success", "Lote obtenido exitosamente", {"plot": plot_info})
