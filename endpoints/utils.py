from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from models.models import AreaUnits, CoffeeVarieties
from dataBase import get_db_session
from sqlalchemy.orm import joinedload

router = APIRouter()

@router.get("/area-units", summary="Obtener lista de unidades de área", description="Obtiene una lista de todas las unidades de área disponibles.")
def list_area_units(db: Session = Depends(get_db_session)):
    """
    Obtiene una lista de todas las unidades de área disponibles.

    Args:
        db (Session): Sesión de base de datos proporcionada por la dependencia.

    Returns:
        dict: Diccionario con el estado, mensaje y datos de las unidades de área.
    """
    # Consulta todas las unidades de área
    area_units = db.query(AreaUnits).all()

    # Construir la respuesta con las unidades de área
    return {
        "status": "success",
        "message": "Unidades de área obtenidas correctamente",
        "data": [
            {
                "area_unit_id": unit.area_unit_id,
                "name": unit.name,
                "abbreviation": unit.abbreviation
            } for unit in area_units
        ]
    }


@router.get("/list-coffee-varieties", summary="Obtener lista de variedades de café", description="Obtiene una lista de todas las variedades de café disponibles junto con sus parcelas asociadas.")
def list_coffee_varieties(db: Session = Depends(get_db_session)):
    """
    Obtiene una lista de todas las variedades de café disponibles junto con sus parcelas asociadas.

    Args:
        db (Session): Sesión de base de datos proporcionada por la dependencia.

    Returns:
        dict: Diccionario con el estado, mensaje y datos de las variedades de café.
    """
    # Consulta todas las variedades de café y carga las parcelas asociadas
    varieties = db.query(CoffeeVarieties).options(joinedload(CoffeeVarieties.plots)).all()

    # Construir la respuesta con las variedades de café y sus parcelas asociadas
    return {
        "status": "success",
        "message": "Variedades de café obtenidas correctamente",
        "data": [
            {
                "coffee_variety_id": variety.coffee_variety_id,
                "name": variety.name
            } for variety in varieties
        ]
    }
