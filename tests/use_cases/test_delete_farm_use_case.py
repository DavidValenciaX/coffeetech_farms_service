"""
Pruebas unitarias para delete_farm_use_case.py
"""
import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from fastapi import HTTPException

from use_cases.delete_farm_use_case import delete_farm


class TestDeleteFarmUseCase:
    """Clase de pruebas para el caso de uso de eliminación de finca"""
    
    def setup_method(self):
        """Configuración inicial para cada prueba"""
        self.db_mock = Mock(spec=Session)
        self.user_mock = Mock()
        self.user_mock.user_id = "test_user_id"
        
        # Mock states
        self.active_farm_state = Mock()
        self.active_farm_state.farm_state_id = 1
        
        self.inactive_farm_state = Mock()
        self.inactive_farm_state.farm_state_id = 2
        
        self.active_urf_state = Mock()
        self.active_urf_state.user_role_farm_state_id = 1
        
        self.inactive_urf_state = Mock()
        self.inactive_urf_state.user_role_farm_state_id = 2
        
        # Mock farm
        self.farm_mock = Mock()
        self.farm_mock.farm_id = 1
        self.farm_mock.farm_state_id = 1
        
        # Mock user_role_farm
        self.user_role_farm_mock = Mock()
        self.user_role_farm_mock.user_role_id = 123
        self.user_role_farm_mock.farm_id = 1
        self.user_role_farm_mock.user_role_farm_state_id = 1

    @patch('use_cases.delete_farm_use_case.get_state')
    @patch('use_cases.delete_farm_use_case.get_user_role_ids')
    @patch('use_cases.delete_farm_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.delete_farm_use_case.create_response')
    def test_delete_farm_success(self, mock_create_response, mock_get_permissions, 
                                mock_get_user_role_ids, mock_get_state):
        """Prueba la eliminación exitosa de una finca"""
        # Arrange
        farm_id = 1
        
        # Mock get_state calls
        mock_get_state.side_effect = [
            self.active_farm_state,    # active_farm_state
            self.active_urf_state,     # active_urf_state
            self.inactive_farm_state,  # inactive_farm_state
            self.inactive_urf_state    # inactive_urf_state
        ]
        
        # Mock user service calls
        mock_get_user_role_ids.return_value = [123]
        mock_get_permissions.return_value = ["delete_farm"]
        
        # Mock database queries
        query_mock = Mock()
        self.db_mock.query.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = self.user_role_farm_mock
        query_mock.all.return_value = [self.user_role_farm_mock]
        
        # Mock farm query
        farm_query_mock = Mock()
        self.db_mock.query.side_effect = [query_mock, farm_query_mock, query_mock]
        farm_query_mock.filter.return_value = farm_query_mock
        farm_query_mock.first.return_value = self.farm_mock
        
        mock_create_response.return_value = {"status": "success", "message": "Finca puesta en estado 'Inactivo' correctamente"}
        
        # Act
        result = delete_farm(farm_id, self.user_mock, self.db_mock)
        
        # Assert
        mock_get_user_role_ids.assert_called_once_with(self.user_mock.user_id)
        mock_get_permissions.assert_called_once_with(123)
        self.db_mock.commit.assert_called_once()
        assert self.farm_mock.farm_state_id == self.inactive_farm_state.farm_state_id
        assert self.user_role_farm_mock.user_role_farm_state_id == self.inactive_urf_state.user_role_farm_state_id
        mock_create_response.assert_called_with("success", "Finca puesta en estado 'Inactivo' correctamente")
        assert result == {"status": "success", "message": "Finca puesta en estado 'Inactivo' correctamente"}

    @patch('use_cases.delete_farm_use_case.get_state')
    @patch('use_cases.delete_farm_use_case.get_user_role_ids')
    @patch('use_cases.delete_farm_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.delete_farm_use_case.create_response')
    def test_delete_farm_not_found(self, mock_create_response, mock_get_permissions, 
                                  mock_get_user_role_ids, mock_get_state):
        """Prueba cuando la finca no existe"""
        # Arrange
        farm_id = 999
        
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state
        ]
        
        mock_get_user_role_ids.return_value = [123]
        mock_get_permissions.return_value = ["delete_farm"]
        
        # Mock user_role_farm query
        query_mock = Mock()
        self.db_mock.query.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = self.user_role_farm_mock
        
        # Mock farm query - farm not found
        farm_query_mock = Mock()
        self.db_mock.query.side_effect = [query_mock, farm_query_mock]
        farm_query_mock.filter.return_value = farm_query_mock
        farm_query_mock.first.return_value = None
        
        mock_create_response.return_value = {"status": "error", "message": "Finca no encontrada"}
        
        # Act
        result = delete_farm(farm_id, self.user_mock, self.db_mock)
        
        # Assert
        mock_create_response.assert_called_with("error", "Finca no encontrada")
        self.db_mock.commit.assert_not_called()
        assert result == {"status": "error", "message": "Finca no encontrada"}

    @patch('use_cases.delete_farm_use_case.get_state')
    @patch('use_cases.delete_farm_use_case.get_user_role_ids')
    @patch('use_cases.delete_farm_use_case.create_response')
    def test_delete_farm_no_permission_user_not_associated(self, mock_create_response, 
                                                          mock_get_user_role_ids, mock_get_state):
        """Prueba cuando el usuario no está asociado con la finca"""
        # Arrange
        farm_id = 1
        
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state
        ]
        
        mock_get_user_role_ids.return_value = [123]
        
        # Mock database query - no user_role_farm found
        query_mock = Mock()
        self.db_mock.query.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = None
        
        mock_create_response.return_value = {"status": "error", "message": "No tienes permiso para eliminar esta finca"}
        
        # Act
        result = delete_farm(farm_id, self.user_mock, self.db_mock)
        
        # Assert
        mock_create_response.assert_called_with("error", "No tienes permiso para eliminar esta finca")
        self.db_mock.commit.assert_not_called()
        assert result == {"status": "error", "message": "No tienes permiso para eliminar esta finca"}

    @patch('use_cases.delete_farm_use_case.get_state')
    @patch('use_cases.delete_farm_use_case.get_user_role_ids')
    @patch('use_cases.delete_farm_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.delete_farm_use_case.create_response')
    def test_delete_farm_no_permission_insufficient_role(self, mock_create_response, mock_get_permissions, 
                                                        mock_get_user_role_ids, mock_get_state):
        """Prueba cuando el usuario no tiene permisos para eliminar la finca"""
        # Arrange
        farm_id = 1
        
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state
        ]
        
        mock_get_user_role_ids.return_value = [123]
        mock_get_permissions.return_value = ["read_farm", "update_farm"]  # No delete_farm permission
        
        # Mock database query
        query_mock = Mock()
        self.db_mock.query.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = self.user_role_farm_mock
        
        mock_create_response.return_value = {"status": "error", "message": "No tienes permiso para eliminar esta finca"}
        
        # Act
        result = delete_farm(farm_id, self.user_mock, self.db_mock)
        
        # Assert
        mock_get_permissions.assert_called_once_with(123)
        mock_create_response.assert_called_with("error", "No tienes permiso para eliminar esta finca")
        self.db_mock.commit.assert_not_called()
        assert result == {"status": "error", "message": "No tienes permiso para eliminar esta finca"}

    @patch('use_cases.delete_farm_use_case.get_state')
    @patch('use_cases.delete_farm_use_case.get_user_role_ids')
    @patch('use_cases.delete_farm_use_case.create_response')
    def test_delete_farm_user_service_error_get_user_role_ids(self, mock_create_response, 
                                                             mock_get_user_role_ids, mock_get_state):
        """Prueba error al obtener user_role_ids del microservicio de usuarios"""
        # Arrange
        farm_id = 1
        
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state
        ]
        
        mock_get_user_role_ids.side_effect = Exception("User service error")
        mock_create_response.return_value = {"status": "error", "message": "No se pudieron obtener los roles del usuario", "status_code": 500}
        
        # Act
        result = delete_farm(farm_id, self.user_mock, self.db_mock)
        
        # Assert
        mock_create_response.assert_called_with("error", "No se pudieron obtener los roles del usuario", status_code=500)
        self.db_mock.commit.assert_not_called()
        assert result == {"status": "error", "message": "No se pudieron obtener los roles del usuario", "status_code": 500}

    @patch('use_cases.delete_farm_use_case.get_state')
    @patch('use_cases.delete_farm_use_case.get_user_role_ids')
    @patch('use_cases.delete_farm_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.delete_farm_use_case.create_response')
    def test_delete_farm_user_service_error_get_permissions(self, mock_create_response, mock_get_permissions, 
                                                           mock_get_user_role_ids, mock_get_state):
        """Prueba error al obtener permisos del microservicio de usuarios"""
        # Arrange
        farm_id = 1
        
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state
        ]
        
        mock_get_user_role_ids.return_value = [123]
        mock_get_permissions.side_effect = Exception("Permission service error")
        
        # Mock database query
        query_mock = Mock()
        self.db_mock.query.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = self.user_role_farm_mock
        
        mock_create_response.return_value = {"status": "error", "message": "No se pudieron obtener los permisos del rol", "status_code": 500}
        
        # Act
        result = delete_farm(farm_id, self.user_mock, self.db_mock)
        
        # Assert
        mock_create_response.assert_called_with("error", "No se pudieron obtener los permisos del rol", status_code=500)
        self.db_mock.commit.assert_not_called()
        assert result == {"status": "error", "message": "No se pudieron obtener los permisos del rol", "status_code": 500}

    @patch('use_cases.delete_farm_use_case.get_state')
    @patch('use_cases.delete_farm_use_case.get_user_role_ids')
    @patch('use_cases.delete_farm_use_case.get_role_permissions_for_user_role')
    def test_delete_farm_database_error(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Prueba error de base de datos durante la eliminación"""
        # Arrange
        farm_id = 1
        
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state,
            self.inactive_farm_state,
            self.inactive_urf_state
        ]
        
        mock_get_user_role_ids.return_value = [123]
        mock_get_permissions.return_value = ["delete_farm"]
        
        # Mock database queries
        query_mock = Mock()
        self.db_mock.query.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = self.user_role_farm_mock
        query_mock.all.return_value = [self.user_role_farm_mock]
        
        # Mock farm query
        farm_query_mock = Mock()
        self.db_mock.query.side_effect = [query_mock, farm_query_mock, query_mock]
        farm_query_mock.filter.return_value = farm_query_mock
        farm_query_mock.first.return_value = self.farm_mock
        
        # Mock database error on commit
        self.db_mock.commit.side_effect = Exception("Database error")
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            delete_farm(farm_id, self.user_mock, self.db_mock)
        
        assert exc_info.value.status_code == 500
        assert "Error al desactivar la finca" in str(exc_info.value.detail)
        self.db_mock.rollback.assert_called_once()

    @patch('use_cases.delete_farm_use_case.get_state')
    @patch('use_cases.delete_farm_use_case.create_response')
    def test_delete_farm_missing_active_farm_state(self, mock_create_response, mock_get_state):
        """Prueba cuando no se encuentra el estado 'Activo' para Farms"""
        # Arrange
        farm_id = 1
        
        mock_get_state.side_effect = [None]  # active_farm_state not found
        mock_create_response.return_value = {"status": "error", "message": "Estado 'Activo' no encontrado para Farms", "status_code": 400}
        
        # Act
        result = delete_farm(farm_id, self.user_mock, self.db_mock)
        
        # Assert
        mock_create_response.assert_called_with("error", "Estado 'Activo' no encontrado para Farms", status_code=400)
        self.db_mock.commit.assert_not_called()
        assert result == {"status": "error", "message": "Estado 'Activo' no encontrado para Farms", "status_code": 400}

    @patch('use_cases.delete_farm_use_case.get_state')
    @patch('use_cases.delete_farm_use_case.create_response')
    def test_delete_farm_missing_active_urf_state(self, mock_create_response, mock_get_state):
        """Prueba cuando no se encuentra el estado 'Activo' para user_role_farm"""
        # Arrange
        farm_id = 1
        
        mock_get_state.side_effect = [
            self.active_farm_state,
            None  # active_urf_state not found
        ]
        mock_create_response.return_value = {"status": "error", "message": "Estado 'Activo' no encontrado para user_role_farm", "status_code": 400}
        
        # Act
        result = delete_farm(farm_id, self.user_mock, self.db_mock)
        
        # Assert
        mock_create_response.assert_called_with("error", "Estado 'Activo' no encontrado para user_role_farm", status_code=400)
        self.db_mock.commit.assert_not_called()
        assert result == {"status": "error", "message": "Estado 'Activo' no encontrado para user_role_farm", "status_code": 400}

    @patch('use_cases.delete_farm_use_case.get_state')
    @patch('use_cases.delete_farm_use_case.get_user_role_ids')
    @patch('use_cases.delete_farm_use_case.get_role_permissions_for_user_role')
    def test_delete_farm_missing_inactive_farm_state(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Prueba cuando no se encuentra el estado 'Inactivo' para Farms"""
        # Arrange
        farm_id = 1
        
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state,
            None  # inactive_farm_state not found
        ]
        
        mock_get_user_role_ids.return_value = [123]
        mock_get_permissions.return_value = ["delete_farm"]
        
        # Mock database queries
        query_mock = Mock()
        self.db_mock.query.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = self.user_role_farm_mock
        
        # Mock farm query
        farm_query_mock = Mock()
        self.db_mock.query.side_effect = [query_mock, farm_query_mock]
        farm_query_mock.filter.return_value = farm_query_mock
        farm_query_mock.first.return_value = self.farm_mock
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            delete_farm(farm_id, self.user_mock, self.db_mock)
        
        assert exc_info.value.status_code == 500
        assert "No se encontró el estado 'Inactivo' para el tipo 'Farms'" in str(exc_info.value.detail)

    @patch('use_cases.delete_farm_use_case.get_state')
    @patch('use_cases.delete_farm_use_case.get_user_role_ids')
    @patch('use_cases.delete_farm_use_case.get_role_permissions_for_user_role')
    def test_delete_farm_missing_inactive_urf_state(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Prueba cuando no se encuentra el estado 'Inactivo' para user_role_farm"""
        # Arrange
        farm_id = 1
        
        mock_get_state.side_effect = [
            self.active_farm_state,
            self.active_urf_state,
            self.inactive_farm_state,
            None  # inactive_urf_state not found
        ]
        
        mock_get_user_role_ids.return_value = [123]
        mock_get_permissions.return_value = ["delete_farm"]
        
        # Mock database queries
        query_mock = Mock()
        self.db_mock.query.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = self.user_role_farm_mock
        
        # Mock farm query
        farm_query_mock = Mock()
        self.db_mock.query.side_effect = [query_mock, farm_query_mock]
        farm_query_mock.filter.return_value = farm_query_mock
        farm_query_mock.first.return_value = self.farm_mock
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            delete_farm(farm_id, self.user_mock, self.db_mock)
        
        assert exc_info.value.status_code == 500
        assert "No se encontró el estado 'Inactivo' para el tipo 'user_role_farm'" in str(exc_info.value.detail) 