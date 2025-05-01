from fastapi import HTTPException
from models.models import Farms, UserRoleFarm, Plots
from utils.response import create_response
from utils.state import get_state
import logging

logger = logging.getLogger(__name__)

def delete_plot(plot_id: int, user, db):
    # Obtener los estados "Activo" e "Inactivo" para Plots
    active_plot_state = get_state(db, "Activo", "Plots")
    inactive_plot_state = get_state(db, "Inactivo", "Plots")

    # Obtener el lote
    plot = db.query(Plots).filter(Plots.plot_id == plot_id, Plots.plot_state_id == active_plot_state.plot_state_id).first()
    if not plot:
        logger.warning("El lote con ID %s no existe o no está activo", plot_id)
        return create_response("error", "El lote no existe o no está activo")

    # Obtener la finca asociada al lote
    farm = db.query(Farms).filter(Farms.farm_id == plot.farm_id).first()
    if not farm:
        logger.warning("La finca asociada al lote no existe")
        return create_response("error", "La finca asociada al lote no existe")

    # Obtener el estado "Activo" para UserRoleFarm
    active_urf_state = get_state(db, "Activo", "user_role_farm")

    # Verificar si el usuario tiene un rol en la finca
    user_role_farm = db.query(UserRoleFarm).filter(
        UserRoleFarm.user_id == user.user_id,
        UserRoleFarm.farm_id == farm.farm_id,
        UserRoleFarm.user_role_farm_state_id == active_urf_state.user_role_farm_state_id
    ).first()
    if not user_role_farm:
        logger.warning("El usuario no está asociado con la finca con ID %s", farm.farm_id)
        return create_response("error", "No tienes permiso para eliminar este lote")

    # Verificar permiso 'delete_plot'
    role_permission = db.query(RolePermission).join(Permissions).filter(
        RolePermission.role_id == user_role_farm.role_id,
        Permissions.name == "delete_plot"
    ).first()
    if not role_permission:
        logger.warning("El rol del usuario no tiene permiso para eliminar el lote en la finca")
        return create_response("error", "No tienes permiso para eliminar este lote")

    # Cambiar el estado del lote a 'Inactivo'
    try:
        plot.plot_state_id = inactive_plot_state.plot_state_id
        db.commit()
        logger.info("Lote con ID %s puesto en estado 'Inactivo'", plot.plot_id)
        return create_response("success", "Lote eliminado correctamente")
    except Exception as e:
        db.rollback()
        logger.error("Error al eliminar el lote: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Error al eliminar el lote: {str(e)}")
