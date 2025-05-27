import logging
from fastapi import HTTPException
from models.models import Farms, UserRoleFarm, AreaUnits, FarmStates
from utils.response import create_response
from utils.state import get_state
from adapters.user_client import get_role_name_for_user_role, get_user_role_ids

logger = logging.getLogger(__name__)

def list_farms(user, db, list_farm_response):
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
        # Get all user_role_ids for the current user
        try:
            user_role_ids = get_user_role_ids(user.user_id)
        except Exception as e:
            logger.error(f"Error al obtener user_role_ids para el usuario {user.user_id}: {str(e)}")
            return create_response("error", f"Error al obtener información de roles del usuario: {str(e)}", status_code=500)
        
        if not user_role_ids:
            logger.warning(f"No se encontraron roles para el usuario {user.user_id}")
            return create_response("success", "No se encontraron fincas asociadas al usuario", {"farms": []})

        # Query farms using user_role_ids instead of user_id
        farms = db.query(Farms, AreaUnits, FarmStates, UserRoleFarm).select_from(UserRoleFarm).join(
            Farms, UserRoleFarm.farm_id == Farms.farm_id
        ).join(
            AreaUnits, Farms.area_unit_id == AreaUnits.area_unit_id
        ).join(
            FarmStates, Farms.farm_state_id == FarmStates.farm_state_id
        ).filter(
            UserRoleFarm.user_role_id.in_(user_role_ids),
            UserRoleFarm.user_role_farm_state_id == active_urf_state.user_role_farm_state_id,
            Farms.farm_state_id == active_farm_state.farm_state_id
        ).all()

        farm_list = []
        for farm, area_unit, farm_state, user_role_farm in farms:
            # Get role name from user service
            role_name = get_role_name_for_user_role(user_role_farm.user_role_id)
            
            farm_list.append(list_farm_response(
                farm_id=farm.farm_id,
                name=farm.name,
                area=farm.area,
                area_unit_id=farm.area_unit_id,  
                area_unit=area_unit.name,
                farm_state_id=farm.farm_state_id,  
                farm_state=farm_state.name,
                user_role_id=user_role_farm.user_role_id,  
                role=role_name  
            ))

        return create_response("success", "Lista de fincas obtenida exitosamente", {"farms": farm_list})

    except Exception as e:
        logger.error("Error al obtener la lista de fincas: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Error al obtener la lista de fincas: {str(e)}")