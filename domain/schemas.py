from pydantic import BaseModel, Field
from typing import List

# --- Farms ---
class CreateFarmRequest(BaseModel):
    name: str
    area: float
    area_unit_id: int

class ListFarmResponse(BaseModel):
    farm_id: int
    name: str
    area: float
    area_unit_id: int
    area_unit: str
    farm_state_id: int
    farm_state: str
    user_role_id: int
    role: str

class UpdateFarmRequest(BaseModel):
    farm_id: int
    name: str
    area: float
    area_unit_id: int

# --- Plots ---
class CreatePlotRequest(BaseModel):
    name: str = Field(..., max_length=255, description="Nombre del lote. Máximo 255 caracteres.")
    coffee_variety_id: int = Field(..., description="ID de la variedad de café.")
    latitude: float = Field(..., ge=-90, le=90, description="Latitud del lote.")
    longitude: float = Field(..., ge=-180, le=180, description="Longitud del lote.")
    altitude: float = Field(..., ge=0, le=3000, description="Altitud del lote en metros.")
    farm_id: int = Field(..., description="ID de la finca a la que pertenece el lote.")

class UpdatePlotGeneralInfoRequest(BaseModel):
    plot_id: int = Field(..., description="ID del lote a actualizar.")
    name: str = Field(..., max_length=255, description="Nuevo nombre del lote. Máximo 255 caracteres.")
    coffee_variety_id: int = Field(..., description="ID de la nueva variedad de café.")

class UpdatePlotLocationRequest(BaseModel):
    plot_id: int = Field(..., description="ID del lote a actualizar.")
    latitude: float = Field(..., ge=-90, le=90, description="Nueva latitud del lote.")
    longitude: float = Field(..., ge=-180, le=180, description="Nueva longitud del lote.")
    altitude: float = Field(..., ge=0, le=3000, description="Nueva altitud del lote en metros.")

# --- Collaborators ---

class EditCollaboratorRoleRequest(BaseModel):
    collaborator_id: int
    new_role_id: int

    class Config:
        populate_by_name = True
        from_attributes = True

class DeleteCollaboratorRequest(BaseModel):
    collaborator_id: int = Field(..., alias="collaborator_id")

    class Config:
        populate_by_name = True
        from_attributes = True

    def validate_input(self):
        if self.collaborator_id <= 0:
            raise ValueError("El `collaborator_id` debe ser un entero positivo.")

# --- Collaborators Response Schemas ---

class CollaboratorInfo(BaseModel):
    user_role_id: int
    user_id: int
    user_name: str
    user_email: str
    role_id: int
    role_name: str

class ListCollaboratorsResponse(BaseModel):
    status: str
    message: str
    collaborators: List[CollaboratorInfo]

class EditCollaboratorRoleResponse(BaseModel):
    status: str
    message: str

class DeleteCollaboratorResponse(BaseModel):
    status: str
    message: str

# --- Farms Service (internal) ---
class FarmDetailResponse(BaseModel):
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

class UserRoleFarmCreateRequest(BaseModel):
    user_role_id: int
    farm_id: int
    user_role_farm_state_id: int

# --- User Service Models ---
class UserResponse(BaseModel):
    user_id: int
    name: str
    email: str
