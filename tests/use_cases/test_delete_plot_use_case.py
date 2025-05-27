"""
Pruebas unitarias para delete_plot_use_case.py
"""
import pytest
import json
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from fastapi import HTTPException

from use_cases.delete_plot_use_case import delete_plot


class TestDeletePlotUseCase:
    """Clase de pruebas para el caso de uso de eliminación de lote"""
    
    def setup_method(self):
        """Configuración inicial para cada prueba"""
        self.db_mock = Mock(spec=Session)
        self.user_mock = Mock()
        self.user_mock.user_id = "test_user_id"
        
        # Mock states
        self.active_plot_state = Mock()
        self.active_plot_state.plot_state_id = 1
        
        self.inactive_plot_state = Mock()
        self.inactive_plot_state.plot_state_id = 2
        
        self.active_urf_state = Mock()
        self.active_urf_state.user_role_farm_state_id = 1
        
        # Mock plot
        self.plot_mock = Mock()
        self.plot_mock.plot_id = 1
        self.plot_mock.farm_id = 1
        self.plot_mock.plot_state_id = 1
        
        # Mock farm
        self.farm_mock = Mock()
        self.farm_mock.farm_id = 1
        
        # Mock user_role_farm
        self.user_role_farm_mock = Mock()
        self.user_role_farm_mock.user_role_id = 1
        self.user_role_farm_mock.farm_id = 1
        
    def _extract_response_content(self, response):
        """Helper method to extract content from ORJSONResponse"""
        if hasattr(response, 'body'):
            return json.loads(response.body.decode())
        elif hasattr(response, 'content'):
            return response.content
        else:
            return response
        
    @patch('use_cases.delete_plot_use_case.get_state')
    @patch('use_cases.delete_plot_use_case.get_user_role_ids')
    @patch('use_cases.delete_plot_use_case.get_role_permissions_for_user_role')
    def test_delete_plot_success(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Prueba la eliminación exitosa de un lote"""
        # Arrange
        mock_get_state.side_effect = [
            self.active_plot_state,  # active_plot_state
            self.inactive_plot_state,  # inactive_plot_state
            self.active_urf_state  # active_urf_state
        ]
        
        mock_get_user_role_ids.return_value = [1, 2, 3]
        mock_get_permissions.return_value = ["delete_plot", "view_plot"]
        
        # Configure database queries
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,  # plot query
            self.farm_mock,  # farm query
            self.user_role_farm_mock  # user_role_farm query
        ]
        
        # Act
        response = delete_plot(1, self.user_mock, self.db_mock)
        result = self._extract_response_content(response)
        
        # Assert
        assert result["status"] == "success"
        assert result["message"] == "Lote eliminado correctamente"
        assert self.plot_mock.plot_state_id == self.inactive_plot_state.plot_state_id
        self.db_mock.commit.assert_called_once()
        mock_get_user_role_ids.assert_called_once_with(self.user_mock.user_id)
        mock_get_permissions.assert_called_once_with(self.user_role_farm_mock.user_role_id)
        
    @patch('use_cases.delete_plot_use_case.get_state')
    def test_delete_plot_not_found(self, mock_get_state):
        """Prueba cuando el lote no existe o no está activo"""
        # Arrange
        mock_get_state.side_effect = [
            self.active_plot_state,  # active_plot_state
            self.inactive_plot_state  # inactive_plot_state
        ]
        
        # Configure database query to return None (plot not found)
        self.db_mock.query.return_value.filter.return_value.first.return_value = None
        
        # Act
        response = delete_plot(999, self.user_mock, self.db_mock)
        result = self._extract_response_content(response)
        
        # Assert
        assert result["status"] == "error"
        assert result["message"] == "El lote no existe o no está activo"
        self.db_mock.commit.assert_not_called()
        
    @patch('use_cases.delete_plot_use_case.get_state')
    def test_delete_plot_farm_not_found(self, mock_get_state):
        """Prueba cuando la finca asociada al lote no existe"""
        # Arrange
        mock_get_state.side_effect = [
            self.active_plot_state,  # active_plot_state
            self.inactive_plot_state  # inactive_plot_state
        ]
        
        # Configure database queries
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,  # plot query returns plot
            None  # farm query returns None
        ]
        
        # Act
        response = delete_plot(1, self.user_mock, self.db_mock)
        result = self._extract_response_content(response)
        
        # Assert
        assert result["status"] == "error"
        assert result["message"] == "La finca asociada al lote no existe"
        self.db_mock.commit.assert_not_called()
        
    @patch('use_cases.delete_plot_use_case.get_state')
    @patch('use_cases.delete_plot_use_case.get_user_role_ids')
    def test_delete_plot_no_permission_user_not_in_farm(self, mock_get_user_role_ids, mock_get_state):
        """Prueba cuando el usuario no está asociado con la finca"""
        # Arrange
        mock_get_state.side_effect = [
            self.active_plot_state,  # active_plot_state
            self.inactive_plot_state,  # inactive_plot_state
            self.active_urf_state  # active_urf_state
        ]
        
        mock_get_user_role_ids.return_value = [1, 2, 3]
        
        # Configure database queries
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,  # plot query
            self.farm_mock,  # farm query
            None  # user_role_farm query returns None
        ]
        
        # Act
        response = delete_plot(1, self.user_mock, self.db_mock)
        result = self._extract_response_content(response)
        
        # Assert
        assert result["status"] == "error"
        assert result["message"] == "No tienes permiso para eliminar este lote"
        self.db_mock.commit.assert_not_called()
        mock_get_user_role_ids.assert_called_once_with(self.user_mock.user_id)
        
    @patch('use_cases.delete_plot_use_case.get_state')
    @patch('use_cases.delete_plot_use_case.get_user_role_ids')
    @patch('use_cases.delete_plot_use_case.get_role_permissions_for_user_role')
    def test_delete_plot_no_permission_insufficient_permissions(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Prueba cuando el usuario no tiene permisos para eliminar el lote"""
        # Arrange
        mock_get_state.side_effect = [
            self.active_plot_state,  # active_plot_state
            self.inactive_plot_state,  # inactive_plot_state
            self.active_urf_state  # active_urf_state
        ]
        
        mock_get_user_role_ids.return_value = [1, 2, 3]
        mock_get_permissions.return_value = ["view_plot", "edit_plot"]  # No delete_plot permission
        
        # Configure database queries
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,  # plot query
            self.farm_mock,  # farm query
            self.user_role_farm_mock  # user_role_farm query
        ]
        
        # Act
        response = delete_plot(1, self.user_mock, self.db_mock)
        result = self._extract_response_content(response)
        
        # Assert
        assert result["status"] == "error"
        assert result["message"] == "No tienes permiso para eliminar este lote"
        self.db_mock.commit.assert_not_called()
        mock_get_permissions.assert_called_once_with(self.user_role_farm_mock.user_role_id)
        
    @patch('use_cases.delete_plot_use_case.get_state')
    @patch('use_cases.delete_plot_use_case.get_user_role_ids')
    def test_delete_plot_user_service_error_get_user_role_ids(self, mock_get_user_role_ids, mock_get_state):
        """Prueba cuando hay error al obtener user_role_ids del microservicio"""
        # Arrange
        mock_get_state.side_effect = [
            self.active_plot_state,  # active_plot_state
            self.inactive_plot_state,  # inactive_plot_state
            self.active_urf_state  # active_urf_state
        ]
        
        mock_get_user_role_ids.side_effect = Exception("User service error")
        
        # Configure database queries
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,  # plot query
            self.farm_mock  # farm query
        ]
        
        # Act
        response = delete_plot(1, self.user_mock, self.db_mock)
        result = self._extract_response_content(response)
        
        # Assert
        assert result["status"] == "error"
        assert result["message"] == "No se pudieron obtener los roles del usuario"
        assert response.status_code == 500
        self.db_mock.commit.assert_not_called()
        
    @patch('use_cases.delete_plot_use_case.get_state')
    @patch('use_cases.delete_plot_use_case.get_user_role_ids')
    @patch('use_cases.delete_plot_use_case.get_role_permissions_for_user_role')
    def test_delete_plot_user_service_error_get_permissions(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Prueba cuando hay error al obtener permisos del microservicio"""
        # Arrange
        mock_get_state.side_effect = [
            self.active_plot_state,  # active_plot_state
            self.inactive_plot_state,  # inactive_plot_state
            self.active_urf_state  # active_urf_state
        ]
        
        mock_get_user_role_ids.return_value = [1, 2, 3]
        mock_get_permissions.side_effect = Exception("Permissions service error")
        
        # Configure database queries
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,  # plot query
            self.farm_mock,  # farm query
            self.user_role_farm_mock  # user_role_farm query
        ]
        
        # Act
        response = delete_plot(1, self.user_mock, self.db_mock)
        result = self._extract_response_content(response)
        
        # Assert
        assert result["status"] == "error"
        assert result["message"] == "No se pudieron obtener los permisos del rol"
        assert response.status_code == 500
        self.db_mock.commit.assert_not_called()
        
    @patch('use_cases.delete_plot_use_case.get_state')
    @patch('use_cases.delete_plot_use_case.get_user_role_ids')
    @patch('use_cases.delete_plot_use_case.get_role_permissions_for_user_role')
    def test_delete_plot_database_error(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Prueba cuando hay error en la base de datos durante el commit"""
        # Arrange
        mock_get_state.side_effect = [
            self.active_plot_state,  # active_plot_state
            self.inactive_plot_state,  # inactive_plot_state
            self.active_urf_state  # active_urf_state
        ]
        
        mock_get_user_role_ids.return_value = [1, 2, 3]
        mock_get_permissions.return_value = ["delete_plot", "view_plot"]
        
        # Configure database queries
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,  # plot query
            self.farm_mock,  # farm query
            self.user_role_farm_mock  # user_role_farm query
        ]
        
        # Configure database commit to raise exception
        self.db_mock.commit.side_effect = Exception("Database error")
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            delete_plot(1, self.user_mock, self.db_mock)
        
        assert exc_info.value.status_code == 500
        assert "Error al eliminar el lote" in str(exc_info.value.detail)
        self.db_mock.rollback.assert_called_once()
        
    @patch('use_cases.delete_plot_use_case.get_state')
    def test_delete_plot_missing_active_plot_state(self, mock_get_state):
        """Prueba cuando no se puede obtener el estado activo del lote"""
        # Arrange
        mock_get_state.side_effect = [
            None,  # active_plot_state returns None
            self.inactive_plot_state  # inactive_plot_state
        ]
        
        # Act & Assert
        # This should cause an AttributeError when trying to access active_plot_state.plot_state_id at line 16
        # This line is NOT inside a try-catch block, so it should raise AttributeError directly
        with pytest.raises(AttributeError):
            delete_plot(1, self.user_mock, self.db_mock)
        
        assert mock_get_state.call_count >= 1
        
    @patch('use_cases.delete_plot_use_case.get_state')
    @patch('use_cases.delete_plot_use_case.get_user_role_ids')
    @patch('use_cases.delete_plot_use_case.get_role_permissions_for_user_role')
    def test_delete_plot_missing_inactive_plot_state(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Prueba cuando no se puede obtener el estado inactivo del lote"""
        # Arrange
        mock_get_state.side_effect = [
            self.active_plot_state,  # active_plot_state
            None,  # inactive_plot_state returns None
            self.active_urf_state  # active_urf_state (in case it gets called)
        ]
        
        mock_get_user_role_ids.return_value = [1, 2, 3]
        mock_get_permissions.return_value = ["delete_plot", "view_plot"]
        
        # Configure database queries
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,  # plot query
            self.farm_mock,  # farm query
            self.user_role_farm_mock  # user_role_farm query
        ]
        
        # Act & Assert
        # This should cause an AttributeError when trying to access inactive_plot_state.plot_state_id
        # which gets caught and converted to an HTTPException
        with pytest.raises(HTTPException) as exc_info:
            delete_plot(1, self.user_mock, self.db_mock)
        
        assert exc_info.value.status_code == 500
        assert "Error al eliminar el lote" in str(exc_info.value.detail)
        assert "'NoneType' object has no attribute 'plot_state_id'" in str(exc_info.value.detail)
        assert mock_get_state.call_count >= 2
        
    @patch('use_cases.delete_plot_use_case.get_state')
    @patch('use_cases.delete_plot_use_case.get_user_role_ids')
    def test_delete_plot_missing_user_role_farm_state(self, mock_get_user_role_ids, mock_get_state):
        """Prueba cuando no se puede obtener el estado activo de user_role_farm"""
        # Arrange
        mock_get_state.side_effect = [
            self.active_plot_state,  # active_plot_state
            self.inactive_plot_state,  # inactive_plot_state
            None  # active_urf_state returns None
        ]
        
        mock_get_user_role_ids.return_value = [1, 2, 3]
        
        # Configure database queries
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,  # plot query
            self.farm_mock  # farm query
        ]
        
        # Act & Assert
        # This should cause an AttributeError when trying to access active_urf_state.user_role_farm_state_id at line 41
        # This line is NOT inside a try-catch block, so it should raise AttributeError directly
        with pytest.raises(AttributeError):
            delete_plot(1, self.user_mock, self.db_mock)
        
        assert mock_get_state.call_count >= 3
        
    @patch('use_cases.delete_plot_use_case.get_state')
    @patch('use_cases.delete_plot_use_case.get_user_role_ids')
    @patch('use_cases.delete_plot_use_case.get_role_permissions_for_user_role')
    def test_delete_plot_with_empty_permissions(self, mock_get_permissions, mock_get_user_role_ids, mock_get_state):
        """Prueba cuando el usuario tiene un rol pero sin permisos"""
        # Arrange
        mock_get_state.side_effect = [
            self.active_plot_state,  # active_plot_state
            self.inactive_plot_state,  # inactive_plot_state
            self.active_urf_state  # active_urf_state
        ]
        
        mock_get_user_role_ids.return_value = [1, 2, 3]
        mock_get_permissions.return_value = []  # Empty permissions list
        
        # Configure database queries
        self.db_mock.query.return_value.filter.return_value.first.side_effect = [
            self.plot_mock,  # plot query
            self.farm_mock,  # farm query
            self.user_role_farm_mock  # user_role_farm query
        ]
        
        # Act
        response = delete_plot(1, self.user_mock, self.db_mock)
        result = self._extract_response_content(response)
        
        # Assert
        assert result["status"] == "error"
        assert result["message"] == "No tienes permiso para eliminar este lote"
        self.db_mock.commit.assert_not_called()
        mock_get_permissions.assert_called_once_with(self.user_role_farm_mock.user_role_id) 