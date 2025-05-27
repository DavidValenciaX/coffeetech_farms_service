from fastapi import HTTPException
from utils.response import create_response
from utils.state import get_state
from sqlalchemy.orm import Session
from models.models import Farms, UserRoleFarm, Plots, CoffeeVarieties
import logging
from adapters.user_client import get_user_role_ids, get_role_permissions_for_user_role

logger = logging.getLogger(__name__)

def _get_required_states(db: Session):
    """Get all required states for plot creation."""
    active_farm_state = get_state(db, "Activo", "Farms")
    if not active_farm_state:
        return None, create_response("error", "No se encontró el estado 'Activo' para el tipo 'Farms'", status_code=400)

    active_urf_state = get_state(db, "Activo", "user_role_farm")
    if not active_urf_state:
        return None, create_response("error", "No se encontró el estado 'Activo' para el tipo 'user_role_farm'", status_code=400)

    active_plot_state = get_state(db, "Activo", "Plots")
    if not active_plot_state:
        return None, create_response("error", "No se encontró el estado 'Activo' para el tipo 'Plots'", status_code=400)

    inactive_plot_state = get_state(db, "Inactivo", "Plots")
    if not inactive_plot_state:
        return None, create_response("error", "No se encontró el estado 'Inactivo' para el tipo 'Plots'", status_code=400)

    return {
        'active_farm': active_farm_state,
        'active_urf': active_urf_state,
        'active_plot': active_plot_state,
        'inactive_plot': inactive_plot_state
    }, None

def _validate_farm_access(db: Session, request, user, states):
    """Validate farm exists and user has access."""
    farm = db.query(Farms).filter(
        Farms.farm_id == request.farm_id, 
        Farms.farm_state_id == states['active_farm'].farm_state_id
    ).first()
    if not farm:
        return None, create_response("error", "La finca no existe o no está activa")

    try:
        user_role_ids = get_user_role_ids(user.user_id)
    except Exception as e:
        logger.error("No se pudieron obtener los user_role_ids: %s", str(e))
        return None, create_response("error", "No se pudieron obtener los roles del usuario", status_code=500)

    user_role_farm = db.query(UserRoleFarm).filter(
        UserRoleFarm.user_role_id.in_(user_role_ids),
        UserRoleFarm.farm_id == request.farm_id,
        UserRoleFarm.user_role_farm_state_id == states['active_urf'].user_role_farm_state_id
    ).first()
    
    if not user_role_farm:
        return None, create_response("error", "No tienes permiso para agregar un lote en esta finca")

    try:
        permissions = get_role_permissions_for_user_role(user_role_farm.user_role_id)
    except Exception as e:
        logger.error("No se pudieron obtener los permisos del rol: %s", str(e))
        return None, create_response("error", "No se pudieron obtener los permisos del rol", status_code=500)

    if "add_plot" not in permissions:
        return None, create_response("error", "No tienes permiso para agregar un lote en esta finca")

    return user_role_farm, None

def _validate_plot_data(db: Session, request, states):
    """Validate plot name and check for duplicates."""
    if not request.name or not request.name.strip():
        return None, create_response("error", "El nombre del lote no puede estar vacío")
    if len(request.name) > 100:
        return None, create_response("error", "El nombre del lote no puede tener más de 100 caracteres")

    existing_active_plot = db.query(Plots).filter(
        Plots.name == request.name,
        Plots.farm_id == request.farm_id,
        Plots.plot_state_id == states['active_plot'].plot_state_id
    ).first()
    if existing_active_plot:
        return None, create_response("error", f"Ya existe un lote activo con el nombre '{request.name}' en esta finca")

    coffee_variety = db.query(CoffeeVarieties).filter(
        CoffeeVarieties.coffee_variety_id == request.coffee_variety_id
    ).first()
    if not coffee_variety:
        return None, create_response("error", f"La variedad de café con ID '{request.coffee_variety_id}' no existe")

    return coffee_variety, None

def _reactivate_inactive_plot(db: Session, request, states, coffee_variety):
    """Reactivate an existing inactive plot."""
    existing_inactive_plot = db.query(Plots).filter(
        Plots.name == request.name,
        Plots.farm_id == request.farm_id,
        Plots.plot_state_id == states['inactive_plot'].plot_state_id
    ).first()
    
    if not existing_inactive_plot:
        return None
    
    logger.info("Encontrado lote inactivo con el nombre '%s', reactivando y actualizando datos", request.name)
    existing_inactive_plot.plot_state_id = states['active_plot'].plot_state_id
    existing_inactive_plot.coffee_variety_id = request.coffee_variety_id
    existing_inactive_plot.latitude = request.latitude
    existing_inactive_plot.longitude = request.longitude
    existing_inactive_plot.altitude = request.altitude
    
    try:
        db.commit()
        db.refresh(existing_inactive_plot)
        logger.info("Lote reactivado y actualizado exitosamente con ID: %s", existing_inactive_plot.plot_id)
        return create_response("success", "Lote reactivado y actualizado correctamente", {
            "plot_id": existing_inactive_plot.plot_id,
            "name": existing_inactive_plot.name,
            "coffee_variety_id": coffee_variety.coffee_variety_id,
            "latitude": float(existing_inactive_plot.latitude) if existing_inactive_plot.latitude else None,
            "longitude": float(existing_inactive_plot.longitude) if existing_inactive_plot.longitude else None,
            "altitude": float(existing_inactive_plot.altitude) if existing_inactive_plot.altitude else None,
            "farm_id": existing_inactive_plot.farm_id,
            "reactivated": True
        })
    except Exception as e:
        db.rollback()
        logger.error("Error al reactivar el lote: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Error al reactivar el lote: {str(e)}")

def _create_new_plot(db: Session, request, states, coffee_variety):
    """Create a new plot."""
    try:
        new_plot = Plots(
            name=request.name,
            coffee_variety_id=request.coffee_variety_id,
            latitude=request.latitude,
            longitude=request.longitude,
            altitude=request.altitude,
            farm_id=request.farm_id,
            plot_state_id=states['active_plot'].plot_state_id
        )
        db.add(new_plot)
        db.commit()
        db.refresh(new_plot)
        logger.info("Lote creado exitosamente con ID: %s", new_plot.plot_id)
        return create_response("success", "Lote creado correctamente", {
            "plot_id": new_plot.plot_id,
            "name": new_plot.name,
            "coffee_variety_id": coffee_variety.coffee_variety_id,
            "latitude": float(new_plot.latitude) if new_plot.latitude else None,
            "longitude": float(new_plot.longitude) if new_plot.longitude else None,
            "altitude": float(new_plot.altitude) if new_plot.altitude else None,
            "farm_id": new_plot.farm_id
        })
    except Exception as e:
        db.rollback()
        logger.error("Error al crear el lote: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Error al crear el lote: {str(e)}")

def create_plot(request, user, db: Session):
    """
    Lógica de negocio para crear un nuevo lote (plot) en una finca.
    """
    # Get required states
    states, error_response = _get_required_states(db)
    if error_response:
        return error_response

    # Validate farm access and permissions
    _, error_response = _validate_farm_access(db, request, user, states)
    if error_response:
        return error_response

    # Validate plot data
    coffee_variety, error_response = _validate_plot_data(db, request, states)
    if error_response:
        return error_response

    # Try to reactivate inactive plot
    reactivation_response = _reactivate_inactive_plot(db, request, states, coffee_variety)
    if reactivation_response:
        return reactivation_response

    # Create new plot
    return _create_new_plot(db, request, states, coffee_variety)