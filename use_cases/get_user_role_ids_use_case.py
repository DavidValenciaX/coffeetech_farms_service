import requests

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
