"""Azure Virtual Desktop Connection Manager."""

from azure.identity import DefaultAzureCredential
from azure.mgmt.desktopvirtualization import DesktopVirtualizationMgmtClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from .utils.logger import get_logger
from .utils.auth import AzureAuthenticator

logger = get_logger(__name__)


class ConnectionManager:
    """Manages connections to Azure Virtual Desktop resources."""

    def __init__(self, subscription_id, resource_group):
        """Initialize the connection manager.
        
        Args:
            subscription_id: Azure subscription ID
            resource_group: Resource group name
        """
        self.subscription_id = subscription_id
        self.resource_group = resource_group
        self.credential = None
        self.avd_client = None
        self.compute_client = None
        self.network_client = None
        logger.info(f"Initialized ConnectionManager for subscription: {subscription_id}")

    def authenticate(self):
        """Authenticate with Azure using default credentials."""
        try:
            self.credential = DefaultAzureCredential()
            logger.info("Authentication successful")
            return True
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return False

    def connect(self):
        """Establish connections to Azure services."""
        if not self.credential:
            if not self.authenticate():
                raise ConnectionError("Failed to authenticate")

        try:
            self.avd_client = DesktopVirtualizationMgmtClient(
                credential=self.credential,
                subscription_id=self.subscription_id
            )
            self.compute_client = ComputeManagementClient(
                credential=self.credential,
                subscription_id=self.subscription_id
            )
            self.network_client = NetworkManagementClient(
                credential=self.credential,
                subscription_id=self.subscription_id
            )
            logger.info("Successfully connected to Azure services")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {str(e)}")
            return False

    def list_host_pools(self):
        """List all host pools in the resource group."""
        if not self.avd_client:
            raise ConnectionError("Not connected to Azure services")

        try:
            host_pools = list(self.avd_client.host_pools.list_by_resource_group(
                self.resource_group
            ))
            logger.info(f"Found {len(host_pools)} host pools")
            return host_pools
        except Exception as e:
            logger.error(f"Failed to list host pools: {str(e)}")
            return []

    def get_host_pool(self, host_pool_name):
        """Get details of a specific host pool."""
        if not self.avd_client:
            raise ConnectionError("Not connected to Azure services")

        try:
            host_pool = self.avd_client.host_pools.get(
                self.resource_group,
                host_pool_name
            )
            logger.info(f"Retrieved host pool: {host_pool_name}")
            return host_pool
        except Exception as e:
            logger.error(f"Failed to get host pool {host_pool_name}: {str(e)}")
            return None

    def disconnect(self):
        """Close all connections."""
        self.avd_client = None
        self.compute_client = None
        self.network_client = None
        self.credential = None
        logger.info("Disconnected from Azure services")