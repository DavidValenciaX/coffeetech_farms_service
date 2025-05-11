from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any
from pydantic import BaseModel, EmailStr, Field
from dataBase import get_db_session
from utils.response import create_response, session_token_invalid_response
from adapters.user_client import verify_session_token
import logging
from use_cases.list_collaborators_use_case import list_collaborators
from use_cases.edit_collaborator_role_use_case import edit_collaborator_role
from use_cases.delete_collaborator_use_case import delete_collaborator

logger = logging.getLogger(__name__)

router = APIRouter()

# Modelo Pydantic actualizado para la respuesta de colaborador
class Collaborator(BaseModel):
    """
    Modelo Pydantic para representar un colaborador.

    Attributes:
        user_id (int): ID del usuario del colaborador.
        name (str): Nombre del colaborador.
        email (EmailStr): Correo electrónico del colaborador.
        role (str): Rol del colaborador.
    """
    user_id: int
    name: str
    email: EmailStr
    role: str

    class Config:
        from_attributes = True
        
# Modelo Pydantic para la solicitud de edición de rol
class EditCollaboratorRoleRequest(BaseModel):
    """
    Modelo Pydantic para la solicitud de edición de rol de un colaborador.

    Attributes:
        collaborator_id (int): ID del usuario colaborador cuyo rol se desea editar.
        new_role_id (int): ID del nuevo rol que se asignará al colaborador.
    """
    collaborator_id: int
    new_role_id: int

    class Config:
        populate_by_name = True
        from_attributes = True
        
# Modelo Pydantic para la solicitud de eliminación de colaborador
class DeleteCollaboratorRequest(BaseModel):
    """
    Modelo Pydantic para la solicitud de eliminación de un colaborador.

    Attributes:
        collaborator_user_role_id (int): ID de la relación usuario-rol del colaborador que se desea eliminar.
    """
    collaborator_user_role_id: int = Field(..., alias="collaborator_user_role_id")

    class Config:
        populate_by_name = True
        from_attributes = True

    def validate_input(self):
        if self.collaborator_user_role_id <= 0:
            raise ValueError("El `collaborator_user_role_id` debe ser un entero positivo.")

@router.get("/list-collaborators", response_model=Dict[str, Any])
def list_collaborators_endpoint(
    farm_id: int,
    session_token: str,
    db: Session = Depends(get_db_session)
):
    """
    Endpoint para listar los colaboradores de una finca específica.
    """
    # Verificar el session_token y obtener el usuario autenticado
    user = verify_session_token(session_token)
    if not user:
        return session_token_invalid_response()
    logger.info(f"Usuario autenticado: {user.name} (ID: {user.user_id})")
    return list_collaborators(farm_id, user, db=db)

@router.post("/edit-collaborator-role", response_model=Dict[str, Any])
def edit_collaborator_role_endpoint(
    edit_request: EditCollaboratorRoleRequest, 
    farm_id: int,
    session_token: str,
    db: Session = Depends(get_db_session)
):
    """
    ### Descripción:
    Endpoint para editar el rol de un colaborador en una finca específica.

    ### Parámetros:
    - **edit_request (EditCollaboratorRoleRequest)**: Objeto con los campos `collaborator_id` y `new_role_id`, que contiene la ID del usuario colaborador y el ID del nuevo rol que se le asignará.
    - **farm_id (int)**: ID de la finca donde se cambiará el rol del colaborador.
    - **session_token (str)**: Token de sesión del usuario autenticado que está realizando la acción.
    - **db (Session)**: Sesión de la base de datos obtenida mediante la dependencia `get_db_session`.

    ### Proceso:
    1. **Autenticación**: Se verifica el `session_token` para autenticar al usuario.
    2. **Verificación de la finca**: Se comprueba si la finca existe.
    3. **Búsqueda de rol del colaborador**: Se busca el rol actual del colaborador en la finca especificada.
    4. **Estado 'Activo'**: Se busca el estado 'Activo' para roles en fincas (`user_role_farm`).
    5. **Rol actual del usuario**: Se verifica el rol del usuario que realiza la acción en la finca.
    6. **Verificación del colaborador**: Se obtiene al colaborador cuyo rol se desea editar.
    7. **Evitar auto-cambio de rol**: El usuario no puede cambiar su propio rol.
    8. **Rol del colaborador actual**: Se comprueba el rol actual del colaborador en la finca.
    9. **Permisos necesarios**: Se verifican los permisos del usuario para asignar el nuevo rol.
    10. **Jerarquía de roles**: Se valida la jerarquía de roles para determinar si el usuario puede asignar el nuevo rol.
    11. **Actualización del rol**: Se actualiza el rol del colaborador en la base de datos.
    
    ### Respuestas:
    - **200 (success)**: El rol del colaborador ha sido actualizado exitosamente.
    - **400 (error)**: Error de validación de entrada o intento de asignar el mismo rol.
    - **403 (error)**: El usuario no tiene permisos suficientes o intentó cambiar su propio rol.
    - **404 (error)**: La finca, el colaborador o su rol en la finca no existen.
    - **500 (error)**: Error interno del servidor al procesar la solicitud.
    """
        
    user = verify_session_token(session_token)
    if not user:
        return session_token_invalid_response()

    logger.info(f"Usuario autenticado: {user.name} (ID: {user.user_id})")

    # Lógica de negocio delegada al use case (already expects new_role_id in edit_request)
    return edit_collaborator_role(edit_request, farm_id, user, db)

@router.post("/delete-collaborator", response_model=Dict[str, Any])
def delete_collaborator_endpoint(
    delete_request: DeleteCollaboratorRequest,
    farm_id: int,
    session_token: str,
    db: Session = Depends(get_db_session)
):
    """
    Elimina un colaborador de una finca específica.

    Parámetros:
    - delete_request (DeleteCollaboratorRequest): Cuerpo de la solicitud que contiene el ID del colaborador a eliminar.
    - farm_id (int): ID de la finca desde la que se eliminará al colaborador.
    - session_token (str): Token de sesión del usuario que realiza la solicitud.
    - db (Session): Sesión de la base de datos proporcionada por FastAPI con `Depends`.

    Retornos:
    - Dict[str, Any]: Respuesta indicando éxito o error con el mensaje adecuado.

    Posibles Respuestas:
    - 200: Colaborador eliminado exitosamente.
    - 400: Error en la validación de la solicitud o algún otro fallo.
    - 403: El usuario no tiene permisos o está intentando eliminarse a sí mismo.
    - 404: Finca o colaborador no encontrado.
    - 500: Error en el servidor o al actualizar la base de datos.
    """

    # Validar la entrada
    try:
        delete_request.validate_input()
    except ValueError as e:
        logger.error(f"Validación de entrada fallida: {str(e)}")
        return create_response(
            "error",
            str(e),
            status_code=400
        )

    # Verificar el session_token y obtener el usuario autenticado
    user = verify_session_token(session_token)
    if not user:
        return session_token_invalid_response()

    logger.info(f"Usuario autenticado: {user.name} (ID: {user.user_id})")

    # Lógica de negocio delegada al use case
    return delete_collaborator(delete_request, farm_id, user, db)
