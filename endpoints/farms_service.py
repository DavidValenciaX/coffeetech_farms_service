from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from dataBase import get_db_session
from utils.response import create_response
from pydantic import BaseModel
from models.models import Farms, UserRoleFarm, UserRoleFarmStates
from adapters.user_client import get_user_role_ids
import logging

router = APIRouter()

logger = logging.getLogger(__name__)

class FarmDetailResponse(BaseModel):
    """
    Modelo de datos para la respuesta al obtener detalles de una finca.
    """
    farm_id: int
    name: str
    area: float
    area_unit_id: int
    area_unit: str
    farm_state_id: int
    farm_state: str

class UserRoleFarmResponse(BaseModel):
    user_role_farm_id: int
    user_role_id: int
    farm_id: int
    user_role_farm_state_id: int
    user_role_farm_state: str

@router.get("/get-farm/{farm_id}", response_model=FarmDetailResponse, include_in_schema=False)
def get_farm_endpoint(farm_id: int, db: Session = Depends(get_db_session)):
    """
    Obtiene una finca por su ID y retorna la información básica.
    """
    farm = db.query(Farms).filter(Farms.farm_id == farm_id).first()
    if not farm:
        return create_response("error", "Finca no encontrada", status_code=404)
    return FarmDetailResponse(
        farm_id=farm.farm_id,
        name=farm.name,
        area=float(farm.area),
        area_unit_id=farm.area_unit_id,
        area_unit=farm.area_unit.name if farm.area_unit else None,
        farm_state_id=farm.farm_state_id,
        farm_state=farm.state.name if farm.state else None,
    )

@router.get("/get-user-role-farm/{user_id}/{farm_id}", response_model=UserRoleFarmResponse, include_in_schema=False)
def get_user_role_farm(user_id: int, farm_id:int, db: Session = Depends(get_db_session)):
    """
    Obtiene la relación user_role_farm y su estado para un usuario y finca.
    """
    try:
        # 1. Get user_role_ids from user service
        user_role_ids = get_user_role_ids(user_id)
        if not user_role_ids:
            logger.warning(f"No user_role_ids found for user_id {user_id}")
            return create_response("error", "No roles found for the user", status_code=404)

        # 2. Query UserRoleFarm using user_role_ids and farm_id
        urf = db.query(UserRoleFarm).filter(
            UserRoleFarm.user_role_id.in_(user_role_ids),
            UserRoleFarm.farm_id == farm_id
        ).first()

        if not urf:
            logger.warning(f"No UserRoleFarm found for user_id {user_id} (roles: {user_role_ids}) and farm_id {farm_id}")
            return create_response("error", "No existe relación user_role_farm para este usuario y finca", status_code=404)

        # 3. Return the found UserRoleFarm details
        return UserRoleFarmResponse(
            user_role_farm_id=urf.user_role_farm_id,
            user_role_id=urf.user_role_id,
            farm_id=farm_id,
            user_role_farm_state_id=urf.user_role_farm_state_id,
            user_role_farm_state=urf.state.name if urf.state else None
        )
    except Exception as e:
        logger.error(f"Error getting user_role_farm for user_id {user_id}, farm_id {farm_id}: {str(e)}")
        # Raise HTTPException for internal errors to ensure proper FastAPI handling
        raise HTTPException(status_code=500, detail="Internal server error retrieving user role farm relationship")