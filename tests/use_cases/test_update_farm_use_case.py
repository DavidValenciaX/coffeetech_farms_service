"""
Pruebas unitarias para update_farm_use_case.py
"""
import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from decimal import Decimal
from fastapi import HTTPException

from use_cases.update_farm_use_case import update_farm


class TestUpdateFarmUseCase:
    """Clase de pruebas para el caso de uso de actualización de finca"""
    
    def setup_method(self):
        """Configuración inicial para cada prueba"""
        self.db_mock = Mock(spec=Session)
        self.user_mock = Mock()
        self.user_mock.user_id = "test_user_id"
        
        # Mock request object
        self.request_mock = Mock()
        self.request_mock.farm_id = 1
        self.request_mock.name = "Updated Farm"
        self.request_mock.area = Decimal("10.5")
        self.request_mock.area_unit_id = 1
        
        # Mock states
        self.active_farm_state = Mock()
        self.active_farm_state.farm_state_id = 1
        
        self.active_urf_state = Mock()
        self.active_urf_state.user_role_farm_state_id = 1
        
        # Mock area unit
        self.area_unit_mock = Mock()
        self.area_unit_mock.area_unit_id = 1
        self.area_unit_mock.name = "Hectáreas"
        
        # Mock farm
        self.farm_mock = Mock()
        self.farm_mock.farm_id = 1
        self.farm_mock.name = "Original Farm"
        self.farm_mock.area = Decimal("5.0")
        self.farm_mock.area_unit_id = 1
        
        # Mock user role farm
        self.user_role_farm_mock = Mock()
        self.user_role_farm_mock.user_role_id = 1
        self.user_role_farm_mock.farm_id = 1

    @patch('use_cases.update_farm_use_case.get_state')
    @patch('use_cases.update_farm_use_case.get_user_role_ids')
    @patch('use_cases.update_farm_use_case.get_role_permissions_for_user_role')
    def test_update_farm_success(self, mock_permissions, mock_user_role_ids, mock_get_state):
        """Test successful farm update"""
        # Setup mocks
        mock_get_state.side_effect = [self.active_farm_state, self.active_urf_state]
        mock_user_role_ids.return_value = [1]
        mock_permissions.return_value = ["edit_farm"]
        
        # Setup database queries
        self.db_mock.query.return_value.join.return_value.filter.return_value.first.return_value = self.user_role_farm_mock
        
        # Mock area unit query
        area_unit_query = Mock()
        area_unit_query.filter.return_value.first.return_value = self.area_unit_mock
        
        # Mock farm query
        farm_query = Mock()
        farm_query.filter.return_value.first.return_value = self.farm_mock
        
        # Mock existing farm query (no duplicate)
        existing_farm_query = Mock()
        existing_farm_query.join.return_value.filter.return_value.first.return_value = None
        
        self.db_mock.query.side_effect = [
            Mock(join=Mock(return_value=Mock(filter=Mock(return_value=Mock(first=Mock(return_value=self.user_role_farm_mock)))))),
            area_unit_query,
            farm_query,
            existing_farm_query
        ]
        
        # Execute
        result = update_farm(self.request_mock, self.user_mock, self.db_mock)
        
        # Verify
        assert result.status_code == 200
        self.db_mock.commit.assert_called_once()
        self.db_mock.refresh.assert_called_once_with(self.farm_mock)
        assert self.farm_mock.name == "Updated Farm"
        assert self.farm_mock.area == Decimal("10.5")
        assert self.farm_mock.area_unit_id == 1

    @patch('use_cases.update_farm_use_case.get_state')
    @patch('use_cases.update_farm_use_case.get_user_role_ids')
    @patch('use_cases.update_farm_use_case.get_role_permissions_for_user_role')
    def test_update_farm_not_found(self, mock_permissions, mock_user_role_ids, mock_get_state):
        """Test farm not found scenario"""
        # Setup mocks
        mock_get_state.side_effect = [self.active_farm_state, self.active_urf_state]
        mock_user_role_ids.return_value = [1]
        mock_permissions.return_value = ["edit_farm"]
        
        # Setup database queries - farm not found
        self.db_mock.query.return_value.join.return_value.filter.return_value.first.return_value = self.user_role_farm_mock
        
        area_unit_query = Mock()
        area_unit_query.filter.return_value.first.return_value = self.area_unit_mock
        
        farm_query = Mock()
        farm_query.filter.return_value.first.return_value = None  # Farm not found
        
        self.db_mock.query.side_effect = [
            Mock(join=Mock(return_value=Mock(filter=Mock(return_value=Mock(first=Mock(return_value=self.user_role_farm_mock)))))),
            area_unit_query,
            farm_query
        ]
        
        # Execute
        result = update_farm(self.request_mock, self.user_mock, self.db_mock)
        
        # Verify
        assert result.status_code == 200
        response_data = result.body.decode()
        assert "Finca no encontrada" in response_data

    @patch('use_cases.update_farm_use_case.get_state')
    @patch('use_cases.update_farm_use_case.get_user_role_ids')
    @patch('use_cases.update_farm_use_case.get_role_permissions_for_user_role')
    def test_update_farm_empty_name(self, mock_permissions, mock_user_role_ids, mock_get_state):
        """Test empty farm name validation"""
        # Setup mocks
        mock_get_state.side_effect = [self.active_farm_state, self.active_urf_state]
        mock_user_role_ids.return_value = [1]
        mock_permissions.return_value = ["edit_farm"]
        
        self.db_mock.query.return_value.join.return_value.filter.return_value.first.return_value = self.user_role_farm_mock
        
        # Set empty name
        self.request_mock.name = ""
        
        # Execute
        result = update_farm(self.request_mock, self.user_mock, self.db_mock)
        
        # Verify
        assert result.status_code == 200
        response_data = result.body.decode()
        assert "El nombre de la finca no puede estar vacío" in response_data

    @patch('use_cases.update_farm_use_case.get_state')
    @patch('use_cases.update_farm_use_case.get_user_role_ids')
    @patch('use_cases.update_farm_use_case.get_role_permissions_for_user_role')
    def test_update_farm_name_too_long(self, mock_permissions, mock_user_role_ids, mock_get_state):
        """Test farm name too long validation"""
        # Setup mocks
        mock_get_state.side_effect = [self.active_farm_state, self.active_urf_state]
        mock_user_role_ids.return_value = [1]
        mock_permissions.return_value = ["edit_farm"]
        
        self.db_mock.query.return_value.join.return_value.filter.return_value.first.return_value = self.user_role_farm_mock
        
        # Set name too long (>50 characters)
        self.request_mock.name = "A" * 51
        
        # Execute
        result = update_farm(self.request_mock, self.user_mock, self.db_mock)
        
        # Verify
        assert result.status_code == 200
        response_data = result.body.decode()
        assert "El nombre de la finca no puede tener más de 50 caracteres" in response_data

    @patch('use_cases.update_farm_use_case.get_state')
    @patch('use_cases.update_farm_use_case.get_user_role_ids')
    @patch('use_cases.update_farm_use_case.get_role_permissions_for_user_role')
    def test_update_farm_negative_area(self, mock_permissions, mock_user_role_ids, mock_get_state):
        """Test negative area validation"""
        # Setup mocks
        mock_get_state.side_effect = [self.active_farm_state, self.active_urf_state]
        mock_user_role_ids.return_value = [1]
        mock_permissions.return_value = ["edit_farm"]
        
        self.db_mock.query.return_value.join.return_value.filter.return_value.first.return_value = self.user_role_farm_mock
        
        # Set negative area
        self.request_mock.area = Decimal("-5.0")
        
        # Execute
        result = update_farm(self.request_mock, self.user_mock, self.db_mock)
        
        # Verify
        assert result.status_code == 200
        response_data = result.body.decode()
        assert "El área de la finca debe ser un número positivo mayor que cero" in response_data

    @patch('use_cases.update_farm_use_case.get_state')
    @patch('use_cases.update_farm_use_case.get_user_role_ids')
    @patch('use_cases.update_farm_use_case.get_role_permissions_for_user_role')
    def test_update_farm_zero_area(self, mock_permissions, mock_user_role_ids, mock_get_state):
        """Test zero area validation"""
        # Setup mocks
        mock_get_state.side_effect = [self.active_farm_state, self.active_urf_state]
        mock_user_role_ids.return_value = [1]
        mock_permissions.return_value = ["edit_farm"]
        
        self.db_mock.query.return_value.join.return_value.filter.return_value.first.return_value = self.user_role_farm_mock
        
        # Set zero area
        self.request_mock.area = Decimal("0")
        
        # Execute
        result = update_farm(self.request_mock, self.user_mock, self.db_mock)
        
        # Verify
        assert result.status_code == 200
        response_data = result.body.decode()
        assert "El área de la finca debe ser un número positivo mayor que cero" in response_data

    @patch('use_cases.update_farm_use_case.get_state')
    @patch('use_cases.update_farm_use_case.get_user_role_ids')
    @patch('use_cases.update_farm_use_case.get_role_permissions_for_user_role')
    def test_update_farm_invalid_area_unit(self, mock_permissions, mock_user_role_ids, mock_get_state):
        """Test invalid area unit validation"""
        # Setup mocks
        mock_get_state.side_effect = [self.active_farm_state, self.active_urf_state]
        mock_user_role_ids.return_value = [1]
        mock_permissions.return_value = ["edit_farm"]
        
        self.db_mock.query.return_value.join.return_value.filter.return_value.first.return_value = self.user_role_farm_mock
        
        # Mock area unit query - not found
        area_unit_query = Mock()
        area_unit_query.filter.return_value.first.return_value = None
        
        self.db_mock.query.side_effect = [
            Mock(join=Mock(return_value=Mock(filter=Mock(return_value=Mock(first=Mock(return_value=self.user_role_farm_mock)))))),
            area_unit_query
        ]
        
        # Execute
        result = update_farm(self.request_mock, self.user_mock, self.db_mock)
        
        # Verify
        assert result.status_code == 200
        response_data = result.body.decode()
        assert "Unidad de medida no válida" in response_data

    @patch('use_cases.update_farm_use_case.get_state')
    @patch('use_cases.update_farm_use_case.get_user_role_ids')
    @patch('use_cases.update_farm_use_case.get_role_permissions_for_user_role')
    def test_update_farm_duplicate_name(self, mock_permissions, mock_user_role_ids, mock_get_state):
        """Test duplicate farm name validation"""
        # Setup mocks
        mock_get_state.side_effect = [self.active_farm_state, self.active_urf_state]
        mock_user_role_ids.return_value = [1]
        mock_permissions.return_value = ["edit_farm"]
        
        self.db_mock.query.return_value.join.return_value.filter.return_value.first.return_value = self.user_role_farm_mock
        
        area_unit_query = Mock()
        area_unit_query.filter.return_value.first.return_value = self.area_unit_mock
        
        farm_query = Mock()
        farm_query.filter.return_value.first.return_value = self.farm_mock
        
        # Mock existing farm query - duplicate found
        existing_farm_mock = Mock()
        existing_farm_query = Mock()
        existing_farm_query.join.return_value.filter.return_value.first.return_value = existing_farm_mock
        
        self.db_mock.query.side_effect = [
            Mock(join=Mock(return_value=Mock(filter=Mock(return_value=Mock(first=Mock(return_value=self.user_role_farm_mock)))))),
            area_unit_query,
            farm_query,
            existing_farm_query
        ]
        
        # Execute
        result = update_farm(self.request_mock, self.user_mock, self.db_mock)
        
        # Verify
        assert result.status_code == 200
        response_data = result.body.decode()
        assert "El nombre de la finca ya está en uso por otra finca del propietario" in response_data

    @patch('use_cases.update_farm_use_case.get_state')
    @patch('use_cases.update_farm_use_case.get_user_role_ids')
    def test_update_farm_no_permission(self, mock_user_role_ids, mock_get_state):
        """Test user has no permission to edit farm"""
        # Setup mocks
        mock_get_state.side_effect = [self.active_farm_state, self.active_urf_state]
        mock_user_role_ids.return_value = [1]
        
        # User not associated with farm
        self.db_mock.query.return_value.join.return_value.filter.return_value.first.return_value = None
        
        # Execute
        result = update_farm(self.request_mock, self.user_mock, self.db_mock)
        
        # Verify
        assert result.status_code == 200
        response_data = result.body.decode()
        assert "No tienes permiso para editar esta finca porque no estás asociado con una finca activa" in response_data

    @patch('use_cases.update_farm_use_case.get_state')
    @patch('use_cases.update_farm_use_case.get_user_role_ids')
    @patch('use_cases.update_farm_use_case.get_role_permissions_for_user_role')
    def test_update_farm_insufficient_role_permissions(self, mock_permissions, mock_user_role_ids, mock_get_state):
        """Test user role doesn't have edit_farm permission"""
        # Setup mocks
        mock_get_state.side_effect = [self.active_farm_state, self.active_urf_state]
        mock_user_role_ids.return_value = [1]
        mock_permissions.return_value = ["view_farm"]  # No edit permission
        
        self.db_mock.query.return_value.join.return_value.filter.return_value.first.return_value = self.user_role_farm_mock
        
        # Execute
        result = update_farm(self.request_mock, self.user_mock, self.db_mock)
        
        # Verify
        assert result.status_code == 200
        response_data = result.body.decode()
        assert "No tienes permiso para editar esta finca" in response_data

    @patch('use_cases.update_farm_use_case.get_state')
    @patch('use_cases.update_farm_use_case.get_user_role_ids')
    def test_update_farm_user_service_error(self, mock_user_role_ids, mock_get_state):
        """Test error when calling user service"""
        # Setup mocks
        mock_get_state.side_effect = [self.active_farm_state, self.active_urf_state]
        mock_user_role_ids.side_effect = Exception("User service error")
        
        # Execute
        result = update_farm(self.request_mock, self.user_mock, self.db_mock)
        
        # Verify
        assert result.status_code == 500
        response_data = result.body.decode()
        assert "No se pudieron obtener los roles del usuario" in response_data

    @patch('use_cases.update_farm_use_case.get_state')
    @patch('use_cases.update_farm_use_case.get_user_role_ids')
    @patch('use_cases.update_farm_use_case.get_role_permissions_for_user_role')
    def test_update_farm_permissions_service_error(self, mock_permissions, mock_user_role_ids, mock_get_state):
        """Test error when getting role permissions"""
        # Setup mocks
        mock_get_state.side_effect = [self.active_farm_state, self.active_urf_state]
        mock_user_role_ids.return_value = [1]
        mock_permissions.side_effect = Exception("Permissions service error")
        
        self.db_mock.query.return_value.join.return_value.filter.return_value.first.return_value = self.user_role_farm_mock
        
        # Execute
        result = update_farm(self.request_mock, self.user_mock, self.db_mock)
        
        # Verify
        assert result.status_code == 500
        response_data = result.body.decode()
        assert "No se pudieron obtener los permisos del rol" in response_data

    @patch('use_cases.update_farm_use_case.get_state')
    @patch('use_cases.update_farm_use_case.get_user_role_ids')
    @patch('use_cases.update_farm_use_case.get_role_permissions_for_user_role')
    def test_update_farm_database_error(self, mock_permissions, mock_user_role_ids, mock_get_state):
        """Test database error during farm update"""
        # Setup mocks
        mock_get_state.side_effect = [self.active_farm_state, self.active_urf_state]
        mock_user_role_ids.return_value = [1]
        mock_permissions.return_value = ["edit_farm"]
        
        self.db_mock.query.return_value.join.return_value.filter.return_value.first.return_value = self.user_role_farm_mock
        
        area_unit_query = Mock()
        area_unit_query.filter.return_value.first.return_value = self.area_unit_mock
        
        farm_query = Mock()
        farm_query.filter.return_value.first.return_value = self.farm_mock
        
        existing_farm_query = Mock()
        existing_farm_query.join.return_value.filter.return_value.first.return_value = None
        
        self.db_mock.query.side_effect = [
            Mock(join=Mock(return_value=Mock(filter=Mock(return_value=Mock(first=Mock(return_value=self.user_role_farm_mock)))))),
            area_unit_query,
            farm_query,
            existing_farm_query
        ]
        
        # Simulate database error on commit
        self.db_mock.commit.side_effect = Exception("Database error")
        
        # Execute and verify exception is raised
        with pytest.raises(HTTPException) as exc_info:
            update_farm(self.request_mock, self.user_mock, self.db_mock)
        
        assert exc_info.value.status_code == 500
        assert "Error al actualizar la finca" in str(exc_info.value.detail)
        self.db_mock.rollback.assert_called_once()

    @patch('use_cases.update_farm_use_case.get_state')
    @patch('use_cases.update_farm_use_case.get_user_role_ids')
    @patch('use_cases.update_farm_use_case.get_role_permissions_for_user_role')
    def test_update_farm_whitespace_only_name(self, mock_permissions, mock_user_role_ids, mock_get_state):
        """Test farm name with only whitespace"""
        # Setup mocks
        mock_get_state.side_effect = [self.active_farm_state, self.active_urf_state]
        mock_user_role_ids.return_value = [1]
        mock_permissions.return_value = ["edit_farm"]
        
        self.db_mock.query.return_value.join.return_value.filter.return_value.first.return_value = self.user_role_farm_mock
        
        # Set name with only whitespace
        self.request_mock.name = "   "
        
        # Execute
        result = update_farm(self.request_mock, self.user_mock, self.db_mock)
        
        # Verify
        assert result.status_code == 200
        response_data = result.body.decode()
        assert "El nombre de la finca no puede estar vacío" in response_data

    @patch('use_cases.update_farm_use_case.get_state')
    @patch('use_cases.update_farm_use_case.get_user_role_ids')
    @patch('use_cases.update_farm_use_case.get_role_permissions_for_user_role')
    def test_update_farm_same_name_no_duplicate_check(self, mock_permissions, mock_user_role_ids, mock_get_state):
        """Test updating farm with same name doesn't trigger duplicate check"""
        # Setup mocks
        mock_get_state.side_effect = [self.active_farm_state, self.active_urf_state]
        mock_user_role_ids.return_value = [1]
        mock_permissions.return_value = ["edit_farm"]
        
        self.db_mock.query.return_value.join.return_value.filter.return_value.first.return_value = self.user_role_farm_mock
        
        area_unit_query = Mock()
        area_unit_query.filter.return_value.first.return_value = self.area_unit_mock
        
        farm_query = Mock()
        farm_query.filter.return_value.first.return_value = self.farm_mock
        
        # Set same name as current farm
        self.request_mock.name = "Original Farm"
        
        self.db_mock.query.side_effect = [
            Mock(join=Mock(return_value=Mock(filter=Mock(return_value=Mock(first=Mock(return_value=self.user_role_farm_mock)))))),
            area_unit_query,
            farm_query
        ]
        
        # Execute
        result = update_farm(self.request_mock, self.user_mock, self.db_mock)
        
        # Verify success (no duplicate check performed)
        assert result.status_code == 200
        self.db_mock.commit.assert_called_once() 