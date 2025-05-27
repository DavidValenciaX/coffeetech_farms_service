"""
Pruebas unitarias para list_collaborators_use_case.py
"""
import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from use_cases.list_collaborators_use_case import list_collaborators
from domain.schemas import ListCollaboratorsResponse, CollaboratorInfo
from models.models import Farms, UserRoleFarm
from adapters.user_client import UserRoleRetrievalError, CollaboratorInfoError


class TestListCollaboratorsUseCase:
    """Clase de pruebas para el caso de uso de listado de colaboradores"""
    
    def setup_method(self):
        """Configuración inicial para cada prueba"""
        self.db_mock = Mock(spec=Session)
        self.user_mock = Mock()
        self.user_mock.user_id = "test_user_id"
        self.farm_id = 1
        
        # Mock farm object
        self.farm_mock = Mock()
        self.farm_mock.farm_id = self.farm_id
        self.farm_mock.name = "Test Farm"
        
        # Mock state object
        self.active_state_mock = Mock()
        self.active_state_mock.user_role_farm_state_id = 1
        
        # Mock user role farm object
        self.user_role_farm_mock = Mock()
        self.user_role_farm_mock.user_role_id = 123
        self.user_role_farm_mock.farm_id = self.farm_id
        
    @patch('use_cases.list_collaborators_use_case.get_state')
    @patch('use_cases.list_collaborators_use_case.get_user_role_ids')
    @patch('use_cases.list_collaborators_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.list_collaborators_use_case.get_collaborators_info')
    def test_list_collaborators_success(self, mock_get_collaborators_info, mock_get_permissions, 
                                      mock_get_user_role_ids, mock_get_state):
        """Prueba el caso exitoso de listado de colaboradores"""
        # Arrange
        self.db_mock.query.return_value.filter.return_value.first.return_value = self.farm_mock
        mock_get_state.return_value = self.active_state_mock
        mock_get_user_role_ids.return_value = [123]
        
        # Mock user role farm query for permission check
        self.db_mock.query.return_value.filter.return_value.first.return_value = self.user_role_farm_mock
        mock_get_permissions.return_value = ["read_collaborators"]
        
        # Mock user role farms query for getting all collaborators
        user_role_farm_1 = Mock()
        user_role_farm_1.user_role_id = 123
        user_role_farm_2 = Mock()
        user_role_farm_2.user_role_id = 456
        self.db_mock.query.return_value.filter.return_value.all.return_value = [user_role_farm_1, user_role_farm_2]
        
        # Mock collaborators info
        collaborators_data = [
            {
                "user_role_id": 123,
                "user_id": 1,
                "user_name": "John Doe",
                "user_email": "john@example.com",
                "role_id": 1,
                "role_name": "Admin"
            },
            {
                "user_role_id": 456,
                "user_id": 2,
                "user_name": "Jane Smith",
                "user_email": "jane@example.com",
                "role_id": 2,
                "role_name": "Worker"
            }
        ]
        mock_get_collaborators_info.return_value = collaborators_data
        
        # Act
        result = list_collaborators(self.farm_id, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status == "success"
        assert result.message == "Colaboradores obtenidos exitosamente"
        assert len(result.collaborators) == 2
        assert result.collaborators[0].user_name == "John Doe"
        assert result.collaborators[1].user_name == "Jane Smith"
        
        # Verify calls
        mock_get_user_role_ids.assert_called_once_with(self.user_mock.user_id)
        mock_get_permissions.assert_called_once_with(123)
        mock_get_collaborators_info.assert_called_once_with([123, 456])

    @patch('use_cases.list_collaborators_use_case.get_state')
    @patch('use_cases.list_collaborators_use_case.get_user_role_ids')
    @patch('use_cases.list_collaborators_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.list_collaborators_use_case.get_collaborators_info')
    def test_list_collaborators_empty_list(self, mock_get_collaborators_info, mock_get_permissions,
                                         mock_get_user_role_ids, mock_get_state):
        """Prueba el caso cuando no hay colaboradores en la finca"""
        # Arrange
        self.db_mock.query.return_value.filter.return_value.first.return_value = self.farm_mock
        mock_get_state.return_value = self.active_state_mock
        mock_get_user_role_ids.return_value = [123]
        
        # Mock user role farm query for permission check
        self.db_mock.query.return_value.filter.return_value.first.return_value = self.user_role_farm_mock
        mock_get_permissions.return_value = ["read_collaborators"]
        
        # Mock empty user role farms query
        self.db_mock.query.return_value.filter.return_value.all.return_value = []
        mock_get_collaborators_info.return_value = []
        
        # Act
        result = list_collaborators(self.farm_id, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status == "success"
        assert result.message == "Colaboradores obtenidos exitosamente"
        assert len(result.collaborators) == 0
        
        # Verify calls
        mock_get_collaborators_info.assert_called_once_with([])

    def test_list_collaborators_farm_not_found(self):
        """Prueba el caso cuando la finca no existe"""
        # Arrange
        self.db_mock.query.return_value.filter.return_value.first.return_value = None
        
        # Act
        result = list_collaborators(self.farm_id, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status == "error"
        assert result.message == "Finca no encontrada"
        assert len(result.collaborators) == 0

    @patch('use_cases.list_collaborators_use_case.get_state')
    def test_list_collaborators_active_state_not_found(self, mock_get_state):
        """Prueba el caso cuando no se encuentra el estado 'Activo'"""
        # Arrange
        self.db_mock.query.return_value.filter.return_value.first.return_value = self.farm_mock
        mock_get_state.return_value = None
        
        # Act
        result = list_collaborators(self.farm_id, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status == "error"
        assert result.message == "Estado 'Activo' no encontrado para 'user_role_farm'"
        assert len(result.collaborators) == 0

    @patch('use_cases.list_collaborators_use_case.get_state')
    @patch('use_cases.list_collaborators_use_case.get_user_role_ids')
    def test_list_collaborators_no_permission(self, mock_get_user_role_ids, mock_get_state):
        """Prueba el caso cuando el usuario no está asociado con la finca"""
        # Arrange
        mock_get_state.return_value = self.active_state_mock
        mock_get_user_role_ids.return_value = [123]
        
        # Create separate mocks for different query types
        farms_query_mock = Mock()
        farms_query_mock.filter.return_value.first.return_value = self.farm_mock
        
        user_role_farm_query_mock = Mock()
        user_role_farm_query_mock.filter.return_value.first.return_value = None  # No association
        
        # Mock db.query to return different mocks based on the model type
        def query_side_effect(model):
            if model == Farms:
                return farms_query_mock
            elif model == UserRoleFarm:
                return user_role_farm_query_mock
            return Mock()
        
        self.db_mock.query.side_effect = query_side_effect
        
        # Act
        result = list_collaborators(self.farm_id, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status == "error"
        assert result.message == "No tienes permiso para ver los colaboradores de esta finca"
        assert len(result.collaborators) == 0

    @patch('use_cases.list_collaborators_use_case.get_state')
    @patch('use_cases.list_collaborators_use_case.get_user_role_ids')
    @patch('use_cases.list_collaborators_use_case.get_role_permissions_for_user_role')
    def test_list_collaborators_insufficient_permissions(self, mock_get_permissions, 
                                                       mock_get_user_role_ids, mock_get_state):
        """Prueba el caso cuando el usuario no tiene permisos para ver colaboradores"""
        # Arrange
        self.db_mock.query.return_value.filter.return_value.first.return_value = self.farm_mock
        mock_get_state.return_value = self.active_state_mock
        mock_get_user_role_ids.return_value = [123]
        
        # Mock user role farm query for permission check
        self.db_mock.query.return_value.filter.return_value.first.return_value = self.user_role_farm_mock
        mock_get_permissions.return_value = ["other_permission"]  # No read_collaborators permission
        
        # Act
        result = list_collaborators(self.farm_id, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status == "error"
        assert result.message == "No tienes permiso para ver los colaboradores de esta finca"
        assert len(result.collaborators) == 0

    @patch('use_cases.list_collaborators_use_case.get_state')
    @patch('use_cases.list_collaborators_use_case.get_user_role_ids')
    def test_list_collaborators_user_service_error(self, mock_get_user_role_ids, mock_get_state):
        """Prueba el caso cuando hay error en el servicio de usuarios"""
        # Arrange
        self.db_mock.query.return_value.filter.return_value.first.return_value = self.farm_mock
        mock_get_state.return_value = self.active_state_mock
        mock_get_user_role_ids.side_effect = UserRoleRetrievalError("Service unavailable")
        
        # Act
        result = list_collaborators(self.farm_id, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status == "error"
        assert result.message == "No se pudieron obtener los roles del usuario"
        assert len(result.collaborators) == 0

    @patch('use_cases.list_collaborators_use_case.get_state')
    @patch('use_cases.list_collaborators_use_case.get_user_role_ids')
    @patch('use_cases.list_collaborators_use_case.get_role_permissions_for_user_role')
    def test_list_collaborators_permissions_service_error(self, mock_get_permissions,
                                                        mock_get_user_role_ids, mock_get_state):
        """Prueba el caso cuando hay error al obtener permisos del servicio de usuarios"""
        # Arrange
        self.db_mock.query.return_value.filter.return_value.first.return_value = self.farm_mock
        mock_get_state.return_value = self.active_state_mock
        mock_get_user_role_ids.return_value = [123]
        
        # Mock user role farm query for permission check
        self.db_mock.query.return_value.filter.return_value.first.return_value = self.user_role_farm_mock
        mock_get_permissions.side_effect = Exception("Service error")
        
        # Act
        result = list_collaborators(self.farm_id, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status == "error"
        assert result.message == "No se pudieron obtener los permisos del rol"
        assert len(result.collaborators) == 0

    @patch('use_cases.list_collaborators_use_case.get_state')
    @patch('use_cases.list_collaborators_use_case.get_user_role_ids')
    @patch('use_cases.list_collaborators_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.list_collaborators_use_case.get_collaborators_info')
    def test_list_collaborators_collaborators_info_error(self, mock_get_collaborators_info,
                                                       mock_get_permissions, mock_get_user_role_ids,
                                                       mock_get_state):
        """Prueba el caso cuando hay error al obtener información de colaboradores"""
        # Arrange
        self.db_mock.query.return_value.filter.return_value.first.return_value = self.farm_mock
        mock_get_state.return_value = self.active_state_mock
        mock_get_user_role_ids.return_value = [123]
        
        # Mock user role farm query for permission check
        self.db_mock.query.return_value.filter.return_value.first.return_value = self.user_role_farm_mock
        mock_get_permissions.return_value = ["read_collaborators"]
        
        # Mock user role farms query
        user_role_farm_1 = Mock()
        user_role_farm_1.user_role_id = 123
        self.db_mock.query.return_value.filter.return_value.all.return_value = [user_role_farm_1]
        
        # Mock collaborators info error
        mock_get_collaborators_info.side_effect = CollaboratorInfoError("Service error")
        
        # Act
        result = list_collaborators(self.farm_id, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status == "error"
        assert result.message == "No se pudo obtener la información de los colaboradores"
        assert len(result.collaborators) == 0

    @patch('use_cases.list_collaborators_use_case.get_state')
    def test_list_collaborators_database_error(self, mock_get_state):
        """Prueba el caso cuando hay error en la base de datos"""
        # Arrange
        self.db_mock.query.side_effect = Exception("Database connection error")
        mock_get_state.return_value = self.active_state_mock
        
        # Act & Assert
        with pytest.raises(Exception):
            list_collaborators(self.farm_id, self.user_mock, self.db_mock)

    @patch('use_cases.list_collaborators_use_case.get_state')
    @patch('use_cases.list_collaborators_use_case.get_user_role_ids')
    @patch('use_cases.list_collaborators_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.list_collaborators_use_case.get_collaborators_info')
    def test_list_collaborators_with_multiple_user_roles(self, mock_get_collaborators_info,
                                                        mock_get_permissions, mock_get_user_role_ids,
                                                        mock_get_state):
        """Prueba el caso cuando el usuario tiene múltiples roles"""
        # Arrange
        self.db_mock.query.return_value.filter.return_value.first.return_value = self.farm_mock
        mock_get_state.return_value = self.active_state_mock
        mock_get_user_role_ids.return_value = [123, 456, 789]  # Multiple roles
        
        # Mock user role farm query for permission check (first matching role)
        self.db_mock.query.return_value.filter.return_value.first.return_value = self.user_role_farm_mock
        mock_get_permissions.return_value = ["read_collaborators"]
        
        # Mock user role farms query
        user_role_farm_1 = Mock()
        user_role_farm_1.user_role_id = 123
        self.db_mock.query.return_value.filter.return_value.all.return_value = [user_role_farm_1]
        
        # Mock collaborators info
        collaborators_data = [
            {
                "user_role_id": 123,
                "user_id": 1,
                "user_name": "John Doe",
                "user_email": "john@example.com",
                "role_id": 1,
                "role_name": "Admin"
            }
        ]
        mock_get_collaborators_info.return_value = collaborators_data
        
        # Act
        result = list_collaborators(self.farm_id, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status == "success"
        assert len(result.collaborators) == 1
        
        # Verify that the query was called with all user role IDs
        mock_get_user_role_ids.assert_called_once_with(self.user_mock.user_id)

    @patch('use_cases.list_collaborators_use_case.get_state')
    @patch('use_cases.list_collaborators_use_case.get_user_role_ids')
    @patch('use_cases.list_collaborators_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.list_collaborators_use_case.get_collaborators_info')
    def test_list_collaborators_response_schema_validation(self, mock_get_collaborators_info,
                                                         mock_get_permissions, mock_get_user_role_ids,
                                                         mock_get_state):
        """Prueba que la respuesta cumple con el schema esperado"""
        # Arrange
        self.db_mock.query.return_value.filter.return_value.first.return_value = self.farm_mock
        mock_get_state.return_value = self.active_state_mock
        mock_get_user_role_ids.return_value = [123]
        
        # Mock user role farm query for permission check
        self.db_mock.query.return_value.filter.return_value.first.return_value = self.user_role_farm_mock
        mock_get_permissions.return_value = ["read_collaborators"]
        
        # Mock user role farms query
        user_role_farm_1 = Mock()
        user_role_farm_1.user_role_id = 123
        self.db_mock.query.return_value.filter.return_value.all.return_value = [user_role_farm_1]
        
        # Mock collaborators info with complete data
        collaborators_data = [
            {
                "user_role_id": 123,
                "user_id": 1,
                "user_name": "John Doe",
                "user_email": "john@example.com",
                "role_id": 1,
                "role_name": "Admin"
            }
        ]
        mock_get_collaborators_info.return_value = collaborators_data
        
        # Act
        result = list_collaborators(self.farm_id, self.user_mock, self.db_mock)
        
        # Assert
        assert isinstance(result, ListCollaboratorsResponse)
        assert isinstance(result.collaborators[0], CollaboratorInfo)
        assert result.collaborators[0].user_role_id == 123
        assert result.collaborators[0].user_id == 1
        assert result.collaborators[0].user_name == "John Doe"
        assert result.collaborators[0].user_email == "john@example.com"
        assert result.collaborators[0].role_id == 1
        assert result.collaborators[0].role_name == "Admin" 