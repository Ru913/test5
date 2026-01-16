# Azure Virtual Desktop Manager

A Python-based management tool for Azure Virtual Desktop (AVD) environments.

## Features

- **Connection Management**: Authenticate and connect to Azure Virtual Desktop resources
- **Session Handling**: Monitor and manage user sessions across host pools
- **Configuration**: Flexible configuration via YAML files or environment variables
- **Logging**: Comprehensive logging for debugging and monitoring

## Installation

```bash
pip install -r requirements.txt
```

Or install in development mode:

```bash
pip install -e .
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_RESOURCE_GROUP=your-resource-group
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
```

### Configuration File

Alternatively, use a YAML configuration file:

```yaml
subscription_id: your-subscription-id
resource_group: your-resource-group
tenant_id: your-tenant-id
client_id: your-client-id
client_secret: your-client-secret
```

## Usage

### Basic Example

```python
from avd_manager import ConnectionManager, SessionHandler, Config

# Load configuration
config = Config('config.yaml')
config.validate()

# Connect to Azure
manager = ConnectionManager(
    config.get('subscription_id'),
    config.get('resource_group')
)
manager.connect()

# List host pools
host_pools = manager.list_host_pools()
for pool in host_pools:
    print(f"Host Pool: {pool.name}")

# Handle sessions
session_handler = SessionHandler(manager)
sessions = session_handler.monitor_sessions('my-host-pool')
print(f"Active sessions: {len(sessions)}")
```

## Testing

Run the test suite:

```bash
python -m unittest discover tests
```

## Project Structure

```
QA-Test-Repo/
├── avd_manager/          # Main package
│   ├── __init__.py
│   ├── connection_manager.py
│   ├── session_handler.py
│   ├── config.py
│   └── utils/            # Utility modules
│       ├── __init__.py
│       ├── logger.py
│       └── auth.py
├── tests/                # Test suite
│   ├── __init__.py
│   ├── test_connection_manager.py
│   └── test_config.py
├── docs/                 # Documentation
├── examples/             # Example scripts
├── requirements.txt      # Dependencies
├── setup.py             # Package setup
└── README.md            # This file
```

## Requirements

- Python 3.8+
- Azure subscription with Virtual Desktop resources
- Appropriate Azure permissions

## License

MIT License

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.