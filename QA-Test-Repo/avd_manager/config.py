"""Configuration management for AVD Manager."""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from .utils.logger import get_logger

logger = get_logger(__name__)


class Config:
    """Configuration manager for Azure Virtual Desktop."""

    def __init__(self, config_file=None):
        """Initialize configuration.
        
        Args:
            config_file: Path to YAML configuration file (optional)
        """
        load_dotenv()
        self.config_file = config_file
        self.config = {}
        self._load_config()
        logger.info("Configuration loaded successfully")

    def _load_config(self):
        """Load configuration from file and environment variables."""
        # Load from YAML file if provided
        if self.config_file and Path(self.config_file).exists():
            with open(self.config_file, 'r') as f:
                self.config = yaml.safe_load(f)
                logger.info(f"Loaded configuration from {self.config_file}")

        # Override with environment variables
        self.config['subscription_id'] = os.getenv(
            'AZURE_SUBSCRIPTION_ID',
            self.config.get('subscription_id')
        )
        self.config['resource_group'] = os.getenv(
            'AZURE_RESOURCE_GROUP',
            self.config.get('resource_group')
        )
        self.config['tenant_id'] = os.getenv(
            'AZURE_TENANT_ID',
            self.config.get('tenant_id')
        )
        self.config['client_id'] = os.getenv(
            'AZURE_CLIENT_ID',
            self.config.get('client_id')
        )
        self.config['client_secret'] = os.getenv(
            'AZURE_CLIENT_SECRET',
            self.config.get('client_secret')
        )

    def get(self, key, default=None):
        """Get configuration value."""
        return self.config.get(key, default)

    def set(self, key, value):
        """Set configuration value."""
        self.config[key] = value
        logger.debug(f"Set configuration: {key}")

    def validate(self):
        """Validate required configuration values."""
        required_fields = ['subscription_id', 'resource_group']
        missing_fields = [field for field in required_fields if not self.config.get(field)]

        if missing_fields:
            error_msg = f"Missing required configuration: {', '.join(missing_fields)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info("Configuration validation passed")
        return True

    def save(self, output_file):
        """Save configuration to YAML file."""
        with open(output_file, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False)
        logger.info(f"Configuration saved to {output_file}")