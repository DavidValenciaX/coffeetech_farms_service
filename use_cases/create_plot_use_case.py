from fastapi import HTTPException
from utils.response import create_response
from utils.state import get_state
from sqlalchemy.orm import Session
from models.models import Farms, UserRoleFarm, Plots, CoffeeVarieties, AreaUnits, AreaUnits
import logging
from adapters.user_client import get_user_role_ids, get_role_permissions_for_user_role

logger = logging.getLogger(__name__)

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

def create_plot(request, user, db: Session):
    """
    Lógica de negocio para crear un nuevo lote (plot) en una finca.
    """

    # Obtener los estados "Activo" para Farms y UserRoleFarm
    active_farm_state = get_state(db, "Activo", "Farms")
    if not active_farm_state:
        logger.error("No se encontró el estado 'Activo' para el tipo 'Farms'")
        return create_response("error", "No se encontró el estado 'Activo' para el tipo 'Farms'", status_code=400)

    active_urf_state = get_state(db, "Activo", "user_role_farm")
    if not active_urf_state:
        logger.error("No se encontró el estado 'Activo' para el tipo 'user_role_farm'")
        return create_response("error", "No se encontró el estado 'Activo' para el tipo 'user_role_farm'", status_code=400)

    # Obtener el estado "Activo" para Plots
    active_plot_state = get_state(db, "Activo", "Plots")
    if not active_plot_state:
        logger.error("No se encontró el estado 'Activo' para el tipo 'Plots'")
        return create_response("error", "No se encontró el estado 'Activo' para el tipo 'Plots'", status_code=400)

    # Verificar que la finca existe y está activa
    farm = db.query(Farms).filter(Farms.farm_id == request.farm_id, Farms.farm_state_id == active_farm_state.farm_state_id).first()
    if not farm:
        logger.warning("La finca con ID %s no existe o no está activa", request.farm_id)
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
        UserRoleFarm.farm_id == request.farm_id,
        UserRoleFarm.user_role_farm_state_id == active_urf_state.user_role_farm_state_id
    ).first()
    
    if not user_role_farm:
        logger.warning("El usuario no está asociado con la finca con ID %s", request.farm_id)
        return create_response("error", "No tienes permiso para agregar un lote en esta finca")

    # Verificar permiso 'add_plot' usando el microservicio de usuarios
    try:
        permissions = get_role_permissions_for_user_role(user_role_farm.user_role_id)
    except Exception as e:
        logger.error("No se pudieron obtener los permisos del rol: %s", str(e))
        return create_response("error", "No se pudieron obtener los permisos del rol", status_code=500)

    if "add_plot" not in permissions:
        logger.warning("El rol del usuario no tiene permiso para agregar un lote en la finca")
        return create_response("error", "No tienes permiso para agregar un lote en esta finca")

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
        Plots.farm_id == request.farm_id,
        Plots.plot_state_id == active_plot_state.plot_state_id
    ).first()
    if existing_plot:
        logger.warning("Ya existe un lote con el nombre '%s' en la finca con ID %s", request.name, request.farm_id)
        return create_response("error", f"Ya existe un lote con el nombre '{request.name}' en esta finca")

    # Obtener la variedad de café
    coffee_variety = db.query(CoffeeVarieties).filter(CoffeeVarieties.coffee_variety_id == request.coffee_variety_id).first()
    if not coffee_variety:
        logger.warning("La variedad de café con ID '%s' no existe", request.coffee_variety_id)
        return create_response("error", f"La variedad de café con ID '{request.coffee_variety_id}' no existe")

    # Validar que el área del lote no sea mayor al área de la finca
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

    # Crear el lote
    try:
        new_plot = Plots(
            name=request.name,
            coffee_variety_id=request.coffee_variety_id,
            latitude=request.latitude,
            longitude=request.longitude,
            altitude=request.altitude,
            farm_id=request.farm_id,
            plot_state_id=active_plot_state.plot_state_id,
            area=request.area,
            area_unit_id=request.area_unit_id
        )
        db.add(new_plot)
        db.commit()
        db.refresh(new_plot)
        logger.info("Lote creado exitosamente con ID: %s", new_plot.plot_id)
        return create_response("success", "Lote creado correctamente", {
            "plot_id": new_plot.plot_id,
            "name": new_plot.name,
            "coffee_variety_id": coffee_variety.coffee_variety_id,
            "latitude": float(new_plot.latitude),
            "longitude": float(new_plot.longitude),
            "altitude": float(new_plot.altitude),
            "farm_id": new_plot.farm_id,
            "area": float(new_plot.area),
            "area_unit_id": new_plot.area_unit_id
        })
    except Exception as e:
        db.rollback()
        logger.error("Error al crear el lote: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Error al crear el lote: {str(e)}")