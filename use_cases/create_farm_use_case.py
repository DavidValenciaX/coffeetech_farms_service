# Lógica de negocio para la creación de una finca
from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.models import Farms, UserRoleFarm, AreaUnits
from utils.response import create_response
from utils.state import get_state
import logging
from adapters.user_client import get_user_role_ids, create_user_role
import os
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv(override=True, encoding="utf-8")

def create_farm(request, user, db: Session):
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

    # Obtener los user_role_ids desde el microservicio de usuarios
    try:
        user_role_ids = get_user_role_ids(user.user_id)
    except Exception as e:
        logger.error("No se pudieron obtener los user_role_ids: %s", str(e))
        return create_response("error", "No se pudieron obtener los roles del usuario", status_code=500)

    existing_farm = db.query(Farms).join(UserRoleFarm).filter(
        Farms.name == request.name,
        UserRoleFarm.user_role_id.in_(user_role_ids),
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

        # --- Crear UserRole en el servicio de usuarios ---
        try:
            user_role_data = create_user_role(user.user_id, "Propietario")
            user_role_id = user_role_data.get("user_role_id")
            if not user_role_id:
                logger.error("Respuesta inválida del servicio de usuarios al crear UserRole: %s", user_role_data)
                db.rollback()
                return create_response("error", "Respuesta inválida del servicio de usuarios al crear UserRole", status_code=500)
        except Exception as e:
            logger.error("Error al comunicarse con el servicio de usuarios: %s", str(e))
            db.rollback()
            return create_response("error", "Error al comunicarse con el servicio de usuarios", status_code=500)

        # Get active state for UserRoleFarm
        active_urf_state = get_state(db, "Activo", "user_role_farm")
        if not active_urf_state:
            logger.error("No se encontró el estado 'Activo' para el tipo 'user_role_farm'")
            db.rollback()
            return create_response("error", "No se encontró el estado 'Activo' para el tipo 'user_role_farm'", status_code=400)

        # Crear la relación UserRoleFarm usando el user_role_id recibido
        user_role_farm = UserRoleFarm(
            user_role_id=user_role_id,
            farm_id=new_farm.farm_id,
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