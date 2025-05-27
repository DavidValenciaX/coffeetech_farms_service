"""
Pruebas unitarias para get_plot_use_case.py
"""
import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from decimal import Decimal

from use_cases.get_plot_use_case import get_plot

class TestGetPlotUseCase:
    """Clase de pruebas para el caso de uso de obtener información de un lote"""
    
    def setup_method(self):
        """Configuración inicial para cada prueba"""
        self.db_mock = Mock(spec=Session)
        self.user_mock = Mock()
        self.user_mock.user_id = "test_user_id"
        
        # Mock states
        self.active_plot_state = Mock()
        self.active_plot_state.plot_state_id = 1
        
        self.active_farm_state = Mock()
        self.active_farm_state.farm_state_id = 1
        
        self.active_urf_state = Mock()
        self.active_urf_state.user_role_farm_state_id = 1
        
        # Mock plot
        self.plot_mock = Mock()
        self.plot_mock.plot_id = 1
        self.plot_mock.name = "Test Plot"
        self.plot_mock.farm_id = 1
        self.plot_mock.coffee_variety_id = 1
        self.plot_mock.latitude = Decimal("10.123456")
        self.plot_mock.longitude = Decimal("-84.123456")
        self.plot_mock.altitude = Decimal("1500.00")
        
        # Mock farm
        self.farm_mock = Mock()
        self.farm_mock.farm_id = 1
        self.farm_mock.name = "Test Farm"
        
        # Mock user role farm
        self.user_role_farm_mock = Mock()
        self.user_role_farm_mock.user_role_id = 1
        
        # Mock coffee variety
        self.coffee_variety_mock = Mock()
        self.coffee_variety_mock.name = "Arabica"
        
    @patch('use_cases.get_plot_use_case.get_state')
    @patch('use_cases.get_plot_use_case.get_user_role_ids')
    @patch('use_cases.get_plot_use_case.get_role_permissions_for_user_role')
    def test_get_plot_success(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Prueba el caso exitoso de obtener información de un lote"""
        # Arrange
        plot_id = 1
        
        # Mock get_state calls
        mock_get_state.side_effect = [
            self.active_plot_state,
            self.active_farm_state,
            self.active_urf_state
        ]
        
        # Mock database queries
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,  # plot query
            self.farm_mock,  # farm query
            self.user_role_farm_mock,  # user_role_farm query
            self.coffee_variety_mock  # coffee_variety query
        ]
        
        # Mock user service calls
        mock_get_user_role_ids.return_value = [1, 2, 3]
        mock_get_permissions.return_value = ["read_plots", "write_plots"]
        
        # Act
        result = get_plot(plot_id, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 200
        response_data = result.body.decode()
        assert '"status":"success"' in response_data
        assert '"message":"Lote obtenido exitosamente"' in response_data
        assert '"plot_id":1' in response_data
        assert '"name":"Test Plot"' in response_data
        assert '"coffee_variety_name":"Arabica"' in response_data
        assert '"farm_id":1' in response_data
        
        # Verify calls
        mock_get_user_role_ids.assert_called_once_with(self.user_mock.user_id)
        mock_get_permissions.assert_called_once_with(1)
        assert self.db_mock.query.call_count == 4

    @patch('use_cases.get_plot_use_case.get_state')
    def test_get_plot_not_found(self, mock_get_state):
        """Prueba cuando el lote no existe o no está activo"""
        # Arrange
        plot_id = 999
        mock_get_state.return_value = self.active_plot_state
        
        # Mock plot not found
        self.db_mock.query.return_value.filter.return_value.first.return_value = None
        
        # Act
        result = get_plot(plot_id, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 200
        response_data = result.body.decode()
        assert '"status":"error"' in response_data
        assert '"message":"El lote no existe o no está activo"' in response_data

    @patch('use_cases.get_plot_use_case.get_state')
    def test_get_plot_farm_not_found(self, mock_get_state):
        """Prueba cuando la finca asociada al lote no existe o no está activa"""
        # Arrange
        plot_id = 1
        mock_get_state.side_effect = [
            self.active_plot_state,
            self.active_farm_state,
            self.active_urf_state  # Add the third call that would be made
        ]
        
        # Mock plot found but farm not found
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,  # plot found
            None  # farm not found
        ]
        
        # Act
        result = get_plot(plot_id, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 200
        response_data = result.body.decode()
        assert '"status":"error"' in response_data
        assert '"message":"La finca asociada al lote no existe o no está activa"' in response_data

    @patch('use_cases.get_plot_use_case.get_state')
    @patch('use_cases.get_plot_use_case.get_user_role_ids')
    def test_get_plot_no_permission(self, mock_get_user_role_ids, mock_get_state):
        """Prueba cuando el usuario no tiene permiso para ver el lote"""
        # Arrange
        plot_id = 1
        mock_get_state.side_effect = [
            self.active_plot_state,
            self.active_farm_state,
            self.active_urf_state
        ]
        
        # Mock plot and farm found
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,  # plot found
            self.farm_mock,  # farm found
            None  # user_role_farm not found (no permission)
        ]
        
        mock_get_user_role_ids.return_value = [1, 2, 3]
        
        # Act
        result = get_plot(plot_id, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 200
        response_data = result.body.decode()
        assert '"status":"error"' in response_data
        assert '"message":"No tienes permiso para ver este lote"' in response_data

    @patch('use_cases.get_plot_use_case.get_state')
    @patch('use_cases.get_plot_use_case.get_user_role_ids')
    def test_get_plot_user_service_error(self, mock_get_user_role_ids, mock_get_state):
        """Prueba cuando hay error al obtener roles del usuario"""
        # Arrange
        plot_id = 1
        mock_get_state.side_effect = [
            self.active_plot_state,
            self.active_farm_state,
            self.active_urf_state  # Add the third call that would be made
        ]
        
        # Mock plot and farm found
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,  # plot found
            self.farm_mock   # farm found
        ]
        
        # Mock user service error
        mock_get_user_role_ids.side_effect = Exception("User service unavailable")
        
        # Act
        result = get_plot(plot_id, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 500
        response_data = result.body.decode()
        assert '"status":"error"' in response_data
        assert '"message":"No se pudieron obtener los roles del usuario"' in response_data

    @patch('use_cases.get_plot_use_case.get_state')
    @patch('use_cases.get_plot_use_case.get_user_role_ids')
    @patch('use_cases.get_plot_use_case.get_role_permissions_for_user_role')
    def test_get_plot_permissions_service_error(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Prueba cuando hay error al obtener permisos del rol"""
        # Arrange
        plot_id = 1
        mock_get_state.side_effect = [
            self.active_plot_state,
            self.active_farm_state,
            self.active_urf_state
        ]
        
        # Mock plot, farm, and user_role_farm found
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,  # plot found
            self.farm_mock,  # farm found
            self.user_role_farm_mock  # user_role_farm found
        ]
        
        mock_get_user_role_ids.return_value = [1, 2, 3]
        
        # Mock permissions service error
        mock_get_permissions.side_effect = Exception("Permissions service unavailable")
        
        # Act
        result = get_plot(plot_id, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 500
        response_data = result.body.decode()
        assert '"status":"error"' in response_data
        assert '"message":"No se pudieron obtener los permisos del rol"' in response_data

    @patch('use_cases.get_plot_use_case.get_state')
    @patch('use_cases.get_plot_use_case.get_user_role_ids')
    @patch('use_cases.get_plot_use_case.get_role_permissions_for_user_role')
    def test_get_plot_insufficient_permissions(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Prueba cuando el usuario no tiene el permiso 'read_plots'"""
        # Arrange
        plot_id = 1
        mock_get_state.side_effect = [
            self.active_plot_state,
            self.active_farm_state,
            self.active_urf_state
        ]
        
        # Mock plot, farm, and user_role_farm found
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,  # plot found
            self.farm_mock,  # farm found
            self.user_role_farm_mock  # user_role_farm found
        ]
        
        mock_get_user_role_ids.return_value = [1, 2, 3]
        
        # Mock permissions without 'read_plots'
        mock_get_permissions.return_value = ["write_plots", "delete_plots"]
        
        # Act
        result = get_plot(plot_id, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 200
        response_data = result.body.decode()
        assert '"status":"error"' in response_data
        assert '"message":"No tienes permiso para ver este lote"' in response_data

    @patch('use_cases.get_plot_use_case.get_state')
    def test_get_plot_database_error(self, mock_get_state):
        """Prueba cuando hay error en la base de datos"""
        # Arrange
        plot_id = 1
        mock_get_state.return_value = self.active_plot_state
        
        # Mock database error
        self.db_mock.query.side_effect = Exception("Database connection error")
        
        # Act & Assert
        with pytest.raises(Exception, match="Database connection error"):
            get_plot(plot_id, self.user_mock, self.db_mock)

    @patch('use_cases.get_plot_use_case.get_state')
    def test_get_plot_missing_active_states(self, mock_get_state):
        """Prueba cuando no se pueden obtener los estados activos"""
        # Arrange
        plot_id = 1
        
        # Mock get_state returning None (missing active state)
        mock_get_state.return_value = None
        
        # Act & Assert
        # This should cause an AttributeError when trying to access .plot_state_id on None
        with pytest.raises(AttributeError):
            get_plot(plot_id, self.user_mock, self.db_mock)

    @patch('use_cases.get_plot_use_case.get_state')
    @patch('use_cases.get_plot_use_case.get_user_role_ids')
    @patch('use_cases.get_plot_use_case.get_role_permissions_for_user_role')
    def test_get_plot_success_without_coffee_variety(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Prueba el caso exitoso cuando no hay variedad de café asociada"""
        # Arrange
        plot_id = 1
        
        mock_get_state.side_effect = [
            self.active_plot_state,
            self.active_farm_state,
            self.active_urf_state
        ]
        
        # Mock database queries - coffee variety not found
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,  # plot query
            self.farm_mock,  # farm query
            self.user_role_farm_mock,  # user_role_farm query
            None  # coffee_variety query returns None
        ]
        
        mock_get_user_role_ids.return_value = [1, 2, 3]
        mock_get_permissions.return_value = ["read_plots", "write_plots"]
        
        # Act
        result = get_plot(plot_id, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 200
        response_data = result.body.decode()
        assert '"status":"success"' in response_data
        assert '"coffee_variety_name":null' in response_data

    @patch('use_cases.get_plot_use_case.get_state')
    @patch('use_cases.get_plot_use_case.get_user_role_ids')
    @patch('use_cases.get_plot_use_case.get_role_permissions_for_user_role')
    def test_get_plot_success_with_null_coordinates(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Prueba el caso exitoso cuando las coordenadas son nulas"""
        # Arrange
        plot_id = 1
        
        # Mock plot with null coordinates
        plot_with_null_coords = Mock()
        plot_with_null_coords.plot_id = 1
        plot_with_null_coords.name = "Test Plot"
        plot_with_null_coords.farm_id = 1
        plot_with_null_coords.coffee_variety_id = 1
        plot_with_null_coords.latitude = None
        plot_with_null_coords.longitude = None
        plot_with_null_coords.altitude = None
        
        mock_get_state.side_effect = [
            self.active_plot_state,
            self.active_farm_state,
            self.active_urf_state
        ]
        
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            plot_with_null_coords,  # plot query
            self.farm_mock,  # farm query
            self.user_role_farm_mock,  # user_role_farm query
            self.coffee_variety_mock  # coffee_variety query
        ]
        
        mock_get_user_role_ids.return_value = [1, 2, 3]
        mock_get_permissions.return_value = ["read_plots"]
        
        # Act
        result = get_plot(plot_id, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 200
        response_data = result.body.decode()
        assert '"status":"success"' in response_data
        assert '"latitude":null' in response_data
        assert '"longitude":null' in response_data
        assert '"altitude":null' in response_data

    @patch('use_cases.get_plot_use_case.get_state')
    @patch('use_cases.get_plot_use_case.get_user_role_ids')
    @patch('use_cases.get_plot_use_case.get_role_permissions_for_user_role')
    def test_get_plot_with_empty_permissions_list(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Prueba cuando la lista de permisos está vacía"""
        # Arrange
        plot_id = 1
        mock_get_state.side_effect = [
            self.active_plot_state,
            self.active_farm_state,
            self.active_urf_state
        ]
        
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,  # plot found
            self.farm_mock,  # farm found
            self.user_role_farm_mock  # user_role_farm found
        ]
        
        mock_get_user_role_ids.return_value = [1, 2, 3]
        mock_get_permissions.return_value = []  # Empty permissions list
        
        # Act
        result = get_plot(plot_id, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 200
        response_data = result.body.decode()
        assert '"status":"error"' in response_data
        assert '"message":"No tienes permiso para ver este lote"' in response_data

    @patch('use_cases.get_plot_use_case.get_state')
    @patch('use_cases.get_plot_use_case.get_user_role_ids')
    def test_get_plot_with_empty_user_role_ids(self, mock_get_user_role_ids, mock_get_state):
        """Prueba cuando el usuario no tiene roles asignados"""
        # Arrange
        plot_id = 1
        mock_get_state.side_effect = [
            self.active_plot_state,
            self.active_farm_state,
            self.active_urf_state
        ]
        
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,  # plot found
            self.farm_mock,  # farm found
            None  # user_role_farm not found due to empty user_role_ids
        ]
        
        mock_get_user_role_ids.return_value = []  # Empty user role ids
        
        # Act
        result = get_plot(plot_id, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 200
        response_data = result.body.decode()
        assert '"status":"error"' in response_data
        assert '"message":"No tienes permiso para ver este lote"' in response_data 