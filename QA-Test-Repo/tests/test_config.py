"""Tests for Config."""

import unittest
import os
from unittest.mock import patch, mock_open
from avd_manager.config import Config


class TestConfig(unittest.TestCase):
    """Test cases for Config."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_config = {
            'subscription_id': 'test-sub-id',
            'resource_group': 'test-rg'
        }

    @patch.dict(os.environ, {
        'AZURE_SUBSCRIPTION_ID': 'env-sub-id',
        'AZURE_RESOURCE_GROUP': 'env-rg'
    })
    def test_load_from_environment(self):
        """Test loading configuration from environment variables."""
        config = Config()
        self.assertEqual(config.get('subscription_id'), 'env-sub-id')
        self.assertEqual(config.get('resource_group'), 'env-rg')

    def test_get_default_value(self):
        """Test getting configuration with default value."""
        config = Config()
        result = config.get('nonexistent_key', 'default_value')
        self.assertEqual(result, 'default_value')

    def test_set_value(self):
        """Test setting configuration value."""
        config = Config()
        config.set('test_key', 'test_value')
        self.assertEqual(config.get('test_key'), 'test_value')

    @patch.dict(os.environ, {
        'AZURE_SUBSCRIPTION_ID': 'test-sub',
        'AZURE_RESOURCE_GROUP': 'test-rg'
    })
    def test_validate_success(self):
        """Test successful validation."""
        config = Config()
        result = config.validate()
        self.assertTrue(result)

    def test_validate_failure(self):
        """Test validation failure with missing fields."""
        config = Config()
        with self.assertRaises(ValueError):
            config.validate()


if __name__ == '__main__':
    unittest.main()