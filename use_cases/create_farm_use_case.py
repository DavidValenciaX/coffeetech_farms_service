# Lógica de negocio para la creación de una finca
from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.models import Farms, UserRoleFarm, AreaUnits, Roles
from utils.response import create_response
from utils.state import get_state
import logging

def create_farm_use_case(request, user, db: Session):
    logger = logging.getLogger(__name__)
    # Validación 1: El nombre de la finca no puede estar vacío ni contener solo espacios
    if not request.name or not request.name.strip():
        logger.warning("El nombre de la finca no puede estar vacío o solo contener espacios")
        return create_response("error", "El nombre de la finca no puede estar vacío")

    # Validación 2: El nombre no puede exceder los 50 caracteres
    if len(request.name) > 50:
        logger.warning("El nombre de la finca es demasiado largo")
        return create_response("error", "El nombre de la finca no puede tener más de 50 caracteres")

    # Validación 3: El área no puede ser negativa ni cero
    if request.area <= 0:
        logger.warning("El área de la finca debe ser mayor que cero")
        return create_response("error", "El área de la finca debe ser un número positivo mayor que cero")

    # Validación 4: Área no puede ser extremadamente grande (por ejemplo, no más de 10,000 hectáreas)
    if request.area > 10000:
        logger.warning("El área de la finca no puede exceder las 10,000 unidades de medida")
        return create_response("error", "El área de la finca no puede exceder las 10,000 unidades de medida")

    # Obtener el state "Activo" para el tipo "Farms"
    active_farm_state = get_state(db, "Activo", "Farms")
    if not active_farm_state:
        logger.error("No se encontró el estado 'Activo' para el tipo 'Farms'")
        return create_response("error", "No se encontró el estado 'Activo' para el tipo 'Farms'", status_code=400)

    # Comprobar si el usuario ya tiene una finca activa con el mismo nombre
    active_urf_state = get_state(db, "Activo", "user_role_farm")
    if not active_urf_state:
        logger.error("No se encontró el estado 'Activo' para el tipo 'user_role_farm'")
        return create_response("error", "No se encontró el estado 'Activo' para el tipo 'user_role_farm'", status_code=400)

    existing_farm = db.query(Farms).join(UserRoleFarm).filter(
        Farms.name == request.name,
        UserRoleFarm.user_id == user.user_id,
        Farms.farm_state_id == active_farm_state.farm_state_id,
        UserRoleFarm.user_role_farm_state_id == active_urf_state.user_role_farm_state_id
    ).first()

    if existing_farm:
        logger.warning("El usuario ya tiene una finca activa con el nombre '%s'", request.name)
        return create_response("error", f"Ya existe una finca activa con el nombre '{request.name}' para el propietario")

    # Buscar la unidad de medida (areaUnit)
    area_unit = db.query(AreaUnits).filter(AreaUnits.name == request.areaUnit).first()
    if not area_unit:
        logger.warning("Unidad de medida no válida: %s", request.areaUnit)
        return create_response("error", "Unidad de medida no válida")

    # Obtener el state "Activo" para el tipo "Farms" utilizando get_state
    farm_state_record = get_state(db, "Activo", "Farms")
    if not farm_state_record:
        logger.error("No se encontró el estado 'Activo' para el tipo 'Farms'")
        return create_response("error", "No se encontró el estado 'Activo' para el tipo 'Farms'", status_code=400)

    try:
        # Crear la nueva finca
        new_farm = Farms(
            name=request.name,
            area=request.area,
            area_unit_id=area_unit.area_unit_id,
            farm_state_id=farm_state_record.farm_state_id
        )
        db.add(new_farm)
        db.commit()
        db.refresh(new_farm)
        logger.info("Finca creada exitosamente con ID: %s", new_farm.farm_id)

        # Buscar el rol "Propietario"
        role = db.query(Roles).filter(Roles.name == "Propietario").first()
        if not role:
            logger.error("Rol 'Propietario' no encontrado")
            raise HTTPException(status_code=400, detail="Rol 'Propietario' no encontrado")

        # Get active state for UserRoleFarm
        active_urf_state = get_state(db, "Activo", "user_role_farm")
        if not active_urf_state:
            logger.error("No se encontró el estado 'Activo' para el tipo 'user_role_farm'")
            raise HTTPException(status_code=400, detail="No se encontró el estado 'Activo' para el tipo 'user_role_farm'")

        # Crear la relación UserRoleFarm
        user_role_farm = UserRoleFarm(
            user_id=user.user_id,
            farm_id=new_farm.farm_id,
            role_id=role.role_id,
            user_role_farm_state_id=active_urf_state.user_role_farm_state_id
        )
        db.add(user_role_farm)
        db.commit()
        logger.info("Usuario asignado como 'Propietario' de la finca con ID: %s", new_farm.farm_id)

        return create_response("success", "Finca creada y usuario asignado correctamente", {
            "farm_id": new_farm.farm_id,
            "name": new_farm.name,
            "area": new_farm.area,
            "area_unit": request.areaUnit
        })
    except Exception as e:
        db.rollback()
        logger.error("Error al crear la finca o asignar el usuario: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Error al crear la finca o asignar el usuario: {str(e)}")