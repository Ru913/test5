"""Authentication utilities for Azure."""

from azure.identity import DefaultAzureCredential, ClientSecretCredential
from .logger import get_logger

logger = get_logger(__name__)


class AzureAuthenticator:
    """Handles Azure authentication methods."""

    def __init__(self, tenant_id=None, client_id=None, client_secret=None):
        """Initialize authenticator.
        
        Args:
            tenant_id: Azure tenant ID (optional)
            client_id: Azure client ID (optional)
            client_secret: Azure client secret (optional)
        """
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.credential = None
        logger.info("Initialized AzureAuthenticator")

    def get_default_credential(self):
        """Get default Azure credential.
        
        Returns:
            DefaultAzureCredential instance
        """
        try:
            self.credential = DefaultAzureCredential()
            logger.info("Using default Azure credential")
            return self.credential
        except Exception as e:
            logger.error(f"Failed to get default credential: {str(e)}")
            raise

    def get_service_principal_credential(self):
        """Get service principal credential.
        
        Returns:
            ClientSecretCredential instance
        """
        if not all([self.tenant_id, self.client_id, self.client_secret]):
            raise ValueError("Service principal credentials not configured")

        try:
            self.credential = ClientSecretCredential(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            logger.info("Using service principal credential")
            return self.credential
        except Exception as e:
            logger.error(f"Failed to get service principal credential: {str(e)}")
            raise

    def get_credential(self):
        """Get appropriate credential based on configuration.
        
        Returns:
            Azure credential instance
        """
        if all([self.tenant_id, self.client_id, self.client_secret]):
            return self.get_service_principal_credential()
        else:
            return self.get_default_credential()