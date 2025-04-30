import requests
import logging
import os
from dotenv import load_dotenv
import httpx
from typing import Optional

# Load environment variables
load_dotenv(override=True, encoding="utf-8")

logger = logging.getLogger(__name__)

USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:8000")

def get_role_name_for_user_role(user_role_id):
    """
    Gets the role name associated with a user_role_id by calling the user service API.
    
    Args:
        user_role_id (int): ID of the UserRole entry
        
    Returns:
        str: The name of the role, or "Unknown" if not found
    """
    user_service_url = os.getenv("USER_SERVICE_URL", "http://localhost:8000")
    
    try:
        response = requests.get(
            f"{user_service_url}/roles/user-role/{user_role_id}",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("role_name", "Unknown")
        else:
            logger.error(f"Error getting role name: {response.text}")
            return "Unknown"
    except Exception as e:
        logger.error(f"Exception getting role name: {str(e)}")
        return "Unknown"

def get_user_role_ids(user_id: int, user_service_url: str):
    """
    Consulta los user_role_id de un usuario en el microservicio de usuarios.

    Args:
        user_id (int): ID del usuario.
        user_service_url (str): URL base del microservicio de usuarios.

    Returns:
        list: Lista de user_role_id asociados al usuario.
    Raises:
        Exception: Si la petición falla o la respuesta es inválida.
    """
    url = f"{user_service_url}/roles/user-role-ids/{user_id}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data.get("user_role_ids", [])
    else:
        raise Exception(f"Error al consultar user_role_ids: {response.text}")

def verify_session_token(session_token: str) -> Optional[dict]:
    """
    Verifica el token de sesión haciendo una solicitud al servicio de usuarios.
    Retorna un diccionario con los datos del usuario si es válido, o None si no lo es.
    """
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.post(f"{USER_SERVICE_URL}/session-token-verification", json={"session_token": session_token})
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success" and "user" in data.get("data", {}):
                    return data["data"]["user"]
            logger.warning(f"Token inválido o error en la verificación: {response.text}")
    except Exception as e:
        logger.error(f"Error al verificar el token de sesión: {e}")
    return None