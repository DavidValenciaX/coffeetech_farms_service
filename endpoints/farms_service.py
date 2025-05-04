from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from dataBase import get_db_session
from utils.response import create_response
from pydantic import BaseModel
from models.models import Farms

router = APIRouter()

class FarmDetailResponse(BaseModel):
    """
    Modelo de datos para la respuesta al obtener detalles de una finca.
    """
    farm_id: int
    name: str
    area: float
    area_unit_id: int
    area_unit: str  # Nombre descriptivo de la unidad
    farm_state_id: int
    farm_state: str  # Nombre descriptivo del estado


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