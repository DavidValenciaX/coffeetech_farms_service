import logging
from fastapi import HTTPException
from models.models import Farms, UserRoleFarm, AreaUnits, FarmStates
from utils.response import create_response
from utils.state import get_state

logger = logging.getLogger(__name__)

def list_farms_use_case(user, db, ListFarmResponse):
    # Obtener el state "Activo" para el tipo "Farms"
    active_farm_state = get_state(db, "Activo", "Farms")
    if not active_farm_state:
        logger.error("No se encontró el estado 'Activo' para el tipo 'Farms'")
        return create_response("error", "Estado 'Activo' no encontrado para Farms", status_code=400)

    # Obtener el state "Activo" para el tipo "user_role_farm"
    active_urf_state = get_state(db, "Activo", "user_role_farm")
    if not active_urf_state:
        logger.error("No se encontró el estado 'Activo' para el tipo 'user_role_farm'")
        return create_response("error", "Estado 'Activo' no encontrado para user_role_farm", status_code=400)

    try:
        farms = db.query(Farms, AreaUnits, FarmStates, Roles).select_from(UserRoleFarm).join(
            Farms, UserRoleFarm.farm_id == Farms.farm_id
        ).join(
            AreaUnits, Farms.area_unit_id == AreaUnits.area_unit_id
        ).join(
            FarmStates, Farms.farm_state_id == FarmStates.farm_state_id
        ).join(
            Roles, UserRoleFarm.role_id == Roles.role_id
        ).filter(
            UserRoleFarm.user_id == user.user_id,
            UserRoleFarm.user_role_farm_state_id == active_urf_state.user_role_farm_state_id,
            Farms.farm_state_id == active_farm_state.farm_state_id
        ).all()

        farm_list = []
        for farm, area_unit, farm_state, role in farms:
            farm_list.append(ListFarmResponse(
                farm_id=farm.farm_id,
                name=farm.name,
                area=farm.area,
                area_unit=area_unit.name,
                farm_state=farm_state.name,
                role=role.name
            ))

        return create_response("success", "Lista de fincas obtenida exitosamente", {"farms": farm_list})

    except Exception as e:
        logger.error("Error al obtener la lista de fincas: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Error al obtener la lista de fincas: {str(e)}")