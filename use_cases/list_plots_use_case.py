from fastapi import HTTPException
from models.models import Farms, UserRoleFarm, Plots, CoffeeVarieties, AreaUnits
from utils.response import create_response
from utils.state import get_state
import logging
from adapters.user_client import get_user_role_ids, get_role_permissions_for_user_role

logger = logging.getLogger(__name__)

def list_plots(farm_id: int, user, db):
    """
    Lógica de negocio para obtener la lista de lotes activos de una finca específica.
    """
    # Obtener los estados "Activo"
    active_farm_state = get_state(db, "Activo", "Farms")
    active_urf_state = get_state(db, "Activo", "user_role_farm")
    active_plot_state = get_state(db, "Activo", "Plots")

    # Verificar que la finca existe y está activa
    farm = db.query(Farms).filter(Farms.farm_id == farm_id, Farms.farm_state_id == active_farm_state.farm_state_id).first()
    if not farm:
        logger.warning("La finca con ID %s no existe o no está activa", farm_id)
        return create_response("error", "La finca no existe o no está activa")

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
        UserRoleFarm.user_role_farm_state_id == active_urf_state.user_role_farm_state_id
    ).first()
    if not user_role_farm:
        logger.warning("El usuario no está asociado con la finca con ID %s", farm_id)
        return create_response("error", "No tienes permiso para ver los lotes de esta finca")

    # Verificar permiso 'read_plots' usando el microservicio de usuarios
    try:
        permissions = get_role_permissions_for_user_role(user_role_farm.user_role_id)
    except Exception as e:
        logger.error("No se pudieron obtener los permisos del rol: %s", str(e))
        return create_response("error", "No se pudieron obtener los permisos del rol", status_code=500)

    if "read_plots" not in permissions:
        logger.warning("El rol del usuario no tiene permiso para ver los lotes en la finca")
        return create_response("error", "No tienes permiso para ver los lotes de esta finca")

    # Obtener todos los lotes activos de la finca
    try:
        plots = db.query(Plots).filter(
            Plots.farm_id == farm_id,
            Plots.plot_state_id == active_plot_state.plot_state_id
        ).all()

        plot_list = []
        for plot in plots:
            coffee_variety = db.query(CoffeeVarieties).filter(
                CoffeeVarieties.coffee_variety_id == plot.coffee_variety_id
            ).first()
            
            plot_list.append({
                "plot_id": plot.plot_id,
                "name": plot.name,
                "coffee_variety_name": coffee_variety.name if coffee_variety else None,
                "latitude": plot.latitude,
                "longitude": plot.longitude,
                "altitude": plot.altitude
            })

        return create_response("success", "Lista de lotes obtenida exitosamente", {"plots": plot_list})

    except Exception as e:
        logger.error("Error al obtener la lista de lotes: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Error al obtener la lista de lotes: {str(e)}")
