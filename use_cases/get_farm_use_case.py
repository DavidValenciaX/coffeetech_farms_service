from models.models import Farms, AreaUnits, FarmStates, UserRoleFarm
from utils.response import create_response
from utils.state import get_state
from adapters.user_client import get_role_name_for_user_role, get_user_role_ids
import logging

logger = logging.getLogger(__name__)

def get_farm(farm_id: int, user, db, ListFarmResponse):
    # Obtener el state "Activo" para la finca y user_role_farm
    active_farm_state = get_state(db, "Activo", "Farms")
    if not active_farm_state:
        logger.error("No se encontró el estado 'Activo' para el tipo 'Farms'")
        return create_response("error", "Estado 'Activo' no encontrado para Farms", status_code=400)

    active_urf_state = get_state(db, "Activo", "user_role_farm")
    if not active_urf_state:
        logger.error("No se encontró el estado 'Activo' para el tipo 'user_role_farm'")
        return create_response("error", "Estado 'Activo' no encontrado para user_role_farm", status_code=400)

    try:
        # Obtener los user_role_ids del usuario desde el microservicio de usuarios
        try:
            user_role_ids = get_user_role_ids(user.user_id)
        except Exception as e:
            logger.error(f"Error al obtener user_role_ids para el usuario {user.user_id}: {str(e)}")
            return create_response("error", f"Error al obtener información de roles del usuario: {str(e)}", status_code=500)

        if not user_role_ids:
            logger.warning(f"No se encontraron roles para el usuario {user.user_id}")
            return create_response("error", "Finca no encontrada o no pertenece al usuario")

        # Buscar la finca asociada a alguno de los user_role_ids activos
        farm_data = db.query(Farms, AreaUnits, FarmStates, UserRoleFarm).select_from(UserRoleFarm).join(
            Farms, UserRoleFarm.farm_id == Farms.farm_id
        ).join(
            AreaUnits, Farms.area_unit_id == AreaUnits.area_unit_id
        ).join(
            FarmStates, Farms.farm_state_id == FarmStates.farm_state_id
        ).filter(
            UserRoleFarm.user_role_id.in_(user_role_ids),
            UserRoleFarm.user_role_farm_state_id == active_urf_state.user_role_farm_state_id,
            Farms.farm_state_id == active_farm_state.farm_state_id,
            Farms.farm_id == farm_id
        ).first()

        # Validar si se encontró la finca
        if not farm_data:
            logger.warning("Finca no encontrada o no pertenece al usuario")
            return create_response("error", "Finca no encontrada o no pertenece al usuario")

        farm, area_unit, farm_state, user_role_farm = farm_data

        # Obtener el nombre del rol desde el microservicio de usuarios
        role_name = get_role_name_for_user_role(user_role_farm.user_role_id)

        # Crear la respuesta en el formato esperado
        farm_response = ListFarmResponse(
            farm_id=farm.farm_id,
            name=farm.name,
            area=farm.area,
            area_unit=area_unit.name,
            area_unit_id=farm.area_unit_id,
            farm_state=farm_state.name,
            farm_state_id=farm.farm_state_id,
            role=role_name,
            user_role_id=user_role_farm.user_role_id
        )

        return create_response("success", "Finca obtenida exitosamente", {"farm": farm_response})

    except Exception as e:
        # Log detallado para administradores, pero respuesta genérica para el usuario
        logger.error("Error al obtener la finca: %s", str(e))
        return create_response("error", "Ocurrió un error al intentar obtener la finca. Por favor, inténtalo de nuevo más tarde.")