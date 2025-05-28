"""
Pruebas unitarias para update_plot_use_case.py
"""
import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from fastapi import HTTPException

from use_cases.update_plot_use_case import update_plot_general_info, update_plot_location


class TestUpdatePlotUseCase:
    """Clase de pruebas para el caso de uso de actualización de lotes"""
    
    def setup_method(self):
        """Configuración inicial para cada prueba"""
        self.db_mock = Mock(spec=Session)
        self.user_mock = Mock()
        self.user_mock.user_id = "test_user_id"
        
        # Mock objects for database entities
        self.active_plot_state = Mock()
        self.active_plot_state.plot_state_id = 1
        
        self.active_urf_state = Mock()
        self.active_urf_state.user_role_farm_state_id = 1
        
        self.plot_mock = Mock()
        self.plot_mock.plot_id = 1
        self.plot_mock.name = "Test Plot"
        self.plot_mock.farm_id = 1
        self.plot_mock.coffee_variety_id = 1
        self.plot_mock.latitude = 10.0
        self.plot_mock.longitude = -84.0
        self.plot_mock.altitude = 1500.0
        
        self.farm_mock = Mock()
        self.farm_mock.farm_id = 1
        self.farm_mock.name = "Test Farm"
        
        self.user_role_farm_mock = Mock()
        self.user_role_farm_mock.user_role_id = 1
        self.user_role_farm_mock.farm_id = 1
        
        self.coffee_variety_mock = Mock()
        self.coffee_variety_mock.coffee_variety_id = 1
        self.coffee_variety_mock.name = "Arabica"
        
        # Mock request objects
        self.general_info_request = Mock()
        self.general_info_request.plot_id = 1
        self.general_info_request.name = "Updated Plot Name"
        self.general_info_request.coffee_variety_id = 1
        
        self.location_request = Mock()
        self.location_request.plot_id = 1
        self.location_request.latitude = 11.0
        self.location_request.longitude = -85.0
        self.location_request.altitude = 1600.0

    @patch('use_cases.update_plot_use_case.get_state')
    @patch('use_cases.update_plot_use_case.get_user_role_ids')
    @patch('use_cases.update_plot_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.update_plot_use_case.create_response')
    def test_update_plot_general_info_success(self, mock_create_response, mock_get_permissions, 
                                            mock_get_user_role_ids, mock_get_state):
        """Test successful update of plot general information"""
        # Setup mocks
        mock_get_state.side_effect = [self.active_plot_state, self.active_urf_state]
        mock_get_user_role_ids.return_value = [1]
        mock_get_permissions.return_value = ["edit_plot"]
        
        # Setup database queries
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,  # plot query
            self.farm_mock,  # farm query
            self.user_role_farm_mock,  # user_role_farm query
            None,  # existing plot with same name query
            self.coffee_variety_mock  # coffee variety query
        ]
        
        mock_create_response.return_value = {"status": "success"}
        
        # Execute
        result = update_plot_general_info(self.general_info_request, self.user_mock, self.db_mock)
        
        # Verify
        assert result == {"status": "success"}
        self.db_mock.commit.assert_called_once()
        self.db_mock.refresh.assert_called_once_with(self.plot_mock)
        assert self.plot_mock.name == "Updated Plot Name"
        assert self.plot_mock.coffee_variety_id == 1

    @patch('use_cases.update_plot_use_case.get_state')
    @patch('use_cases.update_plot_use_case.create_response')
    def test_update_plot_general_info_plot_state_not_found(self, mock_create_response, mock_get_state):
        """Test when active plot state is not found"""
        mock_get_state.return_value = None
        mock_create_response.return_value = {"status": "error"}
        
        result = update_plot_general_info(self.general_info_request, self.user_mock, self.db_mock)
        
        assert result == {"status": "error"}
        mock_create_response.assert_called_with("error", "No se encontró el estado 'Activo' para el tipo 'Plots'", status_code=400)

    @patch('use_cases.update_plot_use_case.get_state')
    @patch('use_cases.update_plot_use_case.create_response')
    def test_update_plot_general_info_plot_not_found(self, mock_create_response, mock_get_state):
        """Test when plot is not found or not active"""
        mock_get_state.return_value = self.active_plot_state
        self.db_mock.query.return_value.filter.return_value.first.return_value = None
        mock_create_response.return_value = {"status": "error"}
        
        result = update_plot_general_info(self.general_info_request, self.user_mock, self.db_mock)
        
        assert result == {"status": "error"}
        mock_create_response.assert_called_with("error", "El lote no existe o no está activo")

    @patch('use_cases.update_plot_use_case.get_state')
    @patch('use_cases.update_plot_use_case.create_response')
    def test_update_plot_general_info_farm_not_found(self, mock_create_response, mock_get_state):
        """Test when farm associated with plot is not found"""
        mock_get_state.return_value = self.active_plot_state
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,  # plot found
            None  # farm not found
        ]
        mock_create_response.return_value = {"status": "error"}
        
        result = update_plot_general_info(self.general_info_request, self.user_mock, self.db_mock)
        
        assert result == {"status": "error"}
        mock_create_response.assert_called_with("error", "La finca asociada al lote no existe")

    @patch('use_cases.update_plot_use_case.get_state')
    @patch('use_cases.update_plot_use_case.get_user_role_ids')
    @patch('use_cases.update_plot_use_case.create_response')
    def test_update_plot_general_info_user_service_error(self, mock_create_response, 
                                                        mock_get_user_role_ids, mock_get_state):
        """Test when user service returns an error"""
        mock_get_state.side_effect = [self.active_plot_state, self.active_urf_state]
        mock_get_user_role_ids.side_effect = Exception("User service error")
        
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,
            self.farm_mock
        ]
        mock_create_response.return_value = {"status": "error"}
        
        result = update_plot_general_info(self.general_info_request, self.user_mock, self.db_mock)
        
        assert result == {"status": "error"}
        mock_create_response.assert_called_with("error", "No se pudieron obtener los roles del usuario", status_code=500)

    @patch('use_cases.update_plot_use_case.get_state')
    @patch('use_cases.update_plot_use_case.get_user_role_ids')
    @patch('use_cases.update_plot_use_case.create_response')
    def test_update_plot_general_info_no_permission(self, mock_create_response, 
                                                   mock_get_user_role_ids, mock_get_state):
        """Test when user has no permission to edit plot"""
        mock_get_state.side_effect = [self.active_plot_state, self.active_urf_state]
        mock_get_user_role_ids.return_value = [1]
        
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,
            self.farm_mock,
            None  # user_role_farm not found
        ]
        mock_create_response.return_value = {"status": "error"}
        
        result = update_plot_general_info(self.general_info_request, self.user_mock, self.db_mock)
        
        assert result == {"status": "error"}
        mock_create_response.assert_called_with("error", "No tienes permiso para editar un lote en esta finca")

    @patch('use_cases.update_plot_use_case.get_state')
    @patch('use_cases.update_plot_use_case.get_user_role_ids')
    @patch('use_cases.update_plot_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.update_plot_use_case.create_response')
    def test_update_plot_general_info_insufficient_permissions(self, mock_create_response, 
                                                              mock_get_permissions, mock_get_user_role_ids, 
                                                              mock_get_state):
        """Test when user role doesn't have edit_plot permission"""
        mock_get_state.side_effect = [self.active_plot_state, self.active_urf_state]
        mock_get_user_role_ids.return_value = [1]
        mock_get_permissions.return_value = ["view_plot"]  # No edit permission
        
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,
            self.farm_mock,
            self.user_role_farm_mock
        ]
        mock_create_response.return_value = {"status": "error"}
        
        result = update_plot_general_info(self.general_info_request, self.user_mock, self.db_mock)
        
        assert result == {"status": "error"}
        mock_create_response.assert_called_with("error", "No tienes permiso para editar un lote en esta finca")

    @patch('use_cases.update_plot_use_case.get_state')
    @patch('use_cases.update_plot_use_case.get_user_role_ids')
    @patch('use_cases.update_plot_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.update_plot_use_case.create_response')
    def test_update_plot_general_info_empty_name(self, mock_create_response, mock_get_permissions, 
                                                mock_get_user_role_ids, mock_get_state):
        """Test when plot name is empty or only whitespace"""
        mock_get_state.side_effect = [self.active_plot_state, self.active_urf_state]
        mock_get_user_role_ids.return_value = [1]
        mock_get_permissions.return_value = ["edit_plot"]
        
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,
            self.farm_mock,
            self.user_role_farm_mock
        ]
        
        # Test empty name
        self.general_info_request.name = ""
        mock_create_response.return_value = {"status": "error"}
        
        result = update_plot_general_info(self.general_info_request, self.user_mock, self.db_mock)
        
        assert result == {"status": "error"}
        mock_create_response.assert_called_with("error", "El nombre del lote no puede estar vacío")

    @patch('use_cases.update_plot_use_case.get_state')
    @patch('use_cases.update_plot_use_case.get_user_role_ids')
    @patch('use_cases.update_plot_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.update_plot_use_case.create_response')
    def test_update_plot_general_info_name_too_long(self, mock_create_response, mock_get_permissions, 
                                                   mock_get_user_role_ids, mock_get_state):
        """Test when plot name is too long"""
        mock_get_state.side_effect = [self.active_plot_state, self.active_urf_state]
        mock_get_user_role_ids.return_value = [1]
        mock_get_permissions.return_value = ["edit_plot"]
        
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,
            self.farm_mock,
            self.user_role_farm_mock
        ]
        
        # Test name too long (over 100 characters)
        self.general_info_request.name = "a" * 101
        mock_create_response.return_value = {"status": "error"}
        
        result = update_plot_general_info(self.general_info_request, self.user_mock, self.db_mock)
        
        assert result == {"status": "error"}
        mock_create_response.assert_called_with("error", "El nombre del lote no puede tener más de 100 caracteres")

    @patch('use_cases.update_plot_use_case.get_state')
    @patch('use_cases.update_plot_use_case.get_user_role_ids')
    @patch('use_cases.update_plot_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.update_plot_use_case.create_response')
    def test_update_plot_general_info_duplicate_name_in_farm(self, mock_create_response, mock_get_permissions, 
                                                            mock_get_user_role_ids, mock_get_state):
        """Test when another active plot with same name exists in farm"""
        mock_get_state.side_effect = [self.active_plot_state, self.active_urf_state]
        mock_get_user_role_ids.return_value = [1]
        mock_get_permissions.return_value = ["edit_plot"]
        
        existing_plot = Mock()
        existing_plot.plot_id = 2
        existing_plot.name = "Updated Plot Name"
        
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,
            self.farm_mock,
            self.user_role_farm_mock,
            existing_plot  # existing plot with same name
        ]
        
        mock_create_response.return_value = {"status": "error"}
        
        result = update_plot_general_info(self.general_info_request, self.user_mock, self.db_mock)
        
        assert result == {"status": "error"}
        mock_create_response.assert_called_with("error", "Ya existe un lote activo con el nombre 'Updated Plot Name' en esta finca")

    @patch('use_cases.update_plot_use_case.get_state')
    @patch('use_cases.update_plot_use_case.get_user_role_ids')
    @patch('use_cases.update_plot_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.update_plot_use_case.create_response')
    def test_update_plot_general_info_invalid_coffee_variety(self, mock_create_response, mock_get_permissions, 
                                                            mock_get_user_role_ids, mock_get_state):
        """Test when coffee variety doesn't exist"""
        mock_get_state.side_effect = [self.active_plot_state, self.active_urf_state]
        mock_get_user_role_ids.return_value = [1]
        mock_get_permissions.return_value = ["edit_plot"]
        
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,
            self.farm_mock,
            self.user_role_farm_mock,
            None,  # no existing plot with same name
            None   # coffee variety not found
        ]
        
        mock_create_response.return_value = {"status": "error"}
        
        result = update_plot_general_info(self.general_info_request, self.user_mock, self.db_mock)
        
        assert result == {"status": "error"}
        mock_create_response.assert_called_with("error", "La variedad de café con ID 1 no existe", status_code=400)

    @patch('use_cases.update_plot_use_case.get_state')
    @patch('use_cases.update_plot_use_case.get_user_role_ids')
    @patch('use_cases.update_plot_use_case.get_role_permissions_for_user_role')
    def test_update_plot_general_info_database_error(self, mock_get_permissions, 
                                                    mock_get_user_role_ids, mock_get_state):
        """Test when database commit fails"""
        mock_get_state.side_effect = [self.active_plot_state, self.active_urf_state]
        mock_get_user_role_ids.return_value = [1]
        mock_get_permissions.return_value = ["edit_plot"]
        
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,
            self.farm_mock,
            self.user_role_farm_mock,
            None,  # no existing plot with same name
            self.coffee_variety_mock
        ]
        
        # Simulate database error on commit
        self.db_mock.commit.side_effect = Exception("Database error")
        
        with pytest.raises(HTTPException) as exc_info:
            update_plot_general_info(self.general_info_request, self.user_mock, self.db_mock)
        
        assert exc_info.value.status_code == 500
        assert "Error al actualizar el lote" in str(exc_info.value.detail)
        self.db_mock.rollback.assert_called_once()

    # Tests for update_plot_location

    @patch('use_cases.update_plot_use_case.get_state')
    @patch('use_cases.update_plot_use_case.get_user_role_ids')
    @patch('use_cases.update_plot_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.update_plot_use_case.create_response')
    def test_update_plot_location_success(self, mock_create_response, mock_get_permissions, 
                                        mock_get_user_role_ids, mock_get_state):
        """Test successful update of plot location"""
        mock_get_state.side_effect = [self.active_plot_state, self.active_urf_state]
        mock_get_user_role_ids.return_value = [1]
        mock_get_permissions.return_value = ["edit_plot"]
        
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,
            self.farm_mock,
            self.user_role_farm_mock
        ]
        
        mock_create_response.return_value = {"status": "success"}
        
        result = update_plot_location(self.location_request, self.user_mock, self.db_mock)
        
        assert result == {"status": "success"}
        self.db_mock.commit.assert_called_once()
        self.db_mock.refresh.assert_called_once_with(self.plot_mock)
        assert self.plot_mock.latitude == pytest.approx(11.0)
        assert self.plot_mock.longitude == pytest.approx(-85.0)
        assert self.plot_mock.altitude == pytest.approx(1600.0)

    @patch('use_cases.update_plot_use_case.get_state')
    @patch('use_cases.update_plot_use_case.create_response')
    def test_update_plot_location_plot_state_not_found(self, mock_create_response, mock_get_state):
        """Test when active plot state is not found for location update"""
        mock_get_state.return_value = None
        mock_create_response.return_value = {"status": "error"}
        
        result = update_plot_location(self.location_request, self.user_mock, self.db_mock)
        
        assert result == {"status": "error"}
        mock_create_response.assert_called_with("error", "No se encontró el estado 'Activo' para el tipo 'Plots'", status_code=400)

    @patch('use_cases.update_plot_use_case.get_state')
    @patch('use_cases.update_plot_use_case.create_response')
    def test_update_plot_location_plot_not_found(self, mock_create_response, mock_get_state):
        """Test when plot is not found for location update"""
        mock_get_state.return_value = self.active_plot_state
        self.db_mock.query.return_value.filter.return_value.first.return_value = None
        mock_create_response.return_value = {"status": "error"}
        
        result = update_plot_location(self.location_request, self.user_mock, self.db_mock)
        
        assert result == {"status": "error"}
        mock_create_response.assert_called_with("error", "El lote no existe o no está activo")

    @patch('use_cases.update_plot_use_case.get_state')
    @patch('use_cases.update_plot_use_case.get_user_role_ids')
    @patch('use_cases.update_plot_use_case.get_role_permissions_for_user_role')
    def test_update_plot_location_database_error(self, mock_get_permissions, 
                                                mock_get_user_role_ids, mock_get_state):
        """Test when database commit fails during location update"""
        mock_get_state.side_effect = [self.active_plot_state, self.active_urf_state]
        mock_get_user_role_ids.return_value = [1]
        mock_get_permissions.return_value = ["edit_plot"]
        
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,
            self.farm_mock,
            self.user_role_farm_mock
        ]
        
        # Simulate database error on commit
        self.db_mock.commit.side_effect = Exception("Database error")
        
        with pytest.raises(HTTPException) as exc_info:
            update_plot_location(self.location_request, self.user_mock, self.db_mock)
        
        assert exc_info.value.status_code == 500
        assert "Error al actualizar la ubicación del lote" in str(exc_info.value.detail)
        self.db_mock.rollback.assert_called_once()

    @patch('use_cases.update_plot_use_case.get_state')
    @patch('use_cases.update_plot_use_case.get_user_role_ids')
    @patch('use_cases.update_plot_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.update_plot_use_case.create_response')
    def test_update_plot_location_permission_service_error(self, mock_create_response, mock_get_permissions, 
                                                          mock_get_user_role_ids, mock_get_state):
        """Test when permission service returns an error during location update"""
        mock_get_state.side_effect = [self.active_plot_state, self.active_urf_state]
        mock_get_user_role_ids.return_value = [1]
        mock_get_permissions.side_effect = Exception("Permission service error")
        
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,
            self.farm_mock,
            self.user_role_farm_mock
        ]
        
        mock_create_response.return_value = {"status": "error"}
        
        result = update_plot_location(self.location_request, self.user_mock, self.db_mock)
        
        assert result == {"status": "error"}
        mock_create_response.assert_called_with("error", "No se pudieron obtener los permisos del rol", status_code=500)

    def test_setup_method_initialization(self):
        """Test that setup_method properly initializes all mock objects"""
        assert self.db_mock is not None
        assert self.user_mock.user_id == "test_user_id"
        assert self.active_plot_state.plot_state_id == 1
        assert self.active_urf_state.user_role_farm_state_id == 1
        assert self.plot_mock.plot_id == 1
        assert self.farm_mock.farm_id == 1
        assert self.user_role_farm_mock.user_role_id == 1
        assert self.coffee_variety_mock.coffee_variety_id == 1
        assert self.general_info_request.plot_id == 1
        assert self.location_request.plot_id == 1

    # Additional edge case tests

    @patch('use_cases.update_plot_use_case.get_state')
    @patch('use_cases.update_plot_use_case.get_user_role_ids')
    @patch('use_cases.update_plot_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.update_plot_use_case.create_response')
    def test_update_plot_general_info_whitespace_only_name(self, mock_create_response, mock_get_permissions, 
                                                          mock_get_user_role_ids, mock_get_state):
        """Test when plot name contains only whitespace"""
        mock_get_state.side_effect = [self.active_plot_state, self.active_urf_state]
        mock_get_user_role_ids.return_value = [1]
        mock_get_permissions.return_value = ["edit_plot"]
        
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,
            self.farm_mock,
            self.user_role_farm_mock
        ]
        
        # Test whitespace only name
        self.general_info_request.name = "   "
        mock_create_response.return_value = {"status": "error"}
        
        result = update_plot_general_info(self.general_info_request, self.user_mock, self.db_mock)
        
        assert result == {"status": "error"}
        mock_create_response.assert_called_with("error", "El nombre del lote no puede estar vacío")

    @patch('use_cases.update_plot_use_case.get_state')
    @patch('use_cases.update_plot_use_case.create_response')
    def test_update_plot_general_info_user_role_farm_state_not_found(self, mock_create_response, mock_get_state):
        """Test when user_role_farm active state is not found"""
        mock_get_state.side_effect = [self.active_plot_state, None]  # Second call returns None
        
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,
            self.farm_mock
        ]
        mock_create_response.return_value = {"status": "error"}
        
        result = update_plot_general_info(self.general_info_request, self.user_mock, self.db_mock)
        
        assert result == {"status": "error"}
        mock_create_response.assert_called_with("error", "No se encontró el estado 'Activo' para el tipo 'user_role_farm'", status_code=400)

    @patch('use_cases.update_plot_use_case.get_state')
    @patch('use_cases.update_plot_use_case.get_user_role_ids')
    @patch('use_cases.update_plot_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.update_plot_use_case.create_response')
    def test_update_plot_general_info_permission_service_error(self, mock_create_response, mock_get_permissions, 
                                                              mock_get_user_role_ids, mock_get_state):
        """Test when permission service returns an error"""
        mock_get_state.side_effect = [self.active_plot_state, self.active_urf_state]
        mock_get_user_role_ids.return_value = [1]
        mock_get_permissions.side_effect = Exception("Permission service error")
        
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,
            self.farm_mock,
            self.user_role_farm_mock
        ]
        
        mock_create_response.return_value = {"status": "error"}
        
        result = update_plot_general_info(self.general_info_request, self.user_mock, self.db_mock)
        
        assert result == {"status": "error"}
        mock_create_response.assert_called_with("error", "No se pudieron obtener los permisos del rol", status_code=500)

    @patch('use_cases.update_plot_use_case.get_state')
    @patch('use_cases.update_plot_use_case.create_response')
    def test_update_plot_location_farm_not_found(self, mock_create_response, mock_get_state):
        """Test when farm associated with plot is not found during location update"""
        mock_get_state.return_value = self.active_plot_state
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,  # plot found
            None  # farm not found
        ]
        mock_create_response.return_value = {"status": "error"}
        
        result = update_plot_location(self.location_request, self.user_mock, self.db_mock)
        
        assert result == {"status": "error"}
        mock_create_response.assert_called_with("error", "La finca asociada al lote no existe")

    @patch('use_cases.update_plot_use_case.get_state')
    @patch('use_cases.update_plot_use_case.get_user_role_ids')
    @patch('use_cases.update_plot_use_case.create_response')
    def test_update_plot_location_user_service_error(self, mock_create_response, 
                                                    mock_get_user_role_ids, mock_get_state):
        """Test when user service returns an error during location update"""
        mock_get_state.side_effect = [self.active_plot_state, self.active_urf_state]
        mock_get_user_role_ids.side_effect = Exception("User service error")
        
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,
            self.farm_mock
        ]
        mock_create_response.return_value = {"status": "error"}
        
        result = update_plot_location(self.location_request, self.user_mock, self.db_mock)
        
        assert result == {"status": "error"}
        mock_create_response.assert_called_with("error", "No se pudieron obtener los roles del usuario", status_code=500)

    @patch('use_cases.update_plot_use_case.get_state')
    @patch('use_cases.update_plot_use_case.get_user_role_ids')
    @patch('use_cases.update_plot_use_case.create_response')
    def test_update_plot_location_no_permission(self, mock_create_response, 
                                               mock_get_user_role_ids, mock_get_state):
        """Test when user has no permission to edit plot location"""
        mock_get_state.side_effect = [self.active_plot_state, self.active_urf_state]
        mock_get_user_role_ids.return_value = [1]
        
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,
            self.farm_mock,
            None  # user_role_farm not found
        ]
        mock_create_response.return_value = {"status": "error"}
        
        result = update_plot_location(self.location_request, self.user_mock, self.db_mock)
        
        assert result == {"status": "error"}
        mock_create_response.assert_called_with("error", "No tienes permiso para editar un lote en esta finca")

    @patch('use_cases.update_plot_use_case.get_state')
    @patch('use_cases.update_plot_use_case.get_user_role_ids')
    @patch('use_cases.update_plot_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.update_plot_use_case.create_response')
    def test_update_plot_location_insufficient_permissions(self, mock_create_response, 
                                                          mock_get_permissions, mock_get_user_role_ids, 
                                                          mock_get_state):
        """Test when user role doesn't have edit_plot permission for location update"""
        mock_get_state.side_effect = [self.active_plot_state, self.active_urf_state]
        mock_get_user_role_ids.return_value = [1]
        mock_get_permissions.return_value = ["view_plot"]  # No edit permission
        
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,
            self.farm_mock,
            self.user_role_farm_mock
        ]
        mock_create_response.return_value = {"status": "error"}
        
        result = update_plot_location(self.location_request, self.user_mock, self.db_mock)
        
        assert result == {"status": "error"}
        mock_create_response.assert_called_with("error", "No tienes permiso para editar un lote en esta finca")

    @patch('use_cases.update_plot_use_case.get_state')
    @patch('use_cases.update_plot_use_case.create_response')
    def test_update_plot_location_user_role_farm_state_not_found(self, mock_create_response, mock_get_state):
        """Test when user_role_farm active state is not found during location update"""
        mock_get_state.side_effect = [self.active_plot_state, None]  # Second call returns None
        
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,
            self.farm_mock
        ]
        mock_create_response.return_value = {"status": "error"}
        
        result = update_plot_location(self.location_request, self.user_mock, self.db_mock)
        
        assert result == {"status": "error"}
        mock_create_response.assert_called_with("error", "No se encontró el estado 'Activo' para el tipo 'user_role_farm'", status_code=400) 