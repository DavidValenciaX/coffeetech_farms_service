"""
Pruebas unitarias para delete_collaborator_use_case.py
"""
import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from use_cases.delete_collaborator_use_case import delete_collaborator
from domain.schemas import DeleteCollaboratorRequest, DeleteCollaboratorResponse
from models.models import Farms, UserRoleFarm, UserRoleFarmStates
from adapters.user_client import (
    UserRoleRetrievalError,
    CollaboratorInfoError,
    UserRoleDeletionError
)


class TestDeleteCollaboratorUseCase:
    """Clase de pruebas para el caso de uso de eliminación de colaborador"""
    
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
        
        self.inactive_state_mock = Mock(spec=UserRoleFarmStates)
        self.inactive_state_mock.user_role_farm_state_id = 2
        self.inactive_state_mock.name = "Inactivo"
        
        # Mock user role farm
        self.user_role_farm_mock = Mock(spec=UserRoleFarm)
        self.user_role_farm_mock.user_role_id = 100
        self.user_role_farm_mock.farm_id = 1
        
        # Mock collaborator role farm
        self.collaborator_role_farm_mock = Mock(spec=UserRoleFarm)
        self.collaborator_role_farm_mock.user_role_id = 200
        self.collaborator_role_farm_mock.farm_id = 1
        
        # Mock delete request
        self.delete_request = DeleteCollaboratorRequest(collaborator_id=2)

    @patch('use_cases.delete_collaborator_use_case.get_state')
    @patch('use_cases.delete_collaborator_use_case.get_user_role_ids')
    @patch('use_cases.delete_collaborator_use_case.get_user_role_id_for_farm')
    @patch('use_cases.delete_collaborator_use_case.get_collaborators_info')
    @patch('use_cases.delete_collaborator_use_case.get_role_name_for_user_role')
    @patch('use_cases.delete_collaborator_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.delete_collaborator_use_case.delete_user_role')
    def test_delete_collaborator_success(
        self, mock_delete_user_role, mock_get_permissions, mock_get_role_name,
        mock_get_collaborators_info, mock_get_user_role_id_for_farm,
        mock_get_user_role_ids, mock_get_state
    ):
        """Test successful deletion of a collaborator"""
        # Setup mocks
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm exists
            self.user_role_farm_mock,  # User role farm
            self.collaborator_role_farm_mock  # Collaborator role farm
        ]
        
        mock_get_state.side_effect = [
            self.active_state_mock,  # Active state
            self.inactive_state_mock  # Inactive state
        ]
        mock_get_user_role_ids.return_value = [100]
        mock_get_user_role_id_for_farm.return_value = 200
        mock_get_collaborators_info.return_value = [{
            'user_name': 'Test Collaborator',
            'user_id': 2
        }]
        mock_get_role_name.side_effect = [
            'Propietario de finca',  # Current user role
            'Operador de campo'  # Collaborator role
        ]
        mock_get_permissions.return_value = ['delete_operator_farm']
        
        # Execute
        result = delete_collaborator(self.delete_request, 1, self.user_mock, self.db_mock)
        
        # Assertions
        assert isinstance(result, DeleteCollaboratorResponse)
        assert result.status == "success"
        assert "Test Collaborator" in result.message
        assert "Test Farm" in result.message
        
        # Verify database operations
        self.db_mock.commit.assert_called_once()
        mock_delete_user_role.assert_called_once_with(200)
        
        # Verify collaborator state was changed to inactive
        assert self.collaborator_role_farm_mock.user_role_farm_state_id == 2

    def test_delete_collaborator_invalid_farm(self):
        """Test deletion with invalid farm ID"""
        # Setup: Farm not found
        self.db_mock.query.return_value.filter.return_value.first.return_value = None
        
        # Execute
        result = delete_collaborator(self.delete_request, 999, self.user_mock, self.db_mock)
        
        # Assertions
        assert result.status_code == 404
        assert "Finca no encontrada" in str(result.body)

    @patch('use_cases.delete_collaborator_use_case.get_state')
    @patch('use_cases.delete_collaborator_use_case.get_user_role_ids')
    @patch('use_cases.delete_collaborator_use_case.get_user_role_id_for_farm')
    @patch('use_cases.delete_collaborator_use_case.get_role_name_for_user_role')
    def test_delete_collaborator_invalid_collaborator(
        self, mock_get_role_name, mock_get_user_role_id_for_farm, mock_get_user_role_ids, mock_get_state
    ):
        """Test deletion with invalid collaborator ID"""
        # Setup mocks
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm exists
            self.user_role_farm_mock  # User role farm
        ]
        mock_get_state.return_value = self.active_state_mock
        mock_get_user_role_ids.return_value = [100]
        mock_get_user_role_id_for_farm.return_value = None  # Collaborator not found
        mock_get_role_name.return_value = 'Propietario de finca'  # Mock user role
        
        # Execute
        result = delete_collaborator(self.delete_request, 1, self.user_mock, self.db_mock)
        
        # Assertions
        assert result.status_code == 404
        response_body = result.body.decode('utf-8')
        assert "Colaborador no encontrado en esta finca" in response_body

    @patch('use_cases.delete_collaborator_use_case.get_state')
    @patch('use_cases.delete_collaborator_use_case.get_user_role_ids')
    def test_delete_collaborator_no_permission(self, mock_get_user_role_ids, mock_get_state):
        """Test deletion when user has no permission to access the farm"""
        # Setup mocks
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm exists
            None  # User not associated with farm
        ]
        mock_get_state.return_value = self.active_state_mock
        mock_get_user_role_ids.return_value = [100]
        
        # Execute
        result = delete_collaborator(self.delete_request, 1, self.user_mock, self.db_mock)
        
        # Assertions
        assert result.status_code == 403
        response_body = result.body.decode('utf-8')
        assert "No estás asociado a esta finca" in response_body

    @patch('use_cases.delete_collaborator_use_case.get_state')
    @patch('use_cases.delete_collaborator_use_case.get_user_role_ids')
    @patch('use_cases.delete_collaborator_use_case.get_user_role_id_for_farm')
    @patch('use_cases.delete_collaborator_use_case.get_collaborators_info')
    @patch('use_cases.delete_collaborator_use_case.get_role_name_for_user_role')
    def test_delete_collaborator_cannot_delete_owner(
        self, mock_get_role_name, mock_get_collaborators_info,
        mock_get_user_role_id_for_farm, mock_get_user_role_ids, mock_get_state
    ):
        """Test that user cannot delete their own association with the farm"""
        # Setup mocks - same user_role_id for both user and collaborator
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm exists
            self.user_role_farm_mock,  # User role farm
            self.user_role_farm_mock  # Same as collaborator (self-deletion attempt)
        ]
        mock_get_state.return_value = self.active_state_mock
        mock_get_user_role_ids.return_value = [100]
        mock_get_user_role_id_for_farm.return_value = 100  # Same as user's role
        mock_get_collaborators_info.return_value = [{
            'user_name': 'Test User',
            'user_id': 1
        }]
        mock_get_role_name.return_value = 'Propietario de finca'
        
        # Execute
        result = delete_collaborator(self.delete_request, 1, self.user_mock, self.db_mock)
        
        # Assertions
        assert result.status_code == 403
        response_body = result.body.decode('utf-8')
        assert "No puedes eliminar tu propia asociación" in response_body

    @patch('use_cases.delete_collaborator_use_case.get_state')
    @patch('use_cases.delete_collaborator_use_case.get_user_role_ids')
    def test_delete_collaborator_user_service_error(self, mock_get_user_role_ids, mock_get_state):
        """Test deletion when user service throws an error"""
        # Setup mocks
        self.db_mock.query.return_value.filter.return_value.first.return_value = self.farm_mock
        mock_get_state.return_value = self.active_state_mock
        mock_get_user_role_ids.side_effect = UserRoleRetrievalError("Service unavailable")
        
        # Execute
        result = delete_collaborator(self.delete_request, 1, self.user_mock, self.db_mock)
        
        # Assertions
        assert result.status_code == 500
        assert "No se pudieron obtener los roles del usuario" in str(result.body)

    @patch('use_cases.delete_collaborator_use_case.get_state')
    @patch('use_cases.delete_collaborator_use_case.get_user_role_ids')
    @patch('use_cases.delete_collaborator_use_case.get_user_role_id_for_farm')
    @patch('use_cases.delete_collaborator_use_case.get_collaborators_info')
    @patch('use_cases.delete_collaborator_use_case.get_role_name_for_user_role')
    @patch('use_cases.delete_collaborator_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.delete_collaborator_use_case.delete_user_role')
    def test_delete_collaborator_database_error(
        self, mock_delete_user_role, mock_get_permissions, mock_get_role_name,
        mock_get_collaborators_info, mock_get_user_role_id_for_farm,
        mock_get_user_role_ids, mock_get_state
    ):
        """Test deletion when database operation fails"""
        # Setup mocks
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm exists
            self.user_role_farm_mock,  # User role farm
            self.collaborator_role_farm_mock  # Collaborator role farm
        ]
        mock_get_state.side_effect = [
            self.active_state_mock,  # Active state
            self.inactive_state_mock  # Inactive state
        ]
        mock_get_user_role_ids.return_value = [100]
        mock_get_user_role_id_for_farm.return_value = 200
        mock_get_collaborators_info.return_value = [{
            'user_name': 'Test Collaborator',
            'user_id': 2
        }]
        mock_get_role_name.side_effect = [
            'Propietario de finca',  # Current user role
            'Operador de campo'  # Collaborator role
        ]
        mock_get_permissions.return_value = ['delete_operator_farm']
        
        # Simulate database error
        self.db_mock.commit.side_effect = Exception("Database error")
        
        # Execute
        result = delete_collaborator(self.delete_request, 1, self.user_mock, self.db_mock)
        
        # Assertions
        assert result.status_code == 500
        response_body = result.body.decode('utf-8')
        assert "Error al eliminar el colaborador" in response_body
        self.db_mock.rollback.assert_called_once()

    @patch('use_cases.delete_collaborator_use_case.get_state')
    def test_delete_collaborator_missing_active_states(self, mock_get_state):
        """Test deletion when active state is not found"""
        # Setup mocks
        self.db_mock.query.return_value.filter.return_value.first.return_value = self.farm_mock
        mock_get_state.return_value = None  # Active state not found
        
        # Execute
        result = delete_collaborator(self.delete_request, 1, self.user_mock, self.db_mock)
        
        # Assertions
        assert result.status_code == 400
        response_body = result.body.decode('utf-8')
        assert "Estado 'Activo' no encontrado para 'user_role_farm'" in response_body

    @patch('use_cases.delete_collaborator_use_case.get_state')
    @patch('use_cases.delete_collaborator_use_case.get_user_role_ids')
    @patch('use_cases.delete_collaborator_use_case.get_user_role_id_for_farm')
    @patch('use_cases.delete_collaborator_use_case.get_collaborators_info')
    @patch('use_cases.delete_collaborator_use_case.get_role_name_for_user_role')
    @patch('use_cases.delete_collaborator_use_case.get_role_permissions_for_user_role')
    def test_delete_collaborator_insufficient_permissions(
        self, mock_get_permissions, mock_get_role_name, mock_get_collaborators_info,
        mock_get_user_role_id_for_farm, mock_get_user_role_ids, mock_get_state
    ):
        """Test deletion when user lacks required permissions"""
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
            'Administrador de finca'  # Collaborator role (requires higher permission)
        ]
        mock_get_permissions.return_value = ['some_other_permission']  # Missing required permission
        
        # Execute
        result = delete_collaborator(self.delete_request, 1, self.user_mock, self.db_mock)
        
        # Assertions
        assert result.status_code == 403
        assert "No tienes permiso para eliminar" in str(result.body)

    @patch('use_cases.delete_collaborator_use_case.get_state')
    @patch('use_cases.delete_collaborator_use_case.get_user_role_ids')
    @patch('use_cases.delete_collaborator_use_case.get_user_role_id_for_farm')
    @patch('use_cases.delete_collaborator_use_case.get_collaborators_info')
    @patch('use_cases.delete_collaborator_use_case.get_role_name_for_user_role')
    def test_delete_collaborator_collaborator_info_error(
        self, mock_get_role_name, mock_get_collaborators_info, mock_get_user_role_id_for_farm,
        mock_get_user_role_ids, mock_get_state
    ):
        """Test deletion when collaborator info cannot be retrieved"""
        # Setup mocks
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm exists
            self.user_role_farm_mock  # User role farm
        ]
        mock_get_state.return_value = self.active_state_mock
        mock_get_user_role_ids.return_value = [100]
        mock_get_user_role_id_for_farm.return_value = 200
        mock_get_collaborators_info.side_effect = CollaboratorInfoError("Service error")
        mock_get_role_name.return_value = 'Propietario de finca'  # Mock user role
        
        # Execute
        result = delete_collaborator(self.delete_request, 1, self.user_mock, self.db_mock)
        
        # Assertions
        assert result.status_code == 404
        response_body = result.body.decode('utf-8')
        assert "Colaborador no encontrado" in response_body

    @patch('use_cases.delete_collaborator_use_case.get_state')
    @patch('use_cases.delete_collaborator_use_case.get_user_role_ids')
    @patch('use_cases.delete_collaborator_use_case.get_user_role_id_for_farm')
    @patch('use_cases.delete_collaborator_use_case.get_collaborators_info')
    @patch('use_cases.delete_collaborator_use_case.get_role_name_for_user_role')
    def test_delete_collaborator_unknown_role(
        self, mock_get_role_name, mock_get_collaborators_info,
        mock_get_user_role_id_for_farm, mock_get_user_role_ids, mock_get_state
    ):
        """Test deletion when collaborator has unknown role"""
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
            'Propietario de finca',  # Current user role
            'Unknown Role'  # Unrecognized collaborator role
        ]
        
        # Execute
        result = delete_collaborator(self.delete_request, 1, self.user_mock, self.db_mock)
        
        # Assertions
        assert result.status_code == 400
        response_body = result.body.decode('utf-8')
        assert "Rol 'Unknown Role' no reconocido para eliminación" in response_body

    @patch('use_cases.delete_collaborator_use_case.get_state')
    @patch('use_cases.delete_collaborator_use_case.get_user_role_ids')
    @patch('use_cases.delete_collaborator_use_case.get_user_role_id_for_farm')
    @patch('use_cases.delete_collaborator_use_case.get_collaborators_info')
    @patch('use_cases.delete_collaborator_use_case.get_role_name_for_user_role')
    @patch('use_cases.delete_collaborator_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.delete_collaborator_use_case.delete_user_role')
    def test_delete_collaborator_inactive_collaborator(
        self, mock_delete_user_role, mock_get_permissions, mock_get_role_name,
        mock_get_collaborators_info, mock_get_user_role_id_for_farm,
        mock_get_user_role_ids, mock_get_state
    ):
        """Test deletion when collaborator is not actively associated with farm"""
        # Setup mocks
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm exists
            self.user_role_farm_mock,  # User role farm
            None  # Collaborator not actively associated
        ]
        mock_get_state.return_value = self.active_state_mock
        mock_get_user_role_ids.return_value = [100]
        mock_get_user_role_id_for_farm.return_value = 200
        mock_get_collaborators_info.return_value = [{
            'user_name': 'Test Collaborator',
            'user_id': 2
        }]
        mock_get_role_name.return_value = 'Propietario de finca'
        
        # Execute
        result = delete_collaborator(self.delete_request, 1, self.user_mock, self.db_mock)
        
        # Assertions
        assert result.status_code == 404
        response_body = result.body.decode('utf-8')
        assert "El colaborador no está asociado activamente a esta finca" in response_body

    @patch('use_cases.delete_collaborator_use_case.get_state')
    @patch('use_cases.delete_collaborator_use_case.get_user_role_ids')
    @patch('use_cases.delete_collaborator_use_case.get_user_role_id_for_farm')
    @patch('use_cases.delete_collaborator_use_case.get_collaborators_info')
    @patch('use_cases.delete_collaborator_use_case.get_role_name_for_user_role')
    @patch('use_cases.delete_collaborator_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.delete_collaborator_use_case.delete_user_role')
    def test_delete_collaborator_missing_inactive_state(
        self, mock_delete_user_role, mock_get_permissions, mock_get_role_name,
        mock_get_collaborators_info, mock_get_user_role_id_for_farm,
        mock_get_user_role_ids, mock_get_state
    ):
        """Test deletion when inactive state is not found during deletion"""
        # Setup mocks
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm exists
            self.user_role_farm_mock,  # User role farm
            self.collaborator_role_farm_mock  # Collaborator role farm
        ]
        mock_get_state.side_effect = [
            self.active_state_mock,  # Active state found
            None  # Inactive state not found
        ]
        mock_get_user_role_ids.return_value = [100]
        mock_get_user_role_id_for_farm.return_value = 200
        mock_get_collaborators_info.return_value = [{
            'user_name': 'Test Collaborator',
            'user_id': 2
        }]
        mock_get_role_name.side_effect = [
            'Propietario de finca',  # Current user role
            'Operador de campo'  # Collaborator role
        ]
        mock_get_permissions.return_value = ['delete_operator_farm']
        
        # Execute
        result = delete_collaborator(self.delete_request, 1, self.user_mock, self.db_mock)
        
        # Assertions
        assert result.status_code == 500
        response_body = result.body.decode('utf-8')
        assert "Estado 'Inactivo' no encontrado para 'user_role_farm'" in response_body

    @patch('use_cases.delete_collaborator_use_case.get_state')
    @patch('use_cases.delete_collaborator_use_case.get_user_role_ids')
    @patch('use_cases.delete_collaborator_use_case.get_user_role_id_for_farm')
    @patch('use_cases.delete_collaborator_use_case.get_collaborators_info')
    @patch('use_cases.delete_collaborator_use_case.get_role_name_for_user_role')
    def test_delete_collaborator_role_not_found(
        self, mock_get_role_name, mock_get_collaborators_info,
        mock_get_user_role_id_for_farm, mock_get_user_role_ids, mock_get_state
    ):
        """Test deletion when current user role cannot be found"""
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
        mock_get_role_name.return_value = "Unknown"  # Role not found
        
        # Execute
        result = delete_collaborator(self.delete_request, 1, self.user_mock, self.db_mock)
        
        # Assertions
        assert result.status_code == 500
        response_body = result.body.decode('utf-8')
        assert "Rol del usuario no encontrado" in response_body

    @patch('use_cases.delete_collaborator_use_case.get_state')
    @patch('use_cases.delete_collaborator_use_case.get_user_role_ids')
    @patch('use_cases.delete_collaborator_use_case.get_user_role_id_for_farm')
    @patch('use_cases.delete_collaborator_use_case.get_collaborators_info')
    @patch('use_cases.delete_collaborator_use_case.get_role_name_for_user_role')
    @patch('use_cases.delete_collaborator_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.delete_collaborator_use_case.delete_user_role')
    def test_delete_collaborator_user_service_deletion_error(
        self, mock_delete_user_role, mock_get_permissions, mock_get_role_name,
        mock_get_collaborators_info, mock_get_user_role_id_for_farm,
        mock_get_user_role_ids, mock_get_state
    ):
        """Test deletion when user service deletion fails"""
        # Setup mocks
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm exists
            self.user_role_farm_mock,  # User role farm
            self.collaborator_role_farm_mock  # Collaborator role farm
        ]
        mock_get_state.side_effect = [
            self.active_state_mock,  # Active state
            self.inactive_state_mock  # Inactive state
        ]
        mock_get_user_role_ids.return_value = [100]
        mock_get_user_role_id_for_farm.return_value = 200
        mock_get_collaborators_info.return_value = [{
            'user_name': 'Test Collaborator',
            'user_id': 2
        }]
        mock_get_role_name.side_effect = [
            'Propietario de finca',  # Current user role
            'Operador de campo'  # Collaborator role
        ]
        mock_get_permissions.return_value = ['delete_operator_farm']
        mock_delete_user_role.side_effect = UserRoleDeletionError("Deletion failed")
        
        # Execute
        result = delete_collaborator(self.delete_request, 1, self.user_mock, self.db_mock)
        
        # Assertions
        assert result.status_code == 500
        assert "Error al eliminar el colaborador" in str(result.body)
        self.db_mock.rollback.assert_called_once()

    def test_delete_collaborator_request_validation(self):
        """Test validation of delete collaborator request"""
        # Test with invalid collaborator_id
        invalid_request = DeleteCollaboratorRequest(collaborator_id=-1)
        
        with pytest.raises(ValueError, match="debe ser un entero positivo"):
            invalid_request.validate_input()
        
        # Test with valid collaborator_id
        valid_request = DeleteCollaboratorRequest(collaborator_id=1)
        # Should not raise any exception
        valid_request.validate_input() 