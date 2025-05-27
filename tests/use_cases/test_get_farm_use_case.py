"""
Pruebas unitarias para get_farm_use_case.py
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session
from decimal import Decimal

from use_cases.get_farm_use_case import get_farm, FARM_NOT_FOUND_OR_NOT_BELONGS_TO_USER_ERROR
from adapters.user_client import UserRoleRetrievalError


class TestGetFarmUseCase:
    """Clase de pruebas para el caso de uso de obtener información de una finca"""
    
    def setup_method(self):
        """Configuración inicial para cada prueba"""
        self.db_mock = Mock(spec=Session)
        self.user_mock = Mock()
        self.user_mock.user_id = "test_user_id"
        
        # Mock list_farm_response function
        self.list_farm_response_mock = Mock()
        self.list_farm_response_mock.return_value = {
            "farm_id": 1,
            "name": "Test Farm",
            "area": 100.5,
            "area_unit": "Hectáreas",
            "area_unit_id": 1,
            "farm_state": "Activo",
            "farm_state_id": 1,
            "role": "Propietario",
            "user_role_id": 123
        }
        
        # Mock states
        self.active_farm_state_mock = Mock()
        self.active_farm_state_mock.farm_state_id = 1
        
        self.active_urf_state_mock = Mock()
        self.active_urf_state_mock.user_role_farm_state_id = 1
        
        # Mock entities
        self.farm_mock = Mock()
        self.farm_mock.farm_id = 1
        self.farm_mock.name = "Test Farm"
        self.farm_mock.area = Decimal('100.5')
        self.farm_mock.area_unit_id = 1
        self.farm_mock.farm_state_id = 1
        
        self.area_unit_mock = Mock()
        self.area_unit_mock.area_unit_id = 1
        self.area_unit_mock.name = "Hectáreas"
        
        self.farm_state_mock = Mock()
        self.farm_state_mock.farm_state_id = 1
        self.farm_state_mock.name = "Activo"
        
        self.user_role_farm_mock = Mock()
        self.user_role_farm_mock.user_role_id = 123
        self.user_role_farm_mock.farm_id = 1
        self.user_role_farm_mock.user_role_farm_state_id = 1

    @patch('use_cases.get_farm_use_case.get_state')
    @patch('use_cases.get_farm_use_case.get_user_role_ids')
    @patch('use_cases.get_farm_use_case.get_role_name_for_user_role')
    @patch('use_cases.get_farm_use_case.create_response')
    def test_get_farm_success(self, mock_create_response, mock_get_role_name, 
                             mock_get_user_role_ids, mock_get_state):
        """Test successful farm retrieval"""
        # Arrange
        farm_id = 1
        
        # Mock get_state calls
        mock_get_state.side_effect = [
            self.active_farm_state_mock,  # active_farm_state
            self.active_urf_state_mock    # active_urf_state
        ]
        
        # Mock user service calls
        mock_get_user_role_ids.return_value = [123, 456]
        mock_get_role_name.return_value = "Propietario"
        
        # Mock database query
        farm_data = (self.farm_mock, self.area_unit_mock, self.farm_state_mock, self.user_role_farm_mock)
        query_mock = Mock()
        self.db_mock.query.return_value = query_mock
        query_mock.select_from.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = farm_data
        
        # Mock response creation
        expected_response = Mock()
        mock_create_response.return_value = expected_response
        
        # Act
        result = get_farm(farm_id, self.user_mock, self.db_mock, self.list_farm_response_mock)
        
        # Assert
        mock_get_state.assert_any_call(self.db_mock, "Activo", "Farms")
        mock_get_state.assert_any_call(self.db_mock, "Activo", "user_role_farm")
        mock_get_user_role_ids.assert_called_once_with(self.user_mock.user_id)
        mock_get_role_name.assert_called_once_with(123)
        
        # Verify list_farm_response was called with correct parameters
        self.list_farm_response_mock.assert_called_once_with(
            farm_id=1,
            name="Test Farm",
            area=Decimal('100.5'),
            area_unit="Hectáreas",
            area_unit_id=1,
            farm_state="Activo",
            farm_state_id=1,
            role="Propietario",
            user_role_id=123
        )
        
        mock_create_response.assert_called_once_with(
            "success", 
            "Finca obtenida exitosamente", 
            {"farm": self.list_farm_response_mock.return_value}
        )
        
        assert result == expected_response

    @patch('use_cases.get_farm_use_case.get_state')
    @patch('use_cases.get_farm_use_case.create_response')
    def test_get_farm_missing_active_farm_state(self, mock_create_response, mock_get_state):
        """Test when active farm state is not found"""
        # Arrange
        farm_id = 1
        mock_get_state.return_value = None  # No active farm state found
        
        expected_response = Mock()
        mock_create_response.return_value = expected_response
        
        # Act
        result = get_farm(farm_id, self.user_mock, self.db_mock, self.list_farm_response_mock)
        
        # Assert
        mock_get_state.assert_called_once_with(self.db_mock, "Activo", "Farms")
        mock_create_response.assert_called_once_with(
            "error", 
            "Estado 'Activo' no encontrado para Farms", 
            status_code=400
        )
        assert result == expected_response

    @patch('use_cases.get_farm_use_case.get_state')
    @patch('use_cases.get_farm_use_case.create_response')
    def test_get_farm_missing_active_urf_state(self, mock_create_response, mock_get_state):
        """Test when active user_role_farm state is not found"""
        # Arrange
        farm_id = 1
        mock_get_state.side_effect = [
            self.active_farm_state_mock,  # active_farm_state found
            None                          # active_urf_state not found
        ]
        
        expected_response = Mock()
        mock_create_response.return_value = expected_response
        
        # Act
        result = get_farm(farm_id, self.user_mock, self.db_mock, self.list_farm_response_mock)
        
        # Assert
        mock_get_state.assert_any_call(self.db_mock, "Activo", "Farms")
        mock_get_state.assert_any_call(self.db_mock, "Activo", "user_role_farm")
        mock_create_response.assert_called_once_with(
            "error", 
            "Estado 'Activo' no encontrado para user_role_farm", 
            status_code=400
        )
        assert result == expected_response

    @patch('use_cases.get_farm_use_case.get_state')
    @patch('use_cases.get_farm_use_case.get_user_role_ids')
    @patch('use_cases.get_farm_use_case.create_response')
    def test_get_farm_user_service_error(self, mock_create_response, mock_get_user_role_ids, mock_get_state):
        """Test when user service throws an error"""
        # Arrange
        farm_id = 1
        
        mock_get_state.side_effect = [
            self.active_farm_state_mock,
            self.active_urf_state_mock
        ]
        
        # Mock user service error
        mock_get_user_role_ids.side_effect = UserRoleRetrievalError("Service unavailable")
        
        expected_response = Mock()
        mock_create_response.return_value = expected_response
        
        # Act
        result = get_farm(farm_id, self.user_mock, self.db_mock, self.list_farm_response_mock)
        
        # Assert
        mock_get_user_role_ids.assert_called_once_with(self.user_mock.user_id)
        mock_create_response.assert_called_once_with(
            "error", 
            "Error al obtener información de roles del usuario: Service unavailable", 
            status_code=500
        )
        assert result == expected_response

    @patch('use_cases.get_farm_use_case.get_state')
    @patch('use_cases.get_farm_use_case.get_user_role_ids')
    @patch('use_cases.get_farm_use_case.create_response')
    def test_get_farm_no_user_roles(self, mock_create_response, mock_get_user_role_ids, mock_get_state):
        """Test when user has no roles"""
        # Arrange
        farm_id = 1
        
        mock_get_state.side_effect = [
            self.active_farm_state_mock,
            self.active_urf_state_mock
        ]
        
        mock_get_user_role_ids.return_value = []  # No roles found
        
        expected_response = Mock()
        mock_create_response.return_value = expected_response
        
        # Act
        result = get_farm(farm_id, self.user_mock, self.db_mock, self.list_farm_response_mock)
        
        # Assert
        mock_get_user_role_ids.assert_called_once_with(self.user_mock.user_id)
        mock_create_response.assert_called_once_with(
            "error", 
            FARM_NOT_FOUND_OR_NOT_BELONGS_TO_USER_ERROR
        )
        assert result == expected_response

    @patch('use_cases.get_farm_use_case.get_state')
    @patch('use_cases.get_farm_use_case.get_user_role_ids')
    @patch('use_cases.get_farm_use_case.create_response')
    def test_get_farm_not_found(self, mock_create_response, mock_get_user_role_ids, mock_get_state):
        """Test when farm is not found or doesn't belong to user"""
        # Arrange
        farm_id = 999  # Non-existent farm
        
        mock_get_state.side_effect = [
            self.active_farm_state_mock,
            self.active_urf_state_mock
        ]
        
        mock_get_user_role_ids.return_value = [123, 456]
        
        # Mock database query - no farm found
        query_mock = Mock()
        self.db_mock.query.return_value = query_mock
        query_mock.select_from.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = None  # No farm data found
        
        expected_response = Mock()
        mock_create_response.return_value = expected_response
        
        # Act
        result = get_farm(farm_id, self.user_mock, self.db_mock, self.list_farm_response_mock)
        
        # Assert
        mock_get_user_role_ids.assert_called_once_with(self.user_mock.user_id)
        mock_create_response.assert_called_once_with(
            "error", 
            FARM_NOT_FOUND_OR_NOT_BELONGS_TO_USER_ERROR
        )
        assert result == expected_response

    @patch('use_cases.get_farm_use_case.get_state')
    @patch('use_cases.get_farm_use_case.get_user_role_ids')
    @patch('use_cases.get_farm_use_case.get_role_name_for_user_role')
    @patch('use_cases.get_farm_use_case.create_response')
    def test_get_farm_user_not_associated_with_farm(self, mock_create_response, mock_get_role_name, 
                                                   mock_get_user_role_ids, mock_get_state):
        """Test when user has roles but is not associated with the specific farm"""
        # Arrange
        farm_id = 1
        
        mock_get_state.side_effect = [
            self.active_farm_state_mock,
            self.active_urf_state_mock
        ]
        
        # User has roles but not for this farm
        mock_get_user_role_ids.return_value = [789, 101]  # Different user_role_ids
        
        # Mock database query - no matching farm data
        query_mock = Mock()
        self.db_mock.query.return_value = query_mock
        query_mock.select_from.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = None  # No matching farm data
        
        expected_response = Mock()
        mock_create_response.return_value = expected_response
        
        # Act
        result = get_farm(farm_id, self.user_mock, self.db_mock, self.list_farm_response_mock)
        
        # Assert
        mock_get_user_role_ids.assert_called_once_with(self.user_mock.user_id)
        mock_create_response.assert_called_once_with(
            "error", 
            FARM_NOT_FOUND_OR_NOT_BELONGS_TO_USER_ERROR
        )
        assert result == expected_response

    @patch('use_cases.get_farm_use_case.get_state')
    @patch('use_cases.get_farm_use_case.get_user_role_ids')
    @patch('use_cases.get_farm_use_case.get_role_name_for_user_role')
    @patch('use_cases.get_farm_use_case.create_response')
    def test_get_farm_database_error(self, mock_create_response, mock_get_role_name, 
                                    mock_get_user_role_ids, mock_get_state):
        """Test when database query throws an exception"""
        # Arrange
        farm_id = 1
        
        mock_get_state.side_effect = [
            self.active_farm_state_mock,
            self.active_urf_state_mock
        ]
        
        mock_get_user_role_ids.return_value = [123]
        
        # Mock database error
        query_mock = Mock()
        self.db_mock.query.return_value = query_mock
        query_mock.select_from.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.first.side_effect = Exception("Database connection error")
        
        expected_response = Mock()
        mock_create_response.return_value = expected_response
        
        # Act
        result = get_farm(farm_id, self.user_mock, self.db_mock, self.list_farm_response_mock)
        
        # Assert
        mock_get_user_role_ids.assert_called_once_with(self.user_mock.user_id)
        mock_create_response.assert_called_once_with(
            "error", 
            "Ocurrió un error al intentar obtener la finca. Por favor, inténtalo de nuevo más tarde."
        )
        assert result == expected_response

    @patch('use_cases.get_farm_use_case.get_state')
    @patch('use_cases.get_farm_use_case.get_user_role_ids')
    @patch('use_cases.get_farm_use_case.get_role_name_for_user_role')
    @patch('use_cases.get_farm_use_case.create_response')
    def test_get_farm_role_name_service_error(self, mock_create_response, mock_get_role_name, 
                                             mock_get_user_role_ids, mock_get_state):
        """Test when role name service returns 'Unknown' due to error"""
        # Arrange
        farm_id = 1
        
        mock_get_state.side_effect = [
            self.active_farm_state_mock,
            self.active_urf_state_mock
        ]
        
        mock_get_user_role_ids.return_value = [123]
        mock_get_role_name.return_value = "Unknown"  # Service error returns Unknown
        
        # Mock database query
        farm_data = (self.farm_mock, self.area_unit_mock, self.farm_state_mock, self.user_role_farm_mock)
        query_mock = Mock()
        self.db_mock.query.return_value = query_mock
        query_mock.select_from.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = farm_data
        
        expected_response = Mock()
        mock_create_response.return_value = expected_response
        
        # Act
        result = get_farm(farm_id, self.user_mock, self.db_mock, self.list_farm_response_mock)
        
        # Assert
        mock_get_role_name.assert_called_once_with(123)
        
        # Verify list_farm_response was called with 'Unknown' role
        self.list_farm_response_mock.assert_called_once_with(
            farm_id=1,
            name="Test Farm",
            area=Decimal('100.5'),
            area_unit="Hectáreas",
            area_unit_id=1,
            farm_state="Activo",
            farm_state_id=1,
            role="Unknown",  # Should be Unknown due to service error
            user_role_id=123
        )
        
        mock_create_response.assert_called_once_with(
            "success", 
            "Finca obtenida exitosamente", 
            {"farm": self.list_farm_response_mock.return_value}
        )
        
        assert result == expected_response

    @patch('use_cases.get_farm_use_case.get_state')
    @patch('use_cases.get_farm_use_case.get_user_role_ids')
    @patch('use_cases.get_farm_use_case.get_role_name_for_user_role')
    @patch('use_cases.get_farm_use_case.create_response')
    def test_get_farm_multiple_user_roles(self, mock_create_response, mock_get_role_name, 
                                         mock_get_user_role_ids, mock_get_state):
        """Test successful farm retrieval when user has multiple roles"""
        # Arrange
        farm_id = 1
        
        mock_get_state.side_effect = [
            self.active_farm_state_mock,
            self.active_urf_state_mock
        ]
        
        # User has multiple roles
        mock_get_user_role_ids.return_value = [123, 456, 789]
        mock_get_role_name.return_value = "Colaborador"
        
        # Mock database query
        farm_data = (self.farm_mock, self.area_unit_mock, self.farm_state_mock, self.user_role_farm_mock)
        query_mock = Mock()
        self.db_mock.query.return_value = query_mock
        query_mock.select_from.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = farm_data
        
        expected_response = Mock()
        mock_create_response.return_value = expected_response
        
        # Act
        result = get_farm(farm_id, self.user_mock, self.db_mock, self.list_farm_response_mock)
        
        # Assert
        mock_get_user_role_ids.assert_called_once_with(self.user_mock.user_id)
        mock_get_role_name.assert_called_once_with(123)
        
        # Verify the query was called with all user_role_ids
        query_calls = query_mock.filter.call_args_list
        # The filter should include user_role_ids in the query
        assert len(query_calls) > 0
        
        mock_create_response.assert_called_once_with(
            "success", 
            "Finca obtenida exitosamente", 
            {"farm": self.list_farm_response_mock.return_value}
        )
        
        assert result == expected_response

    @patch('use_cases.get_farm_use_case.get_state')
    @patch('use_cases.get_farm_use_case.get_user_role_ids')
    @patch('use_cases.get_farm_use_case.get_role_name_for_user_role')
    @patch('use_cases.get_farm_use_case.create_response')
    def test_get_farm_with_decimal_area(self, mock_create_response, mock_get_role_name, 
                                       mock_get_user_role_ids, mock_get_state):
        """Test farm retrieval with decimal area values"""
        # Arrange
        farm_id = 1
        
        mock_get_state.side_effect = [
            self.active_farm_state_mock,
            self.active_urf_state_mock
        ]
        
        mock_get_user_role_ids.return_value = [123]
        mock_get_role_name.return_value = "Propietario"
        
        # Mock farm with decimal area
        farm_with_decimal = Mock()
        farm_with_decimal.farm_id = 1
        farm_with_decimal.name = "Decimal Farm"
        farm_with_decimal.area = Decimal('250.75')
        farm_with_decimal.area_unit_id = 2
        farm_with_decimal.farm_state_id = 1
        
        area_unit_decimal = Mock()
        area_unit_decimal.area_unit_id = 2
        area_unit_decimal.name = "Metros cuadrados"
        
        farm_data = (farm_with_decimal, area_unit_decimal, self.farm_state_mock, self.user_role_farm_mock)
        query_mock = Mock()
        self.db_mock.query.return_value = query_mock
        query_mock.select_from.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = farm_data
        
        expected_response = Mock()
        mock_create_response.return_value = expected_response
        
        # Act
        result = get_farm(farm_id, self.user_mock, self.db_mock, self.list_farm_response_mock)
        
        # Assert
        self.list_farm_response_mock.assert_called_once_with(
            farm_id=1,
            name="Decimal Farm",
            area=Decimal('250.75'),
            area_unit="Metros cuadrados",
            area_unit_id=2,
            farm_state="Activo",
            farm_state_id=1,
            role="Propietario",
            user_role_id=123
        )
        
        assert result == expected_response

    @patch('use_cases.get_farm_use_case.get_state')
    @patch('use_cases.get_farm_use_case.get_user_role_ids')
    @patch('use_cases.get_farm_use_case.create_response')
    def test_get_farm_generic_exception_in_user_service(self, mock_create_response, mock_get_user_role_ids, mock_get_state):
        """Test when user service throws a generic exception (not UserRoleRetrievalError)"""
        # Arrange
        farm_id = 1
        
        mock_get_state.side_effect = [
            self.active_farm_state_mock,
            self.active_urf_state_mock
        ]
        
        # Mock generic exception from user service
        mock_get_user_role_ids.side_effect = Exception("Generic service error")
        
        expected_response = Mock()
        mock_create_response.return_value = expected_response
        
        # Act
        result = get_farm(farm_id, self.user_mock, self.db_mock, self.list_farm_response_mock)
        
        # Assert
        mock_get_user_role_ids.assert_called_once_with(self.user_mock.user_id)
        mock_create_response.assert_called_once_with(
            "error", 
            "Error al obtener información de roles del usuario: Generic service error", 
            status_code=500
        )
        assert result == expected_response 