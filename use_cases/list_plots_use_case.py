from fastapi import HTTPException
from models.models import Farms, UserRoleFarm, Plots, CoffeeVarieties
from utils.response import create_response
from utils.state import get_state
import logging

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

    # Verificar si el usuario tiene un rol en la finca
    user_role_farm = db.query(UserRoleFarm).filter(
        UserRoleFarm.user_id == user.user_id,
        UserRoleFarm.farm_id == farm_id,
        UserRoleFarm.user_role_farm_state_id == active_urf_state.user_role_farm_state_id
    ).first()
    if not user_role_farm:
        logger.warning("El usuario no está asociado con la finca con ID %s", farm_id)
        return create_response("error", "No tienes permiso para ver los lotes de esta finca")

    # Verificar permiso 'read_plots'
    role_permission = db.query(RolePermission).join(Permissions).filter(
        RolePermission.role_id == user_role_farm.role_id,
        Permissions.name == "read_plots"
    ).first()
    if not role_permission:
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
