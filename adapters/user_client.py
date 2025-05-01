import logging
from typing import Optional, Any, Dict, List, Union
import httpx
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv(override=True, encoding="utf-8")

logger = logging.getLogger(__name__)

USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:8000")
DEFAULT_TIMEOUT = 10.0

def _make_request(
    endpoint: str,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    timeout: float = DEFAULT_TIMEOUT
) -> Optional[Dict[str, Any]]:
    """
    Base function to make HTTP requests to the user service.
    
    Args:
        endpoint (str): The API endpoint to call (without base URL)
        method (str): HTTP method to use ('GET', 'POST', etc.)
        data (dict, optional): JSON data to send in the request body
        params (dict, optional): Query parameters to include in the request
        timeout (float): Request timeout in seconds
        
    Returns:
        dict: Response data as dictionary if successful, None otherwise
    """
    url = f"{USER_SERVICE_URL}{endpoint}"
    
    try:
        with httpx.Client(timeout=timeout) as client:
            if method.upper() == "GET":
                response = client.get(url, params=params)
            elif method.upper() == "POST":
                response = client.post(url, json=data)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return None
                
            if response.status_code in (200, 201):
                return response.json()
            else:
                logger.error(f"Error calling {url}: {response.status_code} - {response.text}")
                return None
    except Exception as e:
        logger.error(f"Exception calling {url}: {str(e)}")
        return None

def get_role_name_for_user_role(user_role_id: int) -> str:
    """
    Gets the role name associated with a user_role_id by calling the user service API.
    
    Args:
        user_role_id (int): ID of the UserRole entry
        
    Returns:
        str: The name of the role, or "Unknown" if not found
    """
    response = _make_request(f"/roles/user-role/{user_role_id}")
    return response.get("role_name", "Unknown") if response else "Unknown"

def get_user_role_ids(user_id: int) -> List[int]:
    """
    Retrieves user_role_ids for a user from the users microservice.

    Args:
        user_id (int): ID of the user

    Returns:
        list: List of user_role_ids associated with the user
        
    Raises:
        Exception: If the request fails or response is invalid
    """
    response = _make_request(f"/roles/user-role-ids/{user_id}")
    
    if response:
        return response.get("user_role_ids", [])
    else:
        raise Exception(f"Error retrieving user_role_ids for user {user_id}")

def verify_session_token(session_token: str) -> Optional[Dict[str, Any]]:
    """
    Verifies a session token by making a request to the user service.
    Returns user data if the token is valid, None otherwise.
    
    Args:
        session_token (str): Session token to verify
        
    Returns:
        dict: User data if token is valid, None otherwise
    """
    response = _make_request(
        "/session-token-verification", 
        method="POST", 
        data={"session_token": session_token}
    )
    
    if response and response.get("status") == "success" and "user" in response.get("data", {}):
        return response["data"]["user"]
    return None

def create_user_role(user_id: int, role_name: str) -> dict:
    """
    Creates a UserRole for the given user in the user service.

    Args:
        user_id (int): The user ID.
        role_name (str): The role name to assign.

    Returns:
        dict: The response data from the user service.

    Raises:
        Exception: If the request fails or response is invalid.
    """
    response = _make_request(
        "/roles/user-role",
        method="POST",
        data={"user_id": user_id, "role_name": role_name}
    )
    if response and "user_role_id" in response:
        return response
    else:
        raise Exception(f"Error creating user_role for user {user_id} with role '{role_name}': {response}")

def get_role_permissions_for_user_role(user_role_id: int) -> list:
    """
    Gets the list of permission names for a given user_role_id from the user service.

    Args:
        user_role_id (int): ID of the UserRole entry

    Returns:
        list: List of permission names (str)
    """
    response = _make_request(f"/roles/user-role/{user_role_id}/permissions")
    if response and "permissions" in response:
        return [perm["name"] for perm in response["permissions"]]
    return []


def get_collaborators_info(user_role_ids: list) -> list:
    """
    Obtiene la información de los colaboradores desde el microservicio de usuarios.
    Args:
        user_role_ids (list): Lista de IDs de user_role a consultar.
    Returns:
        list: Lista de colaboradores con su información, o lanza una excepción si falla.
    """
    response = _make_request(
        "/roles/user-role/bulk-info",
        method="POST",
        data={"user_role_ids": user_role_ids}
    )
    if response and "collaborators" in response:
        return response["collaborators"]
    else:
        raise Exception("No se pudo obtener la información de los colaboradores desde el microservicio de usuarios")