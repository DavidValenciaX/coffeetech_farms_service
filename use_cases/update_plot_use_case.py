from fastapi import HTTPException
from utils.response import create_response
from utils.state import get_state
from models.models import Plots, Farms, UserRoleFarm, CoffeeVarieties, AreaUnits # Added AreaUnits
import logging
from adapters.user_client import get_user_role_ids, get_role_permissions_for_user_role
from sqlalchemy.orm import Session # Added Session for type hinting

logger = logging.getLogger(__name__)

# --- Copied validation functions from create_plot_use_case.py ---
def convert_area_to_m2(area: float, area_unit_name: str):
    """
    Convierte un área a metros cuadrados según la unidad.
    """
    conversions = {
        "Metro cuadrado": 1,
        "Hectárea": 10000,
        "Kilómetro cuadrado": 1000000,
    }
    factor = conversions.get(area_unit_name)
    if factor is None:
        raise ValueError(f"Unidad de área no soportada para conversión: {area_unit_name}")
    return float(area) * factor

def validate_plot_area_not_greater_than_farm(db: Session, plot_area, plot_area_unit_id, farm_area, farm_area_unit_id):
    """
    Valida que el área del lote no sea mayor al área de la finca, convirtiendo ambas a metros cuadrados.
    """
    # Obtener nombres de las unidades
    plot_unit = db.query(AreaUnits).filter(AreaUnits.area_unit_id == plot_area_unit_id).first()
    farm_unit = db.query(AreaUnits).filter(AreaUnits.area_unit_id == farm_area_unit_id).first()
    if not plot_unit or not farm_unit:
        raise ValueError("No se pudo obtener la unidad de área para la validación.")

    # Convertir ambas áreas a metros cuadrados
    plot_area_m2 = convert_area_to_m2(plot_area, plot_unit.name)
    farm_area_m2 = convert_area_to_m2(farm_area, farm_unit.name)

    if plot_area_m2 > farm_area_m2:
        logger.error("El área del lote (%.2f m2) es mayor que el área de la finca (%.2f m2)", plot_area_m2, farm_area_m2)
        return False, f"El área del lote ({plot_area_m2:.2f} m2) no puede ser mayor que el área de la finca ({farm_area_m2:.2f} m2)"
    return True, None
# --- End of copied functions ---


def update_plot_general_info(request, user, db: Session): # Added Session type hint
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

    # --- Added Area Validation ---
    # Validar que el área del lote no sea mayor al área de la finca
    try:
        # Ensure area and area_unit_id are present in the request
        if not hasattr(request, 'area') or not hasattr(request, 'area_unit_id'):
             logger.error("La solicitud de actualización no incluye 'area' o 'area_unit_id'.")
             # Decide how to handle this: error out, or skip validation/update?
             # Option 1: Error out if area fields are expected
             return create_response("error", "La solicitud debe incluir 'area' y 'area_unit_id' para la actualización.", status_code=400)
             # Option 2: Skip validation and area update if they are optional (remove the return above)
             # pass # Or log a warning and continue without area update/validation

        is_valid_area, area_msg = validate_plot_area_not_greater_than_farm(
            db,
            request.area,
            request.area_unit_id,
            farm.area,
            farm.area_unit_id
        )
        if not is_valid_area:
            logger.error(area_msg)
            return create_response("error", area_msg, status_code=400)
    except ValueError as e:
        logger.error("Error de validación de área: %s", str(e))
        return create_response("error", str(e), status_code=400)
    except AttributeError:
        # This handles the case where request might not have area/area_unit_id if Option 2 above is chosen
        logger.warning("No se validó ni actualizó el área porque no se proporcionó en la solicitud.")
        pass # Continue without area update/validation if fields are optional
    # --- End of Area Validation ---


    # Actualizar el lote
    try:
        plot.name = request.name
        plot.coffee_variety_id = coffee_variety.coffee_variety_id
        # Update area fields if they exist in the request
        if hasattr(request, 'area') and hasattr(request, 'area_unit_id'):
            plot.area = request.area
            plot.area_unit_id = request.area_unit_id

        db.commit()
        db.refresh(plot)
        logger.info("Lote actualizado exitosamente con ID: %s", plot.plot_id)

        response_data = {
            "plot_id": plot.plot_id,
            "name": plot.name,
            "coffee_variety_name": coffee_variety.name,
        }
        # Include area in response if updated
        if hasattr(request, 'area') and hasattr(request, 'area_unit_id'):
             response_data["area"] = float(plot.area)
             response_data["area_unit_id"] = plot.area_unit_id

        return create_response("success", "Información general del lote actualizada correctamente", response_data)
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
