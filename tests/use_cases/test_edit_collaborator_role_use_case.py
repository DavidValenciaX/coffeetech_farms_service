"""
Pruebas unitarias para edit_collaborator_role_use_case.py
"""
import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from use_cases.edit_collaborator_role_use_case import edit_collaborator_role
from domain.schemas import EditCollaboratorRoleRequest, EditCollaboratorRoleResponse
from models.models import Farms, UserRoleFarm, UserRoleFarmStates
from adapters.user_client import (
    UserRoleRetrievalError,
    UserRoleCreationError
)


class TestEditCollaboratorRoleUseCase:
    """Clase de pruebas para el caso de uso de edición de rol de colaborador"""
    
    def setup_method(self):
        """Configuración inicial para cada prueba"""
        self.db_mock = Mock(spec=Session)
        self.user_mock = Mock()
        self.user_mock.user_id = "test_user_id"
        
        # Mock farm
        self.farm_mock = Mock(spec=Farms)
        self.farm_mock.farm_id = 1
        self.farm_mock.name = "Test Farm"
        
        # Mock states
        self.active_state_mock = Mock(spec=UserRoleFarmStates)
        self.active_state_mock.user_role_farm_state_id = 1
        self.active_state_mock.name = "Activo"
        
        # Mock user role farm
        self.user_role_farm_mock = Mock(spec=UserRoleFarm)
        self.user_role_farm_mock.user_role_id = 100
        self.user_role_farm_mock.farm_id = 1
        
        # Mock collaborator role farm
        self.collaborator_role_farm_mock = Mock(spec=UserRoleFarm)
        self.collaborator_role_farm_mock.user_role_id = 200
        self.collaborator_role_farm_mock.farm_id = 1
        
        # Mock edit request
        self.edit_request = EditCollaboratorRoleRequest(
            collaborator_id=2,
            new_role_id=3
        )

    @patch('use_cases.edit_collaborator_role_use_case.get_state')
    @patch('use_cases.edit_collaborator_role_use_case.get_user_role_ids')
    @patch('use_cases.edit_collaborator_role_use_case.get_user_role_id_for_farm')
    @patch('use_cases.edit_collaborator_role_use_case.get_collaborators_info')
    @patch('use_cases.edit_collaborator_role_use_case.get_role_name_for_user_role')
    @patch('use_cases.edit_collaborator_role_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.edit_collaborator_role_use_case.get_role_name_by_id')
    @patch('use_cases.edit_collaborator_role_use_case.create_user_role_for_farm')
    def test_edit_collaborator_role_success_propietario_to_administrador(
        self, mock_create_user_role, mock_get_role_name_by_id, mock_get_permissions,
        mock_get_role_name, mock_get_collaborators_info, mock_get_user_role_id_for_farm,
        mock_get_user_role_ids, mock_get_state
    ):
        """Test successful role change from Propietario to Administrador de finca"""
        # Setup mocks
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm exists
            self.user_role_farm_mock,  # User role farm
            self.collaborator_role_farm_mock  # Collaborator role farm
        ]
        
        mock_get_state.return_value = self.active_state_mock
        mock_get_user_role_ids.return_value = [100]
        mock_get_user_role_id_for_farm.return_value = 200
        mock_get_collaborators_info.return_value = [{
            'user_name': 'Test Collaborator',
            'user_id': 2
        }]
        mock_get_role_name.side_effect = [
            'Propietario',  # Current user role
            'Operador de campo'  # Collaborator current role
        ]
        mock_get_role_name_by_id.return_value = 'Administrador de finca'  # New role
        mock_get_permissions.return_value = ['edit_administrator_farm']
        mock_create_user_role.return_value = 300  # New user_role_id
        
        # Execute
        result = edit_collaborator_role(self.edit_request, 1, self.user_mock, self.db_mock)
        
        # Assertions
        assert isinstance(result, EditCollaboratorRoleResponse)
        assert result.status == "success"
        assert "Test Collaborator" in result.message
        assert "Administrador de finca" in result.message
        
        # Verify database operations
        self.db_mock.commit.assert_called_once()
        mock_create_user_role.assert_called_once_with(2, 3)
        
        # Verify collaborator role was updated
        assert self.collaborator_role_farm_mock.user_role_id == 300

    @patch('use_cases.edit_collaborator_role_use_case.get_state')
    @patch('use_cases.edit_collaborator_role_use_case.get_user_role_ids')
    @patch('use_cases.edit_collaborator_role_use_case.get_user_role_id_for_farm')
    @patch('use_cases.edit_collaborator_role_use_case.get_collaborators_info')
    @patch('use_cases.edit_collaborator_role_use_case.get_role_name_for_user_role')
    @patch('use_cases.edit_collaborator_role_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.edit_collaborator_role_use_case.get_role_name_by_id')
    @patch('use_cases.edit_collaborator_role_use_case.create_user_role_for_farm')
    def test_edit_collaborator_role_success_administrador_to_operador(
        self, mock_create_user_role, mock_get_role_name_by_id, mock_get_permissions,
        mock_get_role_name, mock_get_collaborators_info, mock_get_user_role_id_for_farm,
        mock_get_user_role_ids, mock_get_state
    ):
        """Test successful role change from Administrador to Operador de campo"""
        # Setup mocks
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm exists
            self.user_role_farm_mock,  # User role farm
            self.collaborator_role_farm_mock  # Collaborator role farm
        ]
        
        mock_get_state.return_value = self.active_state_mock
        mock_get_user_role_ids.return_value = [100]
        mock_get_user_role_id_for_farm.return_value = 200
        mock_get_collaborators_info.return_value = [{
            'user_name': 'Test Collaborator',
            'user_id': 2
        }]
        mock_get_role_name.side_effect = [
            'Administrador de finca',  # Current user role
            'Administrador de finca'  # Collaborator current role
        ]
        mock_get_role_name_by_id.return_value = 'Operador de campo'  # New role
        mock_get_permissions.return_value = ['edit_operator_farm']
        mock_create_user_role.return_value = 300  # New user_role_id
        
        # Execute
        result = edit_collaborator_role(self.edit_request, 1, self.user_mock, self.db_mock)
        
        # Assertions
        assert isinstance(result, EditCollaboratorRoleResponse)
        assert result.status == "success"
        assert "Test Collaborator" in result.message
        assert "Operador de campo" in result.message

    def test_edit_collaborator_role_invalid_farm(self):
        """Test editing role with invalid farm ID"""
        # Setup: Farm not found
        self.db_mock.query.return_value.filter.return_value.first.return_value = None
        
        # Execute
        result = edit_collaborator_role(self.edit_request, 999, self.user_mock, self.db_mock)
        
        # Assertions
        assert result.status_code == 404
        assert "Finca no encontrada" in str(result.body)

    @patch('use_cases.edit_collaborator_role_use_case.get_state')
    @patch('use_cases.edit_collaborator_role_use_case.get_user_role_ids')
    def test_edit_collaborator_role_user_not_associated_with_farm(self, mock_get_user_role_ids, mock_get_state):
        """Test editing role when user is not associated with the farm"""
        # Setup mocks
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm exists
            None  # User not associated with farm
        ]
        mock_get_state.return_value = self.active_state_mock
        mock_get_user_role_ids.return_value = [100]
        
        # Execute
        result = edit_collaborator_role(self.edit_request, 1, self.user_mock, self.db_mock)
        
        # Assertions
        assert result.status_code == 403
        response_body = result.body.decode('utf-8')
        assert "No estás asociado a esta finca" in response_body

    @patch('use_cases.edit_collaborator_role_use_case.get_state')
    @patch('use_cases.edit_collaborator_role_use_case.get_user_role_ids')
    @patch('use_cases.edit_collaborator_role_use_case.get_user_role_id_for_farm')
    @patch('use_cases.edit_collaborator_role_use_case.get_role_name_for_user_role')
    def test_edit_collaborator_role_invalid_collaborator(
        self, mock_get_role_name, mock_get_user_role_id_for_farm, mock_get_user_role_ids, mock_get_state
    ):
        """Test editing role with invalid collaborator ID"""
        # Setup mocks
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm exists
            self.user_role_farm_mock  # User role farm
        ]
        mock_get_state.return_value = self.active_state_mock
        mock_get_user_role_ids.return_value = [100]
        mock_get_user_role_id_for_farm.return_value = None  # Collaborator not found
        mock_get_role_name.return_value = 'Propietario'
        
        # Execute
        result = edit_collaborator_role(self.edit_request, 1, self.user_mock, self.db_mock)
        
        # Assertions
        assert result.status_code == 404
        response_body = result.body.decode('utf-8')
        assert "Colaborador no encontrado en esta finca" in response_body

    @patch('use_cases.edit_collaborator_role_use_case.get_state')
    @patch('use_cases.edit_collaborator_role_use_case.get_user_role_ids')
    @patch('use_cases.edit_collaborator_role_use_case.get_user_role_id_for_farm')
    @patch('use_cases.edit_collaborator_role_use_case.get_collaborators_info')
    @patch('use_cases.edit_collaborator_role_use_case.get_role_name_for_user_role')
    def test_edit_collaborator_role_cannot_edit_own_role(
        self, mock_get_role_name, mock_get_collaborators_info,
        mock_get_user_role_id_for_farm, mock_get_user_role_ids, mock_get_state
    ):
        """Test that user cannot edit their own role"""
        # Setup mocks - same user_role_id for both user and collaborator
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm exists
            self.user_role_farm_mock  # User role farm
        ]
        mock_get_state.return_value = self.active_state_mock
        mock_get_user_role_ids.return_value = [100]
        mock_get_user_role_id_for_farm.return_value = 100  # Same as user's role
        mock_get_collaborators_info.return_value = [{
            'user_name': 'Test User',
            'user_id': 1
        }]
        mock_get_role_name.return_value = 'Propietario'
        
        # Execute
        result = edit_collaborator_role(self.edit_request, 1, self.user_mock, self.db_mock)
        
        # Assertions
        assert result.status_code == 403
        response_body = result.body.decode('utf-8')
        assert "No puedes cambiar tu propio rol" in response_body

    @patch('use_cases.edit_collaborator_role_use_case.get_state')
    @patch('use_cases.edit_collaborator_role_use_case.get_user_role_ids')
    @patch('use_cases.edit_collaborator_role_use_case.get_user_role_id_for_farm')
    @patch('use_cases.edit_collaborator_role_use_case.get_collaborators_info')
    @patch('use_cases.edit_collaborator_role_use_case.get_role_name_for_user_role')
    @patch('use_cases.edit_collaborator_role_use_case.get_role_name_by_id')
    def test_edit_collaborator_role_same_role(
        self, mock_get_role_name_by_id, mock_get_role_name, mock_get_collaborators_info,
        mock_get_user_role_id_for_farm, mock_get_user_role_ids, mock_get_state
    ):
        """Test editing role when collaborator already has the target role"""
        # Setup mocks
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm exists
            self.user_role_farm_mock,  # User role farm
            self.collaborator_role_farm_mock  # Collaborator role farm
        ]
        mock_get_state.return_value = self.active_state_mock
        mock_get_user_role_ids.return_value = [100]
        mock_get_user_role_id_for_farm.return_value = 200
        mock_get_collaborators_info.return_value = [{
            'user_name': 'Test Collaborator',
            'user_id': 2
        }]
        mock_get_role_name.side_effect = [
            'Propietario',  # Current user role
            'Administrador de finca'  # Collaborator current role
        ]
        mock_get_role_name_by_id.return_value = 'Administrador de finca'  # Same as current
        
        # Execute
        result = edit_collaborator_role(self.edit_request, 1, self.user_mock, self.db_mock)
        
        # Assertions
        assert result.status_code == 400
        response_body = result.body.decode('utf-8')
        assert "El colaborador ya tiene el rol" in response_body

    @patch('use_cases.edit_collaborator_role_use_case.get_state')
    @patch('use_cases.edit_collaborator_role_use_case.get_user_role_ids')
    @patch('use_cases.edit_collaborator_role_use_case.get_user_role_id_for_farm')
    @patch('use_cases.edit_collaborator_role_use_case.get_collaborators_info')
    @patch('use_cases.edit_collaborator_role_use_case.get_role_name_for_user_role')
    @patch('use_cases.edit_collaborator_role_use_case.get_role_name_by_id')
    def test_edit_collaborator_role_invalid_new_role(
        self, mock_get_role_name_by_id, mock_get_role_name, mock_get_collaborators_info,
        mock_get_user_role_id_for_farm, mock_get_user_role_ids, mock_get_state
    ):
        """Test editing role with invalid new role ID"""
        # Setup mocks
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm exists
            self.user_role_farm_mock,  # User role farm
            self.collaborator_role_farm_mock  # Collaborator role farm
        ]
        mock_get_state.return_value = self.active_state_mock
        mock_get_user_role_ids.return_value = [100]
        mock_get_user_role_id_for_farm.return_value = 200
        mock_get_collaborators_info.return_value = [{
            'user_name': 'Test Collaborator',
            'user_id': 2
        }]
        mock_get_role_name.side_effect = [
            'Propietario',  # Current user role
            'Operador de campo'  # Collaborator current role
        ]
        mock_get_role_name_by_id.return_value = None  # Invalid role ID
        
        # Execute
        result = edit_collaborator_role(self.edit_request, 1, self.user_mock, self.db_mock)
        
        # Assertions
        assert result.status_code == 400
        response_body = result.body.decode('utf-8')
        assert "Rol con ID" in response_body and "no encontrado" in response_body

    @patch('use_cases.edit_collaborator_role_use_case.get_state')
    @patch('use_cases.edit_collaborator_role_use_case.get_user_role_ids')
    @patch('use_cases.edit_collaborator_role_use_case.get_user_role_id_for_farm')
    @patch('use_cases.edit_collaborator_role_use_case.get_collaborators_info')
    @patch('use_cases.edit_collaborator_role_use_case.get_role_name_for_user_role')
    @patch('use_cases.edit_collaborator_role_use_case.get_role_name_by_id')
    @patch('use_cases.edit_collaborator_role_use_case.get_role_permissions_for_user_role')
    def test_edit_collaborator_role_no_permission(
        self, mock_get_permissions, mock_get_role_name_by_id, mock_get_role_name,
        mock_get_collaborators_info, mock_get_user_role_id_for_farm, mock_get_user_role_ids, mock_get_state
    ):
        """Test editing role when user doesn't have permission"""
        # Setup mocks
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm exists
            self.user_role_farm_mock,  # User role farm
            self.collaborator_role_farm_mock  # Collaborator role farm
        ]
        mock_get_state.return_value = self.active_state_mock
        mock_get_user_role_ids.return_value = [100]
        mock_get_user_role_id_for_farm.return_value = 200
        mock_get_collaborators_info.return_value = [{
            'user_name': 'Test Collaborator',
            'user_id': 2
        }]
        mock_get_role_name.side_effect = [
            'Operador de campo',  # Current user role (insufficient)
            'Operador de campo'  # Collaborator current role
        ]
        mock_get_role_name_by_id.return_value = 'Administrador de finca'  # New role
        mock_get_permissions.return_value = []  # No permissions
        
        # Execute
        result = edit_collaborator_role(self.edit_request, 1, self.user_mock, self.db_mock)
        
        # Assertions
        assert result.status_code == 403
        response_body = result.body.decode('utf-8')
        assert "No tienes permiso para asignar el rol" in response_body

    @patch('use_cases.edit_collaborator_role_use_case.get_state')
    @patch('use_cases.edit_collaborator_role_use_case.get_user_role_ids')
    @patch('use_cases.edit_collaborator_role_use_case.get_user_role_id_for_farm')
    @patch('use_cases.edit_collaborator_role_use_case.get_collaborators_info')
    @patch('use_cases.edit_collaborator_role_use_case.get_role_name_for_user_role')
    @patch('use_cases.edit_collaborator_role_use_case.get_role_name_by_id')
    @patch('use_cases.edit_collaborator_role_use_case.get_role_permissions_for_user_role')
    def test_edit_collaborator_role_hierarchy_violation(
        self, mock_get_permissions, mock_get_role_name_by_id, mock_get_role_name,
        mock_get_collaborators_info, mock_get_user_role_id_for_farm, mock_get_user_role_ids, mock_get_state
    ):
        """Test editing role when violating role hierarchy"""
        # Setup mocks
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm exists
            self.user_role_farm_mock,  # User role farm
            self.collaborator_role_farm_mock  # Collaborator role farm
        ]
        mock_get_state.return_value = self.active_state_mock
        mock_get_user_role_ids.return_value = [100]
        mock_get_user_role_id_for_farm.return_value = 200
        mock_get_collaborators_info.return_value = [{
            'user_name': 'Test Collaborator',
            'user_id': 2
        }]
        mock_get_role_name.side_effect = [
            'Operador de campo',  # Current user role (lower hierarchy)
            'Operador de campo'  # Collaborator current role
        ]
        mock_get_role_name_by_id.return_value = 'Administrador de finca'  # Higher role that operator cannot assign
        mock_get_permissions.return_value = []  # No permissions for operator
        
        # Execute
        result = edit_collaborator_role(self.edit_request, 1, self.user_mock, self.db_mock)
        
        # Assertions
        assert result.status_code == 403
        response_body = result.body.decode('utf-8')
        assert "No tienes permiso para asignar el rol" in response_body

    @patch('use_cases.edit_collaborator_role_use_case.get_state')
    @patch('use_cases.edit_collaborator_role_use_case.get_user_role_ids')
    def test_edit_collaborator_role_user_service_error(self, mock_get_user_role_ids, mock_get_state):
        """Test editing role when user service throws an error"""
        # Setup mocks
        self.db_mock.query.return_value.filter.return_value.first.return_value = self.farm_mock
        mock_get_state.return_value = self.active_state_mock
        mock_get_user_role_ids.side_effect = UserRoleRetrievalError("Service error")
        
        # Execute
        result = edit_collaborator_role(self.edit_request, 1, self.user_mock, self.db_mock)
        
        # Assertions
        assert result.status_code == 500
        response_body = result.body.decode('utf-8')
        assert "No se pudieron obtener los roles del usuario" in response_body

    @patch('use_cases.edit_collaborator_role_use_case.get_state')
    @patch('use_cases.edit_collaborator_role_use_case.get_user_role_ids')
    @patch('use_cases.edit_collaborator_role_use_case.get_user_role_id_for_farm')
    @patch('use_cases.edit_collaborator_role_use_case.get_collaborators_info')
    @patch('use_cases.edit_collaborator_role_use_case.get_role_name_for_user_role')
    def test_edit_collaborator_role_collaborator_info_error(
        self, mock_get_role_name, mock_get_collaborators_info, mock_get_user_role_id_for_farm, mock_get_user_role_ids, mock_get_state
    ):
        """Test editing role when collaborator info retrieval fails"""
        # Setup mocks
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm exists
            self.user_role_farm_mock  # User role farm
        ]
        mock_get_state.return_value = self.active_state_mock
        mock_get_user_role_ids.return_value = [100]
        mock_get_user_role_id_for_farm.return_value = 200
        mock_get_role_name.return_value = 'Propietario'  # User role name succeeds
        mock_get_collaborators_info.side_effect = Exception("Service error")  # Use generic Exception instead of CollaboratorInfoError
        
        # Execute
        result = edit_collaborator_role(self.edit_request, 1, self.user_mock, self.db_mock)
        
        # Assertions
        assert result.status_code == 404
        response_body = result.body.decode('utf-8')
        assert "Colaborador no encontrado" in response_body

    @patch('use_cases.edit_collaborator_role_use_case.get_state')
    @patch('use_cases.edit_collaborator_role_use_case.get_user_role_ids')
    @patch('use_cases.edit_collaborator_role_use_case.get_user_role_id_for_farm')
    @patch('use_cases.edit_collaborator_role_use_case.get_collaborators_info')
    @patch('use_cases.edit_collaborator_role_use_case.get_role_name_for_user_role')
    @patch('use_cases.edit_collaborator_role_use_case.get_role_name_by_id')
    @patch('use_cases.edit_collaborator_role_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.edit_collaborator_role_use_case.create_user_role_for_farm')
    def test_edit_collaborator_role_database_error(
        self, mock_create_user_role, mock_get_permissions, mock_get_role_name_by_id,
        mock_get_role_name, mock_get_collaborators_info, mock_get_user_role_id_for_farm,
        mock_get_user_role_ids, mock_get_state
    ):
        """Test editing role when database operation fails"""
        # Setup mocks
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm exists
            self.user_role_farm_mock,  # User role farm
            self.collaborator_role_farm_mock  # Collaborator role farm
        ]
        mock_get_state.return_value = self.active_state_mock
        mock_get_user_role_ids.return_value = [100]
        mock_get_user_role_id_for_farm.return_value = 200
        mock_get_collaborators_info.return_value = [{
            'user_name': 'Test Collaborator',
            'user_id': 2
        }]
        mock_get_role_name.side_effect = [
            'Propietario',  # Current user role
            'Operador de campo'  # Collaborator current role
        ]
        mock_get_role_name_by_id.return_value = 'Administrador de finca'
        mock_get_permissions.return_value = ['edit_administrator_farm']
        mock_create_user_role.return_value = 300
        
        # Simulate database error
        self.db_mock.commit.side_effect = Exception("Database error")
        
        # Execute
        result = edit_collaborator_role(self.edit_request, 1, self.user_mock, self.db_mock)
        
        # Assertions
        assert result.status_code == 500
        response_body = result.body.decode('utf-8')
        assert "Error al actualizar el rol del colaborador" in response_body
        self.db_mock.rollback.assert_called_once()

    @patch('use_cases.edit_collaborator_role_use_case.get_state')
    @patch('use_cases.edit_collaborator_role_use_case.get_user_role_ids')
    @patch('use_cases.edit_collaborator_role_use_case.get_user_role_id_for_farm')
    @patch('use_cases.edit_collaborator_role_use_case.get_collaborators_info')
    @patch('use_cases.edit_collaborator_role_use_case.get_role_name_for_user_role')
    @patch('use_cases.edit_collaborator_role_use_case.get_role_name_by_id')
    @patch('use_cases.edit_collaborator_role_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.edit_collaborator_role_use_case.create_user_role_for_farm')
    def test_edit_collaborator_role_user_role_creation_error(
        self, mock_create_user_role, mock_get_permissions, mock_get_role_name_by_id,
        mock_get_role_name, mock_get_collaborators_info, mock_get_user_role_id_for_farm,
        mock_get_user_role_ids, mock_get_state
    ):
        """Test editing role when user role creation fails"""
        # Setup mocks
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm exists
            self.user_role_farm_mock,  # User role farm
            self.collaborator_role_farm_mock  # Collaborator role farm
        ]
        mock_get_state.return_value = self.active_state_mock
        mock_get_user_role_ids.return_value = [100]
        mock_get_user_role_id_for_farm.return_value = 200
        mock_get_collaborators_info.return_value = [{
            'user_name': 'Test Collaborator',
            'user_id': 2
        }]
        mock_get_role_name.side_effect = [
            'Propietario',  # Current user role
            'Operador de campo'  # Collaborator current role
        ]
        mock_get_role_name_by_id.return_value = 'Administrador de finca'
        mock_get_permissions.return_value = ['edit_administrator_farm']
        mock_create_user_role.side_effect = UserRoleCreationError("Creation failed")
        
        # Execute
        result = edit_collaborator_role(self.edit_request, 1, self.user_mock, self.db_mock)
        
        # Assertions
        assert result.status_code == 500
        response_body = result.body.decode('utf-8')
        assert "Error al actualizar el rol del colaborador" in response_body
        self.db_mock.rollback.assert_called_once()

    @patch('use_cases.edit_collaborator_role_use_case.get_state')
    def test_edit_collaborator_role_missing_active_state(self, mock_get_state):
        """Test editing role when active state is not found"""
        # Setup: Farm exists but active state not found
        self.db_mock.query.return_value.filter.return_value.first.return_value = self.farm_mock
        mock_get_state.return_value = None
        
        # Execute
        result = edit_collaborator_role(self.edit_request, 1, self.user_mock, self.db_mock)
        
        # Assertions
        assert result.status_code == 400
        response_body = result.body.decode('utf-8')
        assert "Estado 'Activo' no encontrado" in response_body

    @patch('use_cases.edit_collaborator_role_use_case.get_state')
    @patch('use_cases.edit_collaborator_role_use_case.get_user_role_ids')
    @patch('use_cases.edit_collaborator_role_use_case.get_user_role_id_for_farm')
    @patch('use_cases.edit_collaborator_role_use_case.get_collaborators_info')
    @patch('use_cases.edit_collaborator_role_use_case.get_role_name_for_user_role')
    def test_edit_collaborator_role_unknown_user_role(
        self, mock_get_role_name, mock_get_collaborators_info,
        mock_get_user_role_id_for_farm, mock_get_user_role_ids, mock_get_state
    ):
        """Test editing role when user role name is unknown"""
        # Setup mocks
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm exists
            self.user_role_farm_mock  # User role farm
        ]
        mock_get_state.return_value = self.active_state_mock
        mock_get_user_role_ids.return_value = [100]
        mock_get_user_role_id_for_farm.return_value = 200
        mock_get_collaborators_info.return_value = [{
            'user_name': 'Test Collaborator',
            'user_id': 2
        }]
        mock_get_role_name.return_value = "Unknown"  # Unknown role
        
        # Execute
        result = edit_collaborator_role(self.edit_request, 1, self.user_mock, self.db_mock)
        
        # Assertions
        assert result.status_code == 500
        response_body = result.body.decode('utf-8')
        assert "Rol del usuario no encontrado" in response_body

    @patch('use_cases.edit_collaborator_role_use_case.get_state')
    @patch('use_cases.edit_collaborator_role_use_case.get_user_role_ids')
    @patch('use_cases.edit_collaborator_role_use_case.get_user_role_id_for_farm')
    @patch('use_cases.edit_collaborator_role_use_case.get_collaborators_info')
    @patch('use_cases.edit_collaborator_role_use_case.get_role_name_for_user_role')
    def test_edit_collaborator_role_unknown_collaborator_role(
        self, mock_get_role_name, mock_get_collaborators_info,
        mock_get_user_role_id_for_farm, mock_get_user_role_ids, mock_get_state
    ):
        """Test editing role when collaborator role name is unknown"""
        # Setup mocks
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm exists
            self.user_role_farm_mock,  # User role farm
            self.collaborator_role_farm_mock  # Collaborator role farm
        ]
        mock_get_state.return_value = self.active_state_mock
        mock_get_user_role_ids.return_value = [100]
        mock_get_user_role_id_for_farm.return_value = 200
        mock_get_collaborators_info.return_value = [{
            'user_name': 'Test Collaborator',
            'user_id': 2
        }]
        mock_get_role_name.side_effect = [
            'Propietario',  # Current user role
            'Unknown'  # Collaborator role unknown
        ]
        
        # Execute
        result = edit_collaborator_role(self.edit_request, 1, self.user_mock, self.db_mock)
        
        # Assertions
        assert result.status_code == 500
        response_body = result.body.decode('utf-8')
        assert "Rol actual del colaborador no encontrado" in response_body

    @patch('use_cases.edit_collaborator_role_use_case.get_state')
    @patch('use_cases.edit_collaborator_role_use_case.get_user_role_ids')
    @patch('use_cases.edit_collaborator_role_use_case.get_user_role_id_for_farm')
    @patch('use_cases.edit_collaborator_role_use_case.get_collaborators_info')
    @patch('use_cases.edit_collaborator_role_use_case.get_role_name_for_user_role')
    @patch('use_cases.edit_collaborator_role_use_case.get_role_name_by_id')
    def test_edit_collaborator_role_invalid_role_name(
        self, mock_get_role_name_by_id, mock_get_role_name, mock_get_collaborators_info,
        mock_get_user_role_id_for_farm, mock_get_user_role_ids, mock_get_state
    ):
        """Test editing role with invalid role name (not in allowed roles)"""
        # Setup mocks
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm exists
            self.user_role_farm_mock,  # User role farm
            self.collaborator_role_farm_mock  # Collaborator role farm
        ]
        mock_get_state.return_value = self.active_state_mock
        mock_get_user_role_ids.return_value = [100]
        mock_get_user_role_id_for_farm.return_value = 200
        mock_get_collaborators_info.return_value = [{
            'user_name': 'Test Collaborator',
            'user_id': 2
        }]
        mock_get_role_name.side_effect = [
            'Propietario',  # Current user role
            'Operador de campo'  # Collaborator current role
        ]
        mock_get_role_name_by_id.return_value = 'Invalid Role'  # Not in allowed roles
        
        # Execute
        result = edit_collaborator_role(self.edit_request, 1, self.user_mock, self.db_mock)
        
        # Assertions
        assert result.status_code == 400
        response_body = result.body.decode('utf-8')
        assert "Rol deseado no válido" in response_body

    @patch('use_cases.edit_collaborator_role_use_case.get_state')
    @patch('use_cases.edit_collaborator_role_use_case.get_user_role_ids')
    @patch('use_cases.edit_collaborator_role_use_case.get_user_role_id_for_farm')
    @patch('use_cases.edit_collaborator_role_use_case.get_collaborators_info')
    @patch('use_cases.edit_collaborator_role_use_case.get_role_name_for_user_role')
    @patch('use_cases.edit_collaborator_role_use_case.get_role_name_by_id')
    @patch('use_cases.edit_collaborator_role_use_case.get_role_permissions_for_user_role')
    def test_edit_collaborator_role_collaborator_not_in_farm(
        self, mock_get_permissions, mock_get_role_name_by_id, mock_get_role_name,
        mock_get_collaborators_info, mock_get_user_role_id_for_farm, mock_get_user_role_ids, mock_get_state
    ):
        """Test editing role when collaborator is not associated with the farm"""
        # Setup mocks
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm exists
            self.user_role_farm_mock,  # User role farm
            None  # Collaborator not in farm
        ]
        mock_get_state.return_value = self.active_state_mock
        mock_get_user_role_ids.return_value = [100]
        mock_get_user_role_id_for_farm.return_value = 200
        mock_get_collaborators_info.return_value = [{
            'user_name': 'Test Collaborator',
            'user_id': 2
        }]
        mock_get_role_name.side_effect = [
            'Propietario',  # Current user role
            'Operador de campo'  # Collaborator current role
        ]
        mock_get_role_name_by_id.return_value = 'Administrador de finca'
        mock_get_permissions.return_value = ['edit_administrator_farm']
        
        # Execute
        result = edit_collaborator_role(self.edit_request, 1, self.user_mock, self.db_mock)
        
        # Assertions
        assert result.status_code == 404
        response_body = result.body.decode('utf-8')
        assert "El colaborador no está asociado a esta finca" in response_body

    def test_edit_collaborator_role_request_validation(self):
        """Test request validation"""
        # Test with valid request
        valid_request = EditCollaboratorRoleRequest(collaborator_id=1, new_role_id=2)
        assert valid_request.collaborator_id == 1
        assert valid_request.new_role_id == 2
        
        # Test with invalid data types should raise validation error
        with pytest.raises((ValueError, TypeError)):
            EditCollaboratorRoleRequest(collaborator_id="invalid", new_role_id=2)
        
        with pytest.raises((ValueError, TypeError)):
            EditCollaboratorRoleRequest(collaborator_id=1, new_role_id="invalid") 