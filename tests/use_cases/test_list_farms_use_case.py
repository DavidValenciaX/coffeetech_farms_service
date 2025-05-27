"""
Pruebas unitarias para list_farms_use_case.py
"""
import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from fastapi import HTTPException

from use_cases.list_farms_use_case import list_farms
from utils.response import create_response


class TestListFarmsUseCase:
    """Clase de pruebas para el caso de uso de listado de fincas"""
    
    def setup_method(self):
        """Configuración inicial para cada prueba"""
        self.db_mock = Mock(spec=Session)
        self.user_mock = Mock()
        self.user_mock.user_id = "test_user_id"
        
        # Mock para list_farm_response
        self.list_farm_response_mock = Mock()
        self.list_farm_response_mock.return_value = {
            "farm_id": 1,
            "name": "Test Farm",
            "area": 10.5,
            "area_unit_id": 1,
            "area_unit": "hectáreas",
            "farm_state_id": 1,
            "farm_state": "Activo",
            "user_role_id": 1,
            "role": "Propietario"
        }
        
        # Mock states
        self.active_farm_state_mock = Mock()
        self.active_farm_state_mock.farm_state_id = 1
        
        self.active_urf_state_mock = Mock()
        self.active_urf_state_mock.user_role_farm_state_id = 1

    @patch('use_cases.list_farms_use_case.get_state')
    @patch('use_cases.list_farms_use_case.get_user_role_ids')
    @patch('use_cases.list_farms_use_case.get_role_name_for_user_role')
    @patch('use_cases.list_farms_use_case.create_response')
    def test_list_farms_success(self, mock_create_response, mock_get_role_name, 
                               mock_get_user_role_ids, mock_get_state):
        """Prueba el listado exitoso de fincas"""
        # Arrange
        mock_get_state.side_effect = [self.active_farm_state_mock, self.active_urf_state_mock]
        mock_get_user_role_ids.return_value = [1, 2]
        mock_get_role_name.return_value = "Propietario"
        
        # Mock farm data
        farm_mock = Mock()
        farm_mock.farm_id = 1
        farm_mock.name = "Test Farm"
        farm_mock.area = 10.5
        farm_mock.area_unit_id = 1
        farm_mock.farm_state_id = 1
        
        area_unit_mock = Mock()
        area_unit_mock.name = "hectáreas"
        
        farm_state_mock = Mock()
        farm_state_mock.name = "Activo"
        
        user_role_farm_mock = Mock()
        user_role_farm_mock.user_role_id = 1
        
        # Mock database query
        self.db_mock.query.return_value.select_from.return_value.join.return_value.join.return_value.join.return_value.filter.return_value.all.return_value = [
            (farm_mock, area_unit_mock, farm_state_mock, user_role_farm_mock)
        ]
        
        expected_response = create_response("success", "Lista de fincas obtenida exitosamente", {"farms": [self.list_farm_response_mock.return_value]})
        mock_create_response.return_value = expected_response
        
        # Act
        result = list_farms(self.user_mock, self.db_mock, self.list_farm_response_mock)
        
        # Assert
        mock_get_state.assert_any_call(self.db_mock, "Activo", "Farms")
        mock_get_state.assert_any_call(self.db_mock, "Activo", "user_role_farm")
        mock_get_user_role_ids.assert_called_once_with(self.user_mock.user_id)
        mock_get_role_name.assert_called_once_with(1)
        self.list_farm_response_mock.assert_called_once()
        mock_create_response.assert_called_once_with("success", "Lista de fincas obtenida exitosamente", {"farms": [self.list_farm_response_mock.return_value]})
        assert result == expected_response

    @patch('use_cases.list_farms_use_case.get_state')
    @patch('use_cases.list_farms_use_case.get_user_role_ids')
    @patch('use_cases.list_farms_use_case.create_response')
    def test_list_farms_empty_list(self, mock_create_response, mock_get_user_role_ids, mock_get_state):
        """Prueba el caso cuando no hay fincas asociadas al usuario"""
        # Arrange
        mock_get_state.side_effect = [self.active_farm_state_mock, self.active_urf_state_mock]
        mock_get_user_role_ids.return_value = [1, 2]
        
        # Mock empty database query result
        self.db_mock.query.return_value.select_from.return_value.join.return_value.join.return_value.join.return_value.filter.return_value.all.return_value = []
        
        expected_response = create_response("success", "Lista de fincas obtenida exitosamente", {"farms": []})
        mock_create_response.return_value = expected_response
        
        # Act
        result = list_farms(self.user_mock, self.db_mock, self.list_farm_response_mock)
        
        # Assert
        mock_create_response.assert_called_once_with("success", "Lista de fincas obtenida exitosamente", {"farms": []})
        assert result == expected_response

    @patch('use_cases.list_farms_use_case.get_state')
    @patch('use_cases.list_farms_use_case.get_user_role_ids')
    @patch('use_cases.list_farms_use_case.create_response')
    def test_list_farms_no_user_roles(self, mock_create_response, mock_get_user_role_ids, mock_get_state):
        """Prueba el caso cuando el usuario no tiene roles asociados"""
        # Arrange
        mock_get_state.side_effect = [self.active_farm_state_mock, self.active_urf_state_mock]
        mock_get_user_role_ids.return_value = []
        
        expected_response = create_response("success", "No se encontraron fincas asociadas al usuario", {"farms": []})
        mock_create_response.return_value = expected_response
        
        # Act
        result = list_farms(self.user_mock, self.db_mock, self.list_farm_response_mock)
        
        # Assert
        mock_get_user_role_ids.assert_called_once_with(self.user_mock.user_id)
        mock_create_response.assert_called_once_with("success", "No se encontraron fincas asociadas al usuario", {"farms": []})
        assert result == expected_response

    @patch('use_cases.list_farms_use_case.get_state')
    @patch('use_cases.list_farms_use_case.get_user_role_ids')
    @patch('use_cases.list_farms_use_case.create_response')
    def test_list_farms_user_service_error(self, mock_create_response, mock_get_user_role_ids, mock_get_state):
        """Prueba el manejo de errores del servicio de usuarios"""
        # Arrange
        mock_get_state.side_effect = [self.active_farm_state_mock, self.active_urf_state_mock]
        mock_get_user_role_ids.side_effect = Exception("User service error")
        
        expected_response = create_response("error", "Error al obtener información de roles del usuario: User service error", status_code=500)
        mock_create_response.return_value = expected_response
        
        # Act
        result = list_farms(self.user_mock, self.db_mock, self.list_farm_response_mock)
        
        # Assert
        mock_get_user_role_ids.assert_called_once_with(self.user_mock.user_id)
        mock_create_response.assert_called_once_with("error", "Error al obtener información de roles del usuario: User service error", status_code=500)
        assert result == expected_response

    @patch('use_cases.list_farms_use_case.get_state')
    @patch('use_cases.list_farms_use_case.get_user_role_ids')
    def test_list_farms_database_error(self, mock_get_user_role_ids, mock_get_state):
        """Prueba el manejo de errores de base de datos"""
        # Arrange
        mock_get_state.side_effect = [self.active_farm_state_mock, self.active_urf_state_mock]
        mock_get_user_role_ids.return_value = [1, 2]
        
        # Mock database error
        self.db_mock.query.side_effect = Exception("Database connection error")
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            list_farms(self.user_mock, self.db_mock, self.list_farm_response_mock)
        
        assert exc_info.value.status_code == 500
        assert "Error al obtener la lista de fincas: Database connection error" in str(exc_info.value.detail)

    @patch('use_cases.list_farms_use_case.get_state')
    @patch('use_cases.list_farms_use_case.create_response')
    def test_list_farms_missing_active_farm_state(self, mock_create_response, mock_get_state):
        """Prueba el caso cuando no se encuentra el estado 'Activo' para Farms"""
        # Arrange
        mock_get_state.return_value = None  # No active farm state found
        
        expected_response = create_response("error", "Estado 'Activo' no encontrado para Farms", status_code=400)
        mock_create_response.return_value = expected_response
        
        # Act
        result = list_farms(self.user_mock, self.db_mock, self.list_farm_response_mock)
        
        # Assert
        mock_get_state.assert_called_once_with(self.db_mock, "Activo", "Farms")
        mock_create_response.assert_called_once_with("error", "Estado 'Activo' no encontrado para Farms", status_code=400)
        assert result == expected_response

    @patch('use_cases.list_farms_use_case.get_state')
    @patch('use_cases.list_farms_use_case.create_response')
    def test_list_farms_missing_active_urf_state(self, mock_create_response, mock_get_state):
        """Prueba el caso cuando no se encuentra el estado 'Activo' para user_role_farm"""
        # Arrange
        mock_get_state.side_effect = [self.active_farm_state_mock, None]  # Second call returns None
        
        expected_response = create_response("error", "Estado 'Activo' no encontrado para user_role_farm", status_code=400)
        mock_create_response.return_value = expected_response
        
        # Act
        result = list_farms(self.user_mock, self.db_mock, self.list_farm_response_mock)
        
        # Assert
        assert mock_get_state.call_count == 2
        mock_get_state.assert_any_call(self.db_mock, "Activo", "Farms")
        mock_get_state.assert_any_call(self.db_mock, "Activo", "user_role_farm")
        mock_create_response.assert_called_once_with("error", "Estado 'Activo' no encontrado para user_role_farm", status_code=400)
        assert result == expected_response

    @patch('use_cases.list_farms_use_case.get_state')
    @patch('use_cases.list_farms_use_case.get_user_role_ids')
    @patch('use_cases.list_farms_use_case.get_role_name_for_user_role')
    @patch('use_cases.list_farms_use_case.create_response')
    def test_list_farms_multiple_farms(self, mock_create_response, mock_get_role_name, 
                                      mock_get_user_role_ids, mock_get_state):
        """Prueba el listado con múltiples fincas"""
        # Arrange
        mock_get_state.side_effect = [self.active_farm_state_mock, self.active_urf_state_mock]
        mock_get_user_role_ids.return_value = [1, 2]
        mock_get_role_name.side_effect = ["Propietario", "Administrador"]
        
        # Mock multiple farms data
        farm1_mock = Mock()
        farm1_mock.farm_id = 1
        farm1_mock.name = "Farm 1"
        farm1_mock.area = 10.5
        farm1_mock.area_unit_id = 1
        farm1_mock.farm_state_id = 1
        
        farm2_mock = Mock()
        farm2_mock.farm_id = 2
        farm2_mock.name = "Farm 2"
        farm2_mock.area = 15.0
        farm2_mock.area_unit_id = 1
        farm2_mock.farm_state_id = 1
        
        area_unit_mock = Mock()
        area_unit_mock.name = "hectáreas"
        
        farm_state_mock = Mock()
        farm_state_mock.name = "Activo"
        
        user_role_farm1_mock = Mock()
        user_role_farm1_mock.user_role_id = 1
        
        user_role_farm2_mock = Mock()
        user_role_farm2_mock.user_role_id = 2
        
        # Mock database query with multiple results
        self.db_mock.query.return_value.select_from.return_value.join.return_value.join.return_value.join.return_value.filter.return_value.all.return_value = [
            (farm1_mock, area_unit_mock, farm_state_mock, user_role_farm1_mock),
            (farm2_mock, area_unit_mock, farm_state_mock, user_role_farm2_mock)
        ]
        
        # Mock list_farm_response to return different values for each call
        self.list_farm_response_mock.side_effect = [
            {"farm_id": 1, "name": "Farm 1", "role": "Propietario"},
            {"farm_id": 2, "name": "Farm 2", "role": "Administrador"}
        ]
        
        expected_response = create_response("success", "Lista de fincas obtenida exitosamente", {
            "farms": [
                {"farm_id": 1, "name": "Farm 1", "role": "Propietario"},
                {"farm_id": 2, "name": "Farm 2", "role": "Administrador"}
            ]
        })
        mock_create_response.return_value = expected_response
        
        # Act
        result = list_farms(self.user_mock, self.db_mock, self.list_farm_response_mock)
        
        # Assert
        assert self.list_farm_response_mock.call_count == 2
        mock_get_role_name.assert_any_call(1)
        mock_get_role_name.assert_any_call(2)
        assert result == expected_response

    @patch('use_cases.list_farms_use_case.get_state')
    @patch('use_cases.list_farms_use_case.get_user_role_ids')
    @patch('use_cases.list_farms_use_case.get_role_name_for_user_role')
    def test_list_farms_role_name_error(self, mock_get_role_name, mock_get_user_role_ids, mock_get_state):
        """Prueba el manejo cuando get_role_name_for_user_role falla"""
        # Arrange
        mock_get_state.side_effect = [self.active_farm_state_mock, self.active_urf_state_mock]
        mock_get_user_role_ids.return_value = [1]
        mock_get_role_name.side_effect = Exception("Role service error")
        
        # Mock farm data
        farm_mock = Mock()
        area_unit_mock = Mock()
        farm_state_mock = Mock()
        user_role_farm_mock = Mock()
        user_role_farm_mock.user_role_id = 1
        
        self.db_mock.query.return_value.select_from.return_value.join.return_value.join.return_value.join.return_value.filter.return_value.all.return_value = [
            (farm_mock, area_unit_mock, farm_state_mock, user_role_farm_mock)
        ]
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            list_farms(self.user_mock, self.db_mock, self.list_farm_response_mock)
        
        assert exc_info.value.status_code == 500
        assert "Error al obtener la lista de fincas: Role service error" in str(exc_info.value.detail) 