"""Tests for ConnectionManager."""

import unittest
from unittest.mock import Mock, patch
from avd_manager.connection_manager import ConnectionManager


class TestConnectionManager(unittest.TestCase):
    """Test cases for ConnectionManager."""

    def setUp(self):
        """Set up test fixtures."""
        self.subscription_id = "test-subscription-id"
        self.resource_group = "test-resource-group"
        self.manager = ConnectionManager(self.subscription_id, self.resource_group)

    def test_initialization(self):
        """Test ConnectionManager initialization."""
        self.assertEqual(self.manager.subscription_id, self.subscription_id)
        self.assertEqual(self.manager.resource_group, self.resource_group)
        self.assertIsNone(self.manager.credential)
        self.assertIsNone(self.manager.avd_client)

    @patch('avd_manager.connection_manager.DefaultAzureCredential')
    def test_authenticate_success(self, mock_credential):
        """Test successful authentication."""
        mock_credential.return_value = Mock()
        result = self.manager.authenticate()
        self.assertTrue(result)
        self.assertIsNotNone(self.manager.credential)

    @patch('avd_manager.connection_manager.DefaultAzureCredential')
    def test_authenticate_failure(self, mock_credential):
        """Test authentication failure."""
        mock_credential.side_effect = Exception("Auth failed")
        result = self.manager.authenticate()
        self.assertFalse(result)

    def test_disconnect(self):
        """Test disconnection."""
        self.manager.credential = Mock()
        self.manager.avd_client = Mock()
        self.manager.disconnect()
        self.assertIsNone(self.manager.credential)
        self.assertIsNone(self.manager.avd_client)


if __name__ == '__main__':
    unittest.main()