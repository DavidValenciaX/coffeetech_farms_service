"""
Pruebas unitarias para list_plots_use_case.py
"""
import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from decimal import Decimal
from fastapi import HTTPException

from use_cases.list_plots_use_case import list_plots

class TestListPlotsUseCase:
    """Clase de pruebas para el caso de uso de listado de lotes"""
    
    def setup_method(self):
        """Configuración inicial para cada prueba"""
        self.db_mock = Mock(spec=Session)
        self.user_mock = Mock()
        self.user_mock.user_id = "test_user_id"
        
        # Mock states
        self.active_farm_state = Mock()
        self.active_farm_state.farm_state_id = 1
        
        self.active_urf_state = Mock()
        self.active_urf_state.user_role_farm_state_id = 1
        
        self.active_plot_state = Mock()
        self.active_plot_state.plot_state_id = 1
        
        # Mock farm
        self.farm_mock = Mock()
        self.farm_mock.farm_id = 1
        self.farm_mock.name = "Test Farm"
        
        # Mock user role farm
        self.user_role_farm_mock = Mock()
        self.user_role_farm_mock.user_role_id = 1
        
        # Mock plots
        self.plot1_mock = Mock()
        self.plot1_mock.plot_id = 1
        self.plot1_mock.name = "Plot 1"
        self.plot1_mock.coffee_variety_id = 1
        self.plot1_mock.latitude = Decimal("10.123456")
        self.plot1_mock.longitude = Decimal("-84.123456")
        self.plot1_mock.altitude = Decimal("1500.00")
        
        self.plot2_mock = Mock()
        self.plot2_mock.plot_id = 2
        self.plot2_mock.name = "Plot 2"
        self.plot2_mock.coffee_variety_id = 2
        self.plot2_mock.latitude = Decimal("10.654321")
        self.plot2_mock.longitude = Decimal("-84.654321")
        self.plot2_mock.altitude = Decimal("1200.00")
        
        # Mock coffee varieties
        self.coffee_variety1_mock = Mock()
        self.coffee_variety1_mock.name = "Arabica"
        
        self.coffee_variety2_mock = Mock()
        self.coffee_variety2_mock.name = "Robusta"

    @patch('use_cases.list_plots_use_case.get_state')
    @patch('use_cases.list_plots_use_case.get_user_role_ids')
    @patch('use_cases.list_plots_use_case.get_role_permissions_for_user_role')
    def test_list_plots_success(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Prueba el listado exitoso de lotes"""
        # Arrange
        farm_id = 1
        
        # Mock get_state calls
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state,
            self.active_plot_state
        ]
        
        # Mock user service calls
        mock_get_user_role_ids.return_value = [1, 2, 3]
        mock_get_permissions.return_value = ["read_plots", "write_plots"]
        
        # Mock database queries
        query_mock = Mock()
        filter_mock = Mock()
        
        # Setup query chain for farm
        self.db_mock.query.return_value = query_mock
        query_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = self.farm_mock
        
        # Setup query chain for user_role_farm
        query_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = self.user_role_farm_mock
        
        # Setup query chain for plots
        query_mock.filter.return_value = filter_mock
        filter_mock.all.return_value = [self.plot1_mock, self.plot2_mock]
        
        # Setup query chain for coffee varieties
        filter_mock.first.side_effect = [
            self.farm_mock,  # farm query
            self.user_role_farm_mock,  # user_role_farm query
            self.coffee_variety1_mock,  # coffee variety for plot 1
            self.coffee_variety2_mock   # coffee variety for plot 2
        ]
        
        # Act
        result = list_plots(farm_id, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 200
        response_data = result.body.decode()
        assert '"status":"success"' in response_data
        assert '"message":"Lista de lotes obtenida exitosamente"' in response_data
        assert '"plot_id":1' in response_data
        assert '"plot_id":2' in response_data
        assert '"name":"Plot 1"' in response_data
        assert '"name":"Plot 2"' in response_data
        assert '"coffee_variety_name":"Arabica"' in response_data
        assert '"coffee_variety_name":"Robusta"' in response_data
        
        # Verify calls
        mock_get_user_role_ids.assert_called_once_with(self.user_mock.user_id)
        mock_get_permissions.assert_called_once_with(1)

    @patch('use_cases.list_plots_use_case.get_state')
    @patch('use_cases.list_plots_use_case.get_user_role_ids')
    @patch('use_cases.list_plots_use_case.get_role_permissions_for_user_role')
    def test_list_plots_empty_list(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Prueba el caso cuando no hay lotes en la finca"""
        # Arrange
        farm_id = 1
        
        # Mock get_state calls
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state,
            self.active_plot_state
        ]
        
        # Mock user service calls
        mock_get_user_role_ids.return_value = [1, 2, 3]
        mock_get_permissions.return_value = ["read_plots"]
        
        # Mock database queries
        query_mock = Mock()
        filter_mock = Mock()
        
        self.db_mock.query.return_value = query_mock
        query_mock.filter.return_value = filter_mock
        filter_mock.first.side_effect = [
            self.farm_mock,  # farm query
            self.user_role_farm_mock  # user_role_farm query
        ]
        filter_mock.all.return_value = []  # empty plots list
        
        # Act
        result = list_plots(farm_id, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 200
        response_data = result.body.decode()
        assert '"status":"success"' in response_data
        assert '"message":"Lista de lotes obtenida exitosamente"' in response_data
        assert '"plots":[]' in response_data

    @patch('use_cases.list_plots_use_case.get_state')
    def test_list_plots_farm_not_found(self, mock_get_state):
        """Prueba cuando la finca no existe o no está activa"""
        # Arrange
        farm_id = 999
        mock_get_state.return_value = self.active_farm_state
        
        # Mock farm not found
        query_mock = Mock()
        filter_mock = Mock()
        self.db_mock.query.return_value = query_mock
        query_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = None
        
        # Act
        result = list_plots(farm_id, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 200
        response_data = result.body.decode()
        assert '"status":"error"' in response_data
        assert '"message":"La finca no existe o no está activa"' in response_data

    @patch('use_cases.list_plots_use_case.get_state')
    @patch('use_cases.list_plots_use_case.get_user_role_ids')
    def test_list_plots_no_permission(self, mock_get_user_role_ids, mock_get_state):
        """Prueba cuando el usuario no tiene permiso para ver los lotes"""
        # Arrange
        farm_id = 1
        
        # Mock get_state calls
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state,
            self.active_plot_state
        ]
        
        # Mock user service calls
        mock_get_user_role_ids.return_value = [1, 2, 3]
        
        # Mock database queries
        query_mock = Mock()
        filter_mock = Mock()
        
        self.db_mock.query.return_value = query_mock
        query_mock.filter.return_value = filter_mock
        filter_mock.first.side_effect = [
            self.farm_mock,  # farm found
            None  # user_role_farm not found (no permission)
        ]
        
        # Act
        result = list_plots(farm_id, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 200
        response_data = result.body.decode()
        assert '"status":"error"' in response_data
        assert '"message":"No tienes permiso para ver los lotes de esta finca"' in response_data

    @patch('use_cases.list_plots_use_case.get_state')
    @patch('use_cases.list_plots_use_case.get_user_role_ids')
    def test_list_plots_user_service_error(self, mock_get_user_role_ids, mock_get_state):
        """Prueba el manejo de errores del servicio de usuarios al obtener roles"""
        # Arrange
        farm_id = 1
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state,
            self.active_plot_state
        ]
        
        # Mock farm found
        query_mock = Mock()
        filter_mock = Mock()
        self.db_mock.query.return_value = query_mock
        query_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = self.farm_mock
        
        # Mock user service error
        mock_get_user_role_ids.side_effect = Exception("User service unavailable")
        
        # Act
        result = list_plots(farm_id, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 500
        response_data = result.body.decode()
        assert '"status":"error"' in response_data
        assert '"message":"No se pudieron obtener los roles del usuario"' in response_data

    @patch('use_cases.list_plots_use_case.get_state')
    @patch('use_cases.list_plots_use_case.get_user_role_ids')
    @patch('use_cases.list_plots_use_case.get_role_permissions_for_user_role')
    def test_list_plots_permissions_service_error(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Prueba el manejo de errores del servicio de usuarios al obtener permisos"""
        # Arrange
        farm_id = 1
        
        # Mock get_state calls
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state,
            self.active_plot_state
        ]
        
        # Mock user service calls
        mock_get_user_role_ids.return_value = [1, 2, 3]
        mock_get_permissions.side_effect = Exception("Permissions service unavailable")
        
        # Mock database queries
        query_mock = Mock()
        filter_mock = Mock()
        
        self.db_mock.query.return_value = query_mock
        query_mock.filter.return_value = filter_mock
        filter_mock.first.side_effect = [
            self.farm_mock,  # farm found
            self.user_role_farm_mock  # user_role_farm found
        ]
        
        # Act
        result = list_plots(farm_id, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 500
        response_data = result.body.decode()
        assert '"status":"error"' in response_data
        assert '"message":"No se pudieron obtener los permisos del rol"' in response_data

    @patch('use_cases.list_plots_use_case.get_state')
    @patch('use_cases.list_plots_use_case.get_user_role_ids')
    @patch('use_cases.list_plots_use_case.get_role_permissions_for_user_role')
    def test_list_plots_insufficient_permissions(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Prueba cuando el usuario no tiene el permiso 'read_plots'"""
        # Arrange
        farm_id = 1
        
        # Mock get_state calls
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state,
            self.active_plot_state
        ]
        
        # Mock user service calls
        mock_get_user_role_ids.return_value = [1, 2, 3]
        mock_get_permissions.return_value = ["write_farms", "delete_farms"]  # No read_plots permission
        
        # Mock database queries
        query_mock = Mock()
        filter_mock = Mock()
        
        self.db_mock.query.return_value = query_mock
        query_mock.filter.return_value = filter_mock
        filter_mock.first.side_effect = [
            self.farm_mock,  # farm found
            self.user_role_farm_mock  # user_role_farm found
        ]
        
        # Act
        result = list_plots(farm_id, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 200
        response_data = result.body.decode()
        assert '"status":"error"' in response_data
        assert '"message":"No tienes permiso para ver los lotes de esta finca"' in response_data

    @patch('use_cases.list_plots_use_case.get_state')
    @patch('use_cases.list_plots_use_case.get_user_role_ids')
    @patch('use_cases.list_plots_use_case.get_role_permissions_for_user_role')
    def test_list_plots_database_error(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Prueba el manejo de errores de base de datos"""
        # Arrange
        farm_id = 1
        
        # Mock get_state calls
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state,
            self.active_plot_state
        ]
        
        # Mock user service calls
        mock_get_user_role_ids.return_value = [1, 2, 3]
        mock_get_permissions.return_value = ["read_plots"]
        
        # Mock database queries - farm and user_role_farm found
        query_mock = Mock()
        filter_mock = Mock()
        
        self.db_mock.query.return_value = query_mock
        query_mock.filter.return_value = filter_mock
        filter_mock.first.side_effect = [
            self.farm_mock,  # farm found
            self.user_role_farm_mock  # user_role_farm found
        ]
        
        # Mock database error when querying plots
        filter_mock.all.side_effect = Exception("Database connection error")
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            list_plots(farm_id, self.user_mock, self.db_mock)
        
        assert exc_info.value.status_code == 500
        assert "Error al obtener la lista de lotes: Database connection error" in str(exc_info.value.detail)

    @patch('use_cases.list_plots_use_case.get_state')
    def test_list_plots_missing_active_states(self, mock_get_state):
        """Prueba el caso cuando no se encuentran los estados activos"""
        # Arrange
        farm_id = 1
        mock_get_state.return_value = None  # No active state found
        
        # Act & Assert
        with pytest.raises(AttributeError):
            list_plots(farm_id, self.user_mock, self.db_mock)

    @patch('use_cases.list_plots_use_case.get_state')
    @patch('use_cases.list_plots_use_case.get_user_role_ids')
    @patch('use_cases.list_plots_use_case.get_role_permissions_for_user_role')
    def test_list_plots_success_without_coffee_variety(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Prueba el listado exitoso cuando un lote no tiene variedad de café asociada"""
        # Arrange
        farm_id = 1
        
        # Mock get_state calls
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state,
            self.active_plot_state
        ]
        
        # Mock user service calls
        mock_get_user_role_ids.return_value = [1, 2, 3]
        mock_get_permissions.return_value = ["read_plots"]
        
        # Mock database queries
        query_mock = Mock()
        filter_mock = Mock()
        
        self.db_mock.query.return_value = query_mock
        query_mock.filter.return_value = filter_mock
        filter_mock.first.side_effect = [
            self.farm_mock,  # farm query
            self.user_role_farm_mock,  # user_role_farm query
            None  # coffee variety not found
        ]
        filter_mock.all.return_value = [self.plot1_mock]
        
        # Act
        result = list_plots(farm_id, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 200
        response_data = result.body.decode()
        assert '"status":"success"' in response_data
        assert '"message":"Lista de lotes obtenida exitosamente"' in response_data
        assert '"coffee_variety_name":null' in response_data

    @patch('use_cases.list_plots_use_case.get_state')
    @patch('use_cases.list_plots_use_case.get_user_role_ids')
    @patch('use_cases.list_plots_use_case.get_role_permissions_for_user_role')
    def test_list_plots_success_with_null_coordinates(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Prueba el listado exitoso cuando un lote tiene coordenadas nulas"""
        # Arrange
        farm_id = 1
        
        # Mock plot with null coordinates
        plot_with_null_coords = Mock()
        plot_with_null_coords.plot_id = 3
        plot_with_null_coords.name = "Plot with null coords"
        plot_with_null_coords.coffee_variety_id = 1
        plot_with_null_coords.latitude = None
        plot_with_null_coords.longitude = None
        plot_with_null_coords.altitude = None
        
        # Mock get_state calls
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state,
            self.active_plot_state
        ]
        
        # Mock user service calls
        mock_get_user_role_ids.return_value = [1, 2, 3]
        mock_get_permissions.return_value = ["read_plots"]
        
        # Mock database queries
        query_mock = Mock()
        filter_mock = Mock()
        
        self.db_mock.query.return_value = query_mock
        query_mock.filter.return_value = filter_mock
        filter_mock.first.side_effect = [
            self.farm_mock,  # farm query
            self.user_role_farm_mock,  # user_role_farm query
            self.coffee_variety1_mock  # coffee variety query
        ]
        filter_mock.all.return_value = [plot_with_null_coords]
        
        # Act
        result = list_plots(farm_id, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 200
        response_data = result.body.decode()
        assert '"status":"success"' in response_data
        assert '"message":"Lista de lotes obtenida exitosamente"' in response_data
        assert '"latitude":null' in response_data
        assert '"longitude":null' in response_data
        assert '"altitude":null' in response_data

    @patch('use_cases.list_plots_use_case.get_state')
    @patch('use_cases.list_plots_use_case.get_user_role_ids')
    def test_list_plots_with_empty_user_role_ids(self, mock_get_user_role_ids, mock_get_state):
        """Prueba cuando el usuario no tiene roles asociados"""
        # Arrange
        farm_id = 1
        
        # Mock get_state calls
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state,
            self.active_plot_state
        ]
        
        # Mock user service calls
        mock_get_user_role_ids.return_value = []  # Empty user role ids
        
        # Mock database queries
        query_mock = Mock()
        filter_mock = Mock()
        
        self.db_mock.query.return_value = query_mock
        query_mock.filter.return_value = filter_mock
        filter_mock.first.side_effect = [
            self.farm_mock,  # farm found
            None  # user_role_farm not found due to empty user_role_ids
        ]
        
        # Act
        result = list_plots(farm_id, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 200
        response_data = result.body.decode()
        assert '"status":"error"' in response_data
        assert '"message":"No tienes permiso para ver los lotes de esta finca"' in response_data

    @patch('use_cases.list_plots_use_case.get_state')
    @patch('use_cases.list_plots_use_case.get_user_role_ids')
    @patch('use_cases.list_plots_use_case.get_role_permissions_for_user_role')
    def test_list_plots_with_empty_permissions_list(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Prueba cuando el rol no tiene permisos asociados"""
        # Arrange
        farm_id = 1
        
        # Mock get_state calls
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state,
            self.active_plot_state
        ]
        
        # Mock user service calls
        mock_get_user_role_ids.return_value = [1, 2, 3]
        mock_get_permissions.return_value = []  # Empty permissions list
        
        # Mock database queries
        query_mock = Mock()
        filter_mock = Mock()
        
        self.db_mock.query.return_value = query_mock
        query_mock.filter.return_value = filter_mock
        filter_mock.first.side_effect = [
            self.farm_mock,  # farm found
            self.user_role_farm_mock  # user_role_farm found
        ]
        
        # Act
        result = list_plots(farm_id, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 200
        response_data = result.body.decode()
        assert '"status":"error"' in response_data
        assert '"message":"No tienes permiso para ver los lotes de esta finca"' in response_data