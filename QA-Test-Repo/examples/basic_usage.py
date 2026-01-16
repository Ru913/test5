"""Basic usage example for AVD Manager."""

from avd_manager import ConnectionManager, SessionHandler, Config


def main():
    """Demonstrate basic AVD Manager usage."""
    # Load configuration
    config = Config()
    config.set('subscription_id', 'your-subscription-id')
    config.set('resource_group', 'your-resource-group')
    
    try:
        config.validate()
    except ValueError as e:
        print(f"Configuration error: {e}")
        return

    # Create connection manager
    manager = ConnectionManager(
        config.get('subscription_id'),
        config.get('resource_group')
    )

    # Connect to Azure
    if not manager.connect():
        print("Failed to connect to Azure")
        return

    print("Connected to Azure successfully")

    # List host pools
    host_pools = manager.list_host_pools()
    print(f"\nFound {len(host_pools)} host pools:")
    for pool in host_pools:
        print(f"  - {pool.name}")

    # Get details of first host pool
    if host_pools:
        pool_name = host_pools[0].name.split('/')[-1]
        pool_details = manager.get_host_pool(pool_name)
        print(f"\nHost Pool Details: {pool_details.name}")
        print(f"  Type: {pool_details.host_pool_type}")
        print(f"  Load Balancer: {pool_details.load_balancer_type}")

        # Monitor sessions
        session_handler = SessionHandler(manager)
        sessions = session_handler.monitor_sessions(pool_name)
        print(f"\nActive sessions: {len(sessions)}")

    # Disconnect
    manager.disconnect()
    print("\nDisconnected from Azure")


if __name__ == '__main__':
    main()