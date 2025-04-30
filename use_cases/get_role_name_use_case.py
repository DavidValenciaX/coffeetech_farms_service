import requests
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True, encoding="utf-8")

logger = logging.getLogger(__name__)

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