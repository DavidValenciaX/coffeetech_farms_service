"""
Pruebas unitarias para create_plot_use_case.py
"""
import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from fastapi import HTTPException
from decimal import Decimal

from use_cases.create_plot_use_case import create_plot


class TestCreatePlotUseCase:
    """Clase de pruebas para el caso de uso de creación de lotes"""
    
    def setup_method(self):
        """Configuración inicial para cada prueba"""
        self.db_mock = Mock(spec=Session)
        self.user_mock = Mock()
        self.user_mock.user_id = "test_user_id"
        
        # Mock request object
        self.request_mock = Mock()
        self.request_mock.name = "Test Plot"
        self.request_mock.farm_id = 1
        self.request_mock.coffee_variety_id = 1
        self.request_mock.latitude = Decimal("10.123456")
        self.request_mock.longitude = Decimal("-84.123456")
        self.request_mock.altitude = Decimal("1500.00")
        
        # Mock states
        self.active_farm_state = Mock()
        self.active_farm_state.farm_state_id = 1
        
        self.active_urf_state = Mock()
        self.active_urf_state.user_role_farm_state_id = 1
        
        self.active_plot_state = Mock()
        self.active_plot_state.plot_state_id = 1
        
        self.inactive_plot_state = Mock()
        self.inactive_plot_state.plot_state_id = 2
        
        # Mock farm
        self.farm_mock = Mock()
        self.farm_mock.farm_id = 1
        self.farm_mock.name = "Test Farm"
        
        # Mock user role farm
        self.user_role_farm_mock = Mock()
        self.user_role_farm_mock.user_role_id = 1
        self.user_role_farm_mock.farm_id = 1
        
        # Mock coffee variety
        self.coffee_variety_mock = Mock()
        self.coffee_variety_mock.coffee_variety_id = 1
        self.coffee_variety_mock.name = "Arabica"
        
        # Mock plot
        self.plot_mock = Mock()
        self.plot_mock.plot_id = 1
        self.plot_mock.name = "Test Plot"
        self.plot_mock.farm_id = 1
        self.plot_mock.coffee_variety_id = 1
        self.plot_mock.latitude = Decimal("10.123456")
        self.plot_mock.longitude = Decimal("-84.123456")
        self.plot_mock.altitude = Decimal("1500.00")
        self.plot_mock.plot_state_id = 1

    @patch('use_cases.create_plot_use_case.get_state')
    @patch('use_cases.create_plot_use_case.get_user_role_ids')
    @patch('use_cases.create_plot_use_case.get_role_permissions_for_user_role')
    def test_create_plot_success(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Test successful plot creation"""
        # Setup mocks
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state,
            self.active_plot_state,
            self.inactive_plot_state
        ]
        mock_get_user_role_ids.return_value = [1]
        mock_get_permissions.return_value = ["add_plot"]
        
        # Setup database queries
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm query
            self.user_role_farm_mock,  # UserRoleFarm query
            None,  # Active plot check (no existing)
            self.coffee_variety_mock,  # Coffee variety query
            None,  # Inactive plot check (no existing)
        ]
        
        # Setup new plot creation
        self.db_mock.add = Mock()
        self.db_mock.commit = Mock()
        self.db_mock.refresh = Mock()
        
        # Execute
        result = create_plot(self.request_mock, self.user_mock, self.db_mock)
        
        # Verify
        assert result.status_code == 200
        response_data = result.body.decode()
        assert '"status":"success"' in response_data
        assert '"message":"Lote creado correctamente"' in response_data
        self.db_mock.add.assert_called_once()
        self.db_mock.commit.assert_called_once()

    @patch('use_cases.create_plot_use_case.get_state')
    def test_create_plot_missing_active_farm_state(self, mock_get_state):
        """Test error when active farm state is not found"""
        mock_get_state.return_value = None
        
        result = create_plot(self.request_mock, self.user_mock, self.db_mock)
        
        assert result.status_code == 400
        response_data = result.body.decode()
        assert '"status":"error"' in response_data
        assert "No se encontró el estado \'Activo\' para el tipo \'Farms\'" in response_data

    @patch('use_cases.create_plot_use_case.get_state')
    def test_create_plot_missing_active_urf_state(self, mock_get_state):
        """Test error when active user_role_farm state is not found"""
        mock_get_state.side_effect = [self.active_farm_state, None]
        
        result = create_plot(self.request_mock, self.user_mock, self.db_mock)
        
        assert result.status_code == 400
        response_data = result.body.decode()
        assert '"status":"error"' in response_data
        assert "No se encontró el estado \'Activo\' para el tipo \'user_role_farm\'" in response_data

    @patch('use_cases.create_plot_use_case.get_state')
    def test_create_plot_missing_active_plot_state(self, mock_get_state):
        """Test error when active plot state is not found"""
        mock_get_state.side_effect = [self.active_farm_state, self.active_urf_state, None]
        
        result = create_plot(self.request_mock, self.user_mock, self.db_mock)
        
        assert result.status_code == 400
        response_data = result.body.decode()
        assert '"status":"error"' in response_data
        assert "No se encontró el estado \'Activo\' para el tipo \'Plots\'" in response_data

    @patch('use_cases.create_plot_use_case.get_state')
    def test_create_plot_missing_inactive_plot_state(self, mock_get_state):
        """Test error when inactive plot state is not found"""
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state,
            self.active_plot_state,
            None
        ]
        
        result = create_plot(self.request_mock, self.user_mock, self.db_mock)
        
        assert result.status_code == 400
        response_data = result.body.decode()
        assert '"status":"error"' in response_data
        assert "No se encontró el estado \'Inactivo\' para el tipo \'Plots\'" in response_data

    @patch('use_cases.create_plot_use_case.get_state')
    @patch('use_cases.create_plot_use_case.get_user_role_ids')
    def test_create_plot_farm_not_found(self, mock_get_user_role_ids, mock_get_state):
        """Test error when farm is not found or not active"""
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state,
            self.active_plot_state,
            self.inactive_plot_state
        ]
        mock_get_user_role_ids.return_value = [1]
        
        self.db_mock.query.return_value.filter.return_value.first.return_value = None
        
        result = create_plot(self.request_mock, self.user_mock, self.db_mock)
        
        assert result.status_code == 200
        response_data = result.body.decode()
        assert '"status":"error"' in response_data
        assert "La finca no existe o no está activa" in response_data

    @patch('use_cases.create_plot_use_case.get_state')
    @patch('use_cases.create_plot_use_case.get_user_role_ids')
    def test_create_plot_user_service_error(self, mock_get_user_role_ids, mock_get_state):
        """Test error when user service fails"""
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state,
            self.active_plot_state,
            self.inactive_plot_state
        ]
        mock_get_user_role_ids.side_effect = Exception("User service error")
        
        self.db_mock.query.return_value.filter.return_value.first.return_value = self.farm_mock
        
        result = create_plot(self.request_mock, self.user_mock, self.db_mock)
        
        assert result.status_code == 500
        response_data = result.body.decode()
        assert '"status":"error"' in response_data
        assert "No se pudieron obtener los roles del usuario" in response_data

    @patch('use_cases.create_plot_use_case.get_state')
    @patch('use_cases.create_plot_use_case.get_user_role_ids')
    def test_create_plot_no_permission(self, mock_get_user_role_ids, mock_get_state):
        """Test error when user has no permission for the farm"""
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state,
            self.active_plot_state,
            self.inactive_plot_state
        ]
        mock_get_user_role_ids.return_value = [1]
        
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm query
            None,  # UserRoleFarm query (no permission)
        ]
        
        result = create_plot(self.request_mock, self.user_mock, self.db_mock)
        
        assert result.status_code == 200
        response_data = result.body.decode()
        assert '"status":"error"' in response_data
        assert "No tienes permiso para agregar un lote en esta finca" in response_data

    @patch('use_cases.create_plot_use_case.get_state')
    @patch('use_cases.create_plot_use_case.get_user_role_ids')
    @patch('use_cases.create_plot_use_case.get_role_permissions_for_user_role')
    def test_create_plot_insufficient_permissions(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Test error when user doesn't have add_plot permission"""
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state,
            self.active_plot_state,
            self.inactive_plot_state
        ]
        mock_get_user_role_ids.return_value = [1]
        mock_get_permissions.return_value = ["view_plot"]  # No add_plot permission
        
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm query
            self.user_role_farm_mock,  # UserRoleFarm query
        ]
        
        result = create_plot(self.request_mock, self.user_mock, self.db_mock)
        
        assert result.status_code == 200
        response_data = result.body.decode()
        assert '"status":"error"' in response_data
        assert "No tienes permiso para agregar un lote en esta finca" in response_data

    @patch('use_cases.create_plot_use_case.get_state')
    @patch('use_cases.create_plot_use_case.get_user_role_ids')
    @patch('use_cases.create_plot_use_case.get_role_permissions_for_user_role')
    def test_create_plot_empty_name(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Test error when plot name is empty"""
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state,
            self.active_plot_state,
            self.inactive_plot_state
        ]
        mock_get_user_role_ids.return_value = [1]
        mock_get_permissions.return_value = ["add_plot"]
        
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm query
            self.user_role_farm_mock,  # UserRoleFarm query
        ]
        
        # Set empty name
        self.request_mock.name = ""
        
        result = create_plot(self.request_mock, self.user_mock, self.db_mock)
        
        assert result.status_code == 200
        response_data = result.body.decode()
        assert '"status":"error"' in response_data
        assert "El nombre del lote no puede estar vacío" in response_data

    @patch('use_cases.create_plot_use_case.get_state')
    @patch('use_cases.create_plot_use_case.get_user_role_ids')
    @patch('use_cases.create_plot_use_case.get_role_permissions_for_user_role')
    def test_create_plot_name_too_long(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Test error when plot name is too long"""
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state,
            self.active_plot_state,
            self.inactive_plot_state
        ]
        mock_get_user_role_ids.return_value = [1]
        mock_get_permissions.return_value = ["add_plot"]
        
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm query
            self.user_role_farm_mock,  # UserRoleFarm query
        ]
        
        # Set name too long (over 100 characters)
        self.request_mock.name = "a" * 101
        
        result = create_plot(self.request_mock, self.user_mock, self.db_mock)
        
        assert result.status_code == 200
        response_data = result.body.decode()
        assert '"status":"error"' in response_data
        assert "El nombre del lote no puede tener más de 100 caracteres" in response_data

    @patch('use_cases.create_plot_use_case.get_state')
    @patch('use_cases.create_plot_use_case.get_user_role_ids')
    @patch('use_cases.create_plot_use_case.get_role_permissions_for_user_role')
    def test_create_plot_duplicate_name_in_farm(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Test error when plot name already exists in farm"""
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state,
            self.active_plot_state,
            self.inactive_plot_state
        ]
        mock_get_user_role_ids.return_value = [1]
        mock_get_permissions.return_value = ["add_plot"]
        
        existing_plot = Mock()
        existing_plot.name = "Test Plot"
        
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm query
            self.user_role_farm_mock,  # UserRoleFarm query
            existing_plot,  # Active plot check (existing)
        ]
        
        result = create_plot(self.request_mock, self.user_mock, self.db_mock)
        
        assert result.status_code == 200
        response_data = result.body.decode()
        assert '"status":"error"' in response_data
        assert "Ya existe un lote activo con el nombre \'Test Plot\' en esta finca" in response_data

    @patch('use_cases.create_plot_use_case.get_state')
    @patch('use_cases.create_plot_use_case.get_user_role_ids')
    @patch('use_cases.create_plot_use_case.get_role_permissions_for_user_role')
    def test_create_plot_invalid_coffee_variety(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Test error when coffee variety doesn't exist"""
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state,
            self.active_plot_state,
            self.inactive_plot_state
        ]
        mock_get_user_role_ids.return_value = [1]
        mock_get_permissions.return_value = ["add_plot"]
        
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm query
            self.user_role_farm_mock,  # UserRoleFarm query
            None,  # Active plot check (no existing)
            None,  # Coffee variety query (not found)
        ]
        
        result = create_plot(self.request_mock, self.user_mock, self.db_mock)
        
        assert result.status_code == 200
        response_data = result.body.decode()
        assert '"status":"error"' in response_data
        assert "La variedad de café con ID \'1\' no existe" in response_data

    @patch('use_cases.create_plot_use_case.get_state')
    @patch('use_cases.create_plot_use_case.get_user_role_ids')
    @patch('use_cases.create_plot_use_case.get_role_permissions_for_user_role')
    def test_create_plot_reactivate_inactive_plot(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Test successful reactivation of inactive plot"""
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state,
            self.active_plot_state,
            self.inactive_plot_state
        ]
        mock_get_user_role_ids.return_value = [1]
        mock_get_permissions.return_value = ["add_plot"]
        
        inactive_plot = Mock()
        inactive_plot.plot_id = 2
        inactive_plot.name = "Test Plot"
        inactive_plot.farm_id = 1
        inactive_plot.latitude = Decimal("10.123456")
        inactive_plot.longitude = Decimal("-84.123456")
        inactive_plot.altitude = Decimal("1500.00")
        
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm query
            self.user_role_farm_mock,  # UserRoleFarm query
            None,  # Active plot check (no existing)
            self.coffee_variety_mock,  # Coffee variety query
            inactive_plot,  # Inactive plot check (existing)
        ]
        
        self.db_mock.commit = Mock()
        self.db_mock.refresh = Mock()
        
        result = create_plot(self.request_mock, self.user_mock, self.db_mock)
        
        assert result.status_code == 200
        response_data = result.body.decode()
        assert '"status":"success"' in response_data
        assert '"message":"Lote reactivado y actualizado correctamente"' in response_data
        assert '"reactivated":true' in response_data
        self.db_mock.commit.assert_called_once()

    @patch('use_cases.create_plot_use_case.get_state')
    @patch('use_cases.create_plot_use_case.get_user_role_ids')
    @patch('use_cases.create_plot_use_case.get_role_permissions_for_user_role')
    def test_create_plot_database_error_on_creation(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Test database error during plot creation"""
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state,
            self.active_plot_state,
            self.inactive_plot_state
        ]
        mock_get_user_role_ids.return_value = [1]
        mock_get_permissions.return_value = ["add_plot"]
        
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm query
            self.user_role_farm_mock,  # UserRoleFarm query
            None,  # Active plot check (no existing)
            self.coffee_variety_mock,  # Coffee variety query
            None,  # Inactive plot check (no existing)
        ]
        
        # Simulate database error
        self.db_mock.commit.side_effect = Exception("Database error")
        self.db_mock.rollback = Mock()
        
        with pytest.raises(HTTPException) as exc_info:
            create_plot(self.request_mock, self.user_mock, self.db_mock)
        
        assert exc_info.value.status_code == 500
        assert "Error al crear el lote" in str(exc_info.value.detail)
        self.db_mock.rollback.assert_called_once()

    @patch('use_cases.create_plot_use_case.get_state')
    @patch('use_cases.create_plot_use_case.get_user_role_ids')
    @patch('use_cases.create_plot_use_case.get_role_permissions_for_user_role')
    def test_create_plot_database_error_on_reactivation(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Test database error during plot reactivation"""
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state,
            self.active_plot_state,
            self.inactive_plot_state
        ]
        mock_get_user_role_ids.return_value = [1]
        mock_get_permissions.return_value = ["add_plot"]
        
        inactive_plot = Mock()
        inactive_plot.plot_id = 2
        inactive_plot.name = "Test Plot"
        inactive_plot.farm_id = 1
        
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm query
            self.user_role_farm_mock,  # UserRoleFarm query
            None,  # Active plot check (no existing)
            self.coffee_variety_mock,  # Coffee variety query
            inactive_plot,  # Inactive plot check (existing)
        ]
        
        # Simulate database error
        self.db_mock.commit.side_effect = Exception("Database error")
        self.db_mock.rollback = Mock()
        
        with pytest.raises(HTTPException) as exc_info:
            create_plot(self.request_mock, self.user_mock, self.db_mock)
        
        assert exc_info.value.status_code == 500
        assert "Error al reactivar el lote" in str(exc_info.value.detail)
        self.db_mock.rollback.assert_called_once()

    @patch('use_cases.create_plot_use_case.get_state')
    @patch('use_cases.create_plot_use_case.get_user_role_ids')
    @patch('use_cases.create_plot_use_case.get_role_permissions_for_user_role')
    def test_create_plot_permissions_service_error(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Test error when permissions service fails"""
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state,
            self.active_plot_state,
            self.inactive_plot_state
        ]
        mock_get_user_role_ids.return_value = [1]
        mock_get_permissions.side_effect = Exception("Permissions service error")
        
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm query
            self.user_role_farm_mock,  # UserRoleFarm query
        ]
        
        result = create_plot(self.request_mock, self.user_mock, self.db_mock)
        
        assert result.status_code == 500
        response_data = result.body.decode()
        assert '"status":"error"' in response_data
        assert "No se pudieron obtener los permisos del rol" in response_data

    @patch('use_cases.create_plot_use_case.get_state')
    @patch('use_cases.create_plot_use_case.get_user_role_ids')
    @patch('use_cases.create_plot_use_case.get_role_permissions_for_user_role')
    def test_create_plot_with_whitespace_name(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Test error when plot name contains only whitespace"""
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state,
            self.active_plot_state,
            self.inactive_plot_state
        ]
        mock_get_user_role_ids.return_value = [1]
        mock_get_permissions.return_value = ["add_plot"]
        
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm query
            self.user_role_farm_mock,  # UserRoleFarm query
        ]
        
        # Set name with only whitespace
        self.request_mock.name = "   "
        
        result = create_plot(self.request_mock, self.user_mock, self.db_mock)
        
        assert result.status_code == 200
        response_data = result.body.decode()
        assert '"status":"error"' in response_data
        assert "El nombre del lote no puede estar vacío" in response_data

    @patch('use_cases.create_plot_use_case.get_state')
    @patch('use_cases.create_plot_use_case.get_user_role_ids')
    @patch('use_cases.create_plot_use_case.get_role_permissions_for_user_role')
    def test_create_plot_with_none_name(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Test error when plot name is None"""
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state,
            self.active_plot_state,
            self.inactive_plot_state
        ]
        mock_get_user_role_ids.return_value = [1]
        mock_get_permissions.return_value = ["add_plot"]
        
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.farm_mock,  # Farm query
            self.user_role_farm_mock,  # UserRoleFarm query
        ]
        
        # Set name to None
        self.request_mock.name = None
        
        result = create_plot(self.request_mock, self.user_mock, self.db_mock)
        
        assert result.status_code == 200
        response_data = result.body.decode()
        assert '"status":"error"' in response_data
        assert "El nombre del lote no puede estar vacío" in response_data