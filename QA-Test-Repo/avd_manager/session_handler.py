"""Azure Virtual Desktop Session Handler."""

from datetime import datetime
from .utils.logger import get_logger

logger = get_logger(__name__)


class SessionHandler:
    """Handles AVD user sessions and session hosts."""

    def __init__(self, connection_manager):
        """Initialize the session handler.
        
        Args:
            connection_manager: ConnectionManager instance
        """
        self.connection_manager = connection_manager
        self.active_sessions = {}
        logger.info("Initialized SessionHandler")

    def list_session_hosts(self, host_pool_name):
        """List all session hosts in a host pool."""
        if not self.connection_manager.avd_client:
            raise ConnectionError("Not connected to Azure services")

        try:
            session_hosts = list(
                self.connection_manager.avd_client.session_hosts.list(
                    self.connection_manager.resource_group,
                    host_pool_name
                )
            )
            logger.info(f"Found {len(session_hosts)} session hosts in {host_pool_name}")
            return session_hosts
        except Exception as e:
            logger.error(f"Failed to list session hosts: {str(e)}")
            return []

    def get_user_sessions(self, host_pool_name, session_host_name):
        """Get active user sessions on a session host."""
        if not self.connection_manager.avd_client:
            raise ConnectionError("Not connected to Azure services")

        try:
            sessions = list(
                self.connection_manager.avd_client.user_sessions.list(
                    self.connection_manager.resource_group,
                    host_pool_name,
                    session_host_name
                )
            )
            logger.info(f"Found {len(sessions)} active sessions on {session_host_name}")
            return sessions
        except Exception as e:
            logger.error(f"Failed to get user sessions: {str(e)}")
            return []

    def disconnect_user_session(self, host_pool_name, session_host_name, session_id):
        """Disconnect a user session."""
        if not self.connection_manager.avd_client:
            raise ConnectionError("Not connected to Azure services")

        try:
            self.connection_manager.avd_client.user_sessions.disconnect(
                self.connection_manager.resource_group,
                host_pool_name,
                session_host_name,
                session_id
            )
            logger.info(f"Disconnected session {session_id} on {session_host_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to disconnect session: {str(e)}")
            return False

    def get_session_host_status(self, host_pool_name, session_host_name):
        """Get the status of a session host."""
        if not self.connection_manager.avd_client:
            raise ConnectionError("Not connected to Azure services")

        try:
            session_host = self.connection_manager.avd_client.session_hosts.get(
                self.connection_manager.resource_group,
                host_pool_name,
                session_host_name
            )
            status = {
                "name": session_host.name,
                "status": session_host.status,
                "sessions": session_host.sessions,
                "last_heartbeat": session_host.last_heart_beat,
                "update_state": session_host.update_state
            }
            logger.info(f"Retrieved status for {session_host_name}")
            return status
        except Exception as e:
            logger.error(f"Failed to get session host status: {str(e)}")
            return None

    def monitor_sessions(self, host_pool_name):
        """Monitor all sessions in a host pool."""
        session_hosts = self.list_session_hosts(host_pool_name)
        all_sessions = []

        for host in session_hosts:
            host_name = host.name.split('/')[-1]
            sessions = self.get_user_sessions(host_pool_name, host_name)
            all_sessions.extend(sessions)

        logger.info(f"Monitoring {len(all_sessions)} total sessions in {host_pool_name}")
        return all_sessions