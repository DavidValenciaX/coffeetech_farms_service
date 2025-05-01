from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from models.models import Farms, UserRoleFarm
from utils.response import create_response
from utils.state import get_state
import logging

logger = logging.getLogger(__name__)

def list_collaborators(farm_id: int, user, db: Session) -> Dict[str, Any]:

    # 2. Verificar que la finca exista
    farm = db.query(Farms).filter(Farms.farm_id == farm_id).first()
    if not farm:
        logger.error(f"Finca con ID {farm_id} no encontrada")
        return create_response(
            "error",
            "Finca no encontrada",
            status_code=404
        )

    logger.info(f"Finca encontrada: {farm.name} (ID: {farm.farm_id})")

    # 3. Obtener el estado 'Activo' para 'user_role_farm'
    urf_active_state = get_state(db, "Activo", "user_role_farm")

    if not urf_active_state:
        logger.error("Estado 'Activo' no encontrado para 'user_role_farm'")
        return create_response(
            "error",
            "Estado 'Activo' no encontrado para 'user_role_farm'",
            status_code=400
        )

    logger.info(f"Estado 'Activo' encontrado: {urf_active_state.name} (ID: {urf_active_state.user_role_farm_state_id})")

    # 4. Obtener el permiso 'read_collaborators' con insensibilidad a mayúsculas
    read_permission = db.query(Permissions).filter(
        func.lower(Permissions.name) == "read_collaborators"
    ).first()

    logger.info(f"Permiso 'read_collaborators' obtenido: {read_permission}")

    if not read_permission:
        logger.error("Permiso 'read_collaborators' no encontrado en la base de datos")
        return create_response(
            "error",
            "Permiso 'read_collaborators' no encontrado en la base de datos",
            status_code=500
        )

    # Verificar si el usuario tiene el permiso 'read_collaborators' en la finca especificada
    has_permission = db.query(UserRoleFarm).join(RolePermission, UserRoleFarm.role_id == RolePermission.role_id).filter(
        UserRoleFarm.user_id == user.user_id,
        UserRoleFarm.farm_id == farm_id,
        UserRoleFarm.user_role_farm_state_id == urf_active_state.user_role_farm_state_id,
        RolePermission.permission_id == read_permission.permission_id
    ).first()

    if not has_permission:
        logger.warning(f"Usuario {user.name} no tiene permiso 'read_collaborators' en la finca ID {farm_id}")
        return create_response(
            "error",
            "No tienes permiso para leer los colaboradores de esta finca",
            status_code=403
        )

    logger.info(f"Usuario {user.name} tiene permiso 'read_collaborators' en la finca ID {farm_id}")

    # 6. Obtener los colaboradores activos de la finca junto con su rol y user_id
    collaborators_query = db.query(Users.user_id, Users.name, Users.email, Roles.name.label("role")).join(
        UserRoleFarm, Users.user_id == UserRoleFarm.user_id
    ).join(
        Roles, UserRoleFarm.role_id == Roles.role_id
    ).filter(
        UserRoleFarm.farm_id == farm_id,
        UserRoleFarm.user_role_farm_state_id == urf_active_state.user_role_farm_state_id
    ).all()

    logger.info(f"Colaboradores encontrados: {collaborators_query}")

    # 7. Convertir los resultados a una lista de dicts
    collaborators_list = [
        {"user_id": user_id, "name": name, "email": email, "role": role}
        for user_id, name, email, role in collaborators_query
    ]

    # 8. Devolver la respuesta con la lista de colaboradores
    return create_response(
        "success",
        "Colaboradores obtenidos exitosamente",
        data=collaborators_list,
        status_code=200
    )
