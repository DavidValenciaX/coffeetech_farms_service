"""
Pruebas unitarias para create_farm_use_case.py
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session
from fastapi import HTTPException
from decimal import Decimal

from use_cases.create_farm_use_case import create_farm


class TestCreateFarmUseCase:
    """Clase de pruebas para el caso de uso de creación de fincas"""
    
    def setup_method(self):
        """Configuración inicial para cada prueba"""
        self.db_mock = Mock(spec=Session)
        self.user_mock = Mock()
        self.user_mock.user_id = "test_user_id"
        
        # Mock request object
        self.request_mock = Mock()
        self.request_mock.name = "Test Farm"
        self.request_mock.area = 100.5
        self.request_mock.area_unit_id = 1
        
        # Mock states
        self.active_farm_state_mock = Mock()
        self.active_farm_state_mock.farm_state_id = 1
        
        self.active_urf_state_mock = Mock()
        self.active_urf_state_mock.user_role_farm_state_id = 1
        
        # Mock area unit
        self.area_unit_mock = Mock()
        self.area_unit_mock.area_unit_id = 1
        self.area_unit_mock.name = "Hectáreas"
        
        # Mock farm
        self.farm_mock = Mock()
        self.farm_mock.farm_id = 1
        self.farm_mock.name = "Test Farm"
        self.farm_mock.area = Decimal('100.5')
    
    @patch('use_cases.create_farm_use_case.get_state')
    @patch('use_cases.create_farm_use_case.get_user_role_ids')
    @patch('use_cases.create_farm_use_case.create_user_role')
    def test_create_farm_success(self, mock_create_user_role, mock_get_user_role_ids, mock_get_state):
        """Test successful farm creation"""
        # Arrange
        mock_get_state.side_effect = [self.active_farm_state_mock, self.active_urf_state_mock, 
                                     self.active_farm_state_mock, self.active_urf_state_mock]
        mock_get_user_role_ids.return_value = [1, 2]
        mock_create_user_role.return_value = {"user_role_id": 123}
        
        # Mock database queries
        self.db_mock.query.return_value.join.return_value.filter.return_value.first.return_value = None
        self.db_mock.query.return_value.filter.return_value.first.return_value = self.area_unit_mock
        
        # Mock farm creation
        self.db_mock.add = Mock()
        self.db_mock.commit = Mock()
        self.db_mock.refresh = Mock()
        
        # Act
        result = create_farm(self.request_mock, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 200
        response_data = result.body.decode('utf-8')
        assert '"status":"success"' in response_data
        assert '"message":"Finca creada y usuario asignado correctamente"' in response_data
        
        # Verify database operations
        assert self.db_mock.add.call_count == 2  # Farm and UserRoleFarm
        assert self.db_mock.commit.call_count == 2
        mock_create_user_role.assert_called_once_with("test_user_id", "Propietario")
    
    def test_create_farm_empty_name(self):
        """Test farm creation with empty name"""
        # Arrange
        self.request_mock.name = ""
        
        # Act
        result = create_farm(self.request_mock, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 200
        response_data = result.body.decode('utf-8')
        assert '"status":"error"' in response_data
        assert '"message":"El nombre de la finca no puede estar vacío"' in response_data
    
    def test_create_farm_name_only_spaces(self):
        """Test farm creation with name containing only spaces"""
        # Arrange
        self.request_mock.name = "   "
        
        # Act
        result = create_farm(self.request_mock, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 200
        response_data = result.body.decode('utf-8')
        assert '"status":"error"' in response_data
        assert '"message":"El nombre de la finca no puede estar vacío"' in response_data
    
    def test_create_farm_name_too_long(self):
        """Test farm creation with name exceeding 50 characters"""
        # Arrange
        self.request_mock.name = "a" * 51  # 51 characters
        
        # Act
        result = create_farm(self.request_mock, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 200
        response_data = result.body.decode('utf-8')
        assert '"status":"error"' in response_data
        assert '"message":"El nombre de la finca no puede tener más de 50 caracteres"' in response_data
    
    def test_create_farm_negative_area(self):
        """Test farm creation with negative area"""
        # Arrange
        self.request_mock.area = -10.5
        
        # Act
        result = create_farm(self.request_mock, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 200
        response_data = result.body.decode('utf-8')
        assert '"status":"error"' in response_data
        assert '"message":"El área de la finca debe ser un número positivo mayor que cero"' in response_data
    
    def test_create_farm_zero_area(self):
        """Test farm creation with zero area"""
        # Arrange
        self.request_mock.area = 0
        
        # Act
        result = create_farm(self.request_mock, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 200
        response_data = result.body.decode('utf-8')
        assert '"status":"error"' in response_data
        assert '"message":"El área de la finca debe ser un número positivo mayor que cero"' in response_data
    
    def test_create_farm_area_too_large(self):
        """Test farm creation with area exceeding 10,000 units"""
        # Arrange
        self.request_mock.area = 10001
        
        # Act
        result = create_farm(self.request_mock, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 200
        response_data = result.body.decode('utf-8')
        assert '"status":"error"' in response_data
        assert '"message":"El área de la finca no puede exceder las 10,000 unidades de medida"' in response_data
    
    @patch('use_cases.create_farm_use_case.get_state')
    @patch('use_cases.create_farm_use_case.get_user_role_ids')
    def test_create_farm_invalid_area_unit(self, mock_get_user_role_ids, mock_get_state):
        """Test farm creation with invalid area unit"""
        # Arrange
        mock_get_state.side_effect = [self.active_farm_state_mock, self.active_urf_state_mock]
        mock_get_user_role_ids.return_value = [1, 2]
        
        # Mock database queries - area unit not found
        self.db_mock.query.return_value.join.return_value.filter.return_value.first.return_value = None
        self.db_mock.query.return_value.filter.return_value.first.return_value = None
        
        # Act
        result = create_farm(self.request_mock, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 200
        response_data = result.body.decode('utf-8')
        assert '"status":"error"' in response_data
        assert '"message":"Unidad de medida no válida"' in response_data
    
    @patch('use_cases.create_farm_use_case.get_state')
    @patch('use_cases.create_farm_use_case.get_user_role_ids')
    def test_create_farm_duplicate_name(self, mock_get_user_role_ids, mock_get_state):
        """Test farm creation with duplicate name for the same user"""
        # Arrange
        mock_get_state.side_effect = [self.active_farm_state_mock, self.active_urf_state_mock]
        mock_get_user_role_ids.return_value = [1, 2]
        
        # Mock existing farm found
        existing_farm_mock = Mock()
        existing_farm_mock.name = "Test Farm"
        
        # Mock database queries
        query_mock = Mock()
        join_mock = Mock()
        filter_mock = Mock()
        
        self.db_mock.query.return_value = query_mock
        query_mock.join.return_value = join_mock
        join_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = existing_farm_mock
        
        # Act
        result = create_farm(self.request_mock, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 200
        response_data = result.body.decode('utf-8')
        assert '"status":"error"' in response_data
        assert '"message":"Ya existe una finca activa con el nombre \'Test Farm\' para el propietario"' in response_data
    
    @patch('use_cases.create_farm_use_case.get_state')
    def test_create_farm_missing_active_state(self, mock_get_state):
        """Test farm creation when active farm state is not found"""
        # Arrange
        mock_get_state.return_value = None
        
        # Act
        result = create_farm(self.request_mock, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 400
        response_data = result.body.decode('utf-8')
        assert '"status":"error"' in response_data
        assert '"message":"No se encontró el estado \'Activo\' para el tipo \'Farms\'"' in response_data
    
    @patch('use_cases.create_farm_use_case.get_state')
    @patch('use_cases.create_farm_use_case.get_user_role_ids')
    def test_create_farm_user_service_error(self, mock_get_user_role_ids, mock_get_state):
        """Test farm creation when user service fails"""
        # Arrange
        mock_get_state.side_effect = [self.active_farm_state_mock, self.active_urf_state_mock]
        mock_get_user_role_ids.side_effect = Exception("User service unavailable")
        
        # Act
        result = create_farm(self.request_mock, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 500
        response_data = result.body.decode('utf-8')
        assert '"status":"error"' in response_data
        assert '"message":"No se pudieron obtener los roles del usuario"' in response_data
    
    @patch('use_cases.create_farm_use_case.get_state')
    @patch('use_cases.create_farm_use_case.get_user_role_ids')
    @patch('use_cases.create_farm_use_case.create_user_role')
    def test_create_farm_database_error(self, mock_create_user_role, mock_get_user_role_ids, mock_get_state):
        """Test farm creation when database operation fails"""
        # Arrange
        mock_get_state.side_effect = [self.active_farm_state_mock, self.active_urf_state_mock, 
                                     self.active_farm_state_mock]
        mock_get_user_role_ids.return_value = [1, 2]
        mock_create_user_role.return_value = {"user_role_id": 123}
        
        # Mock database queries
        self.db_mock.query.return_value.join.return_value.filter.return_value.first.return_value = None
        self.db_mock.query.return_value.filter.return_value.first.return_value = self.area_unit_mock
        
        # Mock database error
        self.db_mock.add = Mock()
        self.db_mock.commit.side_effect = Exception("Database connection error")
        self.db_mock.rollback = Mock()
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            create_farm(self.request_mock, self.user_mock, self.db_mock)
        
        assert exc_info.value.status_code == 500
        assert "Error al crear la finca o asignar el usuario" in str(exc_info.value.detail)
        self.db_mock.rollback.assert_called()
    
    @patch('use_cases.create_farm_use_case.get_state')
    def test_create_farm_missing_active_urf_state(self, mock_get_state):
        """Test farm creation when active user_role_farm state is not found"""
        # Arrange
        mock_get_state.side_effect = [self.active_farm_state_mock, None]
        
        # Act
        result = create_farm(self.request_mock, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 400
        response_data = result.body.decode('utf-8')
        assert '"status":"error"' in response_data
        assert '"message":"No se encontró el estado \'Activo\' para el tipo \'user_role_farm\'"' in response_data
    
    @patch('use_cases.create_farm_use_case.get_state')
    @patch('use_cases.create_farm_use_case.get_user_role_ids')
    @patch('use_cases.create_farm_use_case.create_user_role')
    def test_create_farm_user_role_creation_error(self, mock_create_user_role, mock_get_user_role_ids, mock_get_state):
        """Test farm creation when user role creation fails"""
        # Arrange
        mock_get_state.side_effect = [self.active_farm_state_mock, self.active_urf_state_mock, 
                                     self.active_farm_state_mock]
        mock_get_user_role_ids.return_value = [1, 2]
        mock_create_user_role.side_effect = Exception("User role creation failed")
        
        # Mock database queries
        self.db_mock.query.return_value.join.return_value.filter.return_value.first.return_value = None
        self.db_mock.query.return_value.filter.return_value.first.return_value = self.area_unit_mock
        
        # Mock farm creation
        self.db_mock.add = Mock()
        self.db_mock.commit = Mock()
        self.db_mock.refresh = Mock()
        self.db_mock.rollback = Mock()
        
        # Act
        result = create_farm(self.request_mock, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 500
        response_data = result.body.decode('utf-8')
        assert '"status":"error"' in response_data
        assert '"message":"Error al comunicarse con el servicio de usuarios"' in response_data
        self.db_mock.rollback.assert_called()
    
    @patch('use_cases.create_farm_use_case.get_state')
    @patch('use_cases.create_farm_use_case.get_user_role_ids')
    @patch('use_cases.create_farm_use_case.create_user_role')
    def test_create_farm_invalid_user_role_response(self, mock_create_user_role, mock_get_user_role_ids, mock_get_state):
        """Test farm creation when user role creation returns invalid response"""
        # Arrange
        mock_get_state.side_effect = [self.active_farm_state_mock, self.active_urf_state_mock, 
                                     self.active_farm_state_mock]
        mock_get_user_role_ids.return_value = [1, 2]
        mock_create_user_role.return_value = {"invalid": "response"}  # Missing user_role_id
        
        # Mock database queries
        self.db_mock.query.return_value.join.return_value.filter.return_value.first.return_value = None
        self.db_mock.query.return_value.filter.return_value.first.return_value = self.area_unit_mock
        
        # Mock farm creation
        self.db_mock.add = Mock()
        self.db_mock.commit = Mock()
        self.db_mock.refresh = Mock()
        self.db_mock.rollback = Mock()
        
        # Act
        result = create_farm(self.request_mock, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 500
        response_data = result.body.decode('utf-8')
        assert '"status":"error"' in response_data
        assert '"message":"Respuesta inválida del servicio de usuarios al crear UserRole"' in response_data
        self.db_mock.rollback.assert_called()
    
    @patch('use_cases.create_farm_use_case.get_state')
    @patch('use_cases.create_farm_use_case.get_user_role_ids')
    @patch('use_cases.create_farm_use_case.create_user_role')
    def test_create_farm_missing_urf_state_after_farm_creation(self, mock_create_user_role, mock_get_user_role_ids, mock_get_state):
        """Test farm creation when user_role_farm state is missing after farm creation"""
        # Arrange
        mock_get_state.side_effect = [self.active_farm_state_mock, self.active_urf_state_mock, 
                                     self.active_farm_state_mock, None]  # Last call returns None
        mock_get_user_role_ids.return_value = [1, 2]
        mock_create_user_role.return_value = {"user_role_id": 123}
        
        # Mock database queries
        self.db_mock.query.return_value.join.return_value.filter.return_value.first.return_value = None
        self.db_mock.query.return_value.filter.return_value.first.return_value = self.area_unit_mock
        
        # Mock farm creation
        self.db_mock.add = Mock()
        self.db_mock.commit = Mock()
        self.db_mock.refresh = Mock()
        self.db_mock.rollback = Mock()
        
        # Act
        result = create_farm(self.request_mock, self.user_mock, self.db_mock)
        
        # Assert
        assert result.status_code == 400
        response_data = result.body.decode('utf-8')
        assert '"status":"error"' in response_data
        assert '"message":"No se encontró el estado \'Activo\' para el tipo \'user_role_farm\'"' in response_data
        self.db_mock.rollback.assert_called() 