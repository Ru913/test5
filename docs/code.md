# Azure Virtual Desktop Manager — Code Documentation

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Package Public API](#2-package-public-api)
3. [Key Classes and Responsibilities](#3-key-classes-and-responsibilities)
   - 3.1 [Config](#31-config--avd_managerconfigpy)
   - 3.2 [ConnectionManager](#32-connectionmanager--avd_managerconnection_managerpy)
   - 3.3 [SessionHandler](#33-sessionhandler--avd_managersession_handlerpy)
   - 3.4 [AzureAuthenticator](#34-azureauthenticator--avd_managerutilsauthpy)
4. [Utility Functions](#4-utility-functions)
   - 4.1 [get_logger()](#41-get_logger--avd_managerutilsloggerpy)
   - 4.2 [setup_file_logging()](#42-setup_file_logging--avd_managerutilsloggerpy)
5. [Method Reference](#5-method-reference)
6. [Code Patterns and Conventions](#6-code-patterns-and-conventions)
7. [Error Handling Patterns](#7-error-handling-patterns)
8. [Configuration System](#8-configuration-system)
9. [Dependency and Service Wiring](#9-dependency-and-service-wiring)
10. [External Dependencies](#10-external-dependencies)
11. [Testing Patterns](#11-testing-patterns)
12. [Example Usage](#12-example-usage)

---

## 1. Project Overview

**Package:** `avd-manager` (PyPI name) / `avd_manager` (importable name)  
**Version:** `0.1.0` (Alpha)  
**Python requirement:** ≥ 3.8  
**Author:** QA Test Team (`qa@example.com`)  
**License:** MIT

`avd_manager` is a Python library for managing Azure Virtual Desktop (AVD) environments. It provides three top-level capabilities:

| Capability | Entry Point |
|---|---|
| Azure authentication & connection lifecycle | `ConnectionManager` |
| User session and host-pool monitoring | `SessionHandler` |
| YAML / environment-variable configuration | `Config` |

Source: `QA-Test-Repo/setup.py` (lines 3–26), `QA-Test-Repo/README.md`.

---

## 2. Package Public API

`QA-Test-Repo/avd_manager/__init__.py` (lines 1–10) defines the package's public surface:

```python
__version__ = "0.1.0"
__author__  = "QA Test Team"

from .connection_manager import ConnectionManager
from .session_handler    import SessionHandler
from .config             import Config

__all__ = ["ConnectionManager", "SessionHandler", "Config"]
```

All three classes are importable directly from the top-level package:

```python
from avd_manager import ConnectionManager, SessionHandler, Config
```

**Note:** `__version__` and `__author__` are module-level attributes but are not included in `__all__`. They are accessible as `avd_manager.__version__` and `avd_manager.__author__` but are not part of the formal public API contract.

The `utils` sub-package (`QA-Test-Repo/avd_manager/utils/__init__.py`, lines 1–6) re-exports two helpers:

```python
from .logger import get_logger
from .auth   import AzureAuthenticator

__all__ = ["get_logger", "AzureAuthenticator"]
```

**Important:** `setup_file_logging()` is defined in `utils/logger.py` but is **not** re-exported in `utils/__init__.py`. To use it, import directly:
```python
from avd_manager.utils.logger import setup_file_logging
```

---

## 3. Key Classes and Responsibilities

### 3.1 `Config` — `avd_manager/config.py`

**Responsibility:** Centralised configuration management. Loads settings from an optional YAML file, then overlays values from environment variables. Provides typed get/set access and validates that mandatory fields are present before use.

**Constructor:**

```python
Config.__init__(self, config_file=None)
```
`QA-Test-Repo/avd_manager/config.py` (lines 14–25)

| Parameter | Type | Description |
|---|---|---|
| `config_file` | `str \| None` | Path to a YAML configuration file. Optional. |

On construction the class:
1. Calls `load_dotenv()` to populate `os.environ` from any `.env` file (line 21).
2. Calls `self._load_config()` to merge file + environment values (line 24).
3. Logs `"Configuration loaded successfully"` at INFO level (line 25).

**Note:** `load_dotenv()` is called every time a `Config` object is instantiated. Multiple instantiations will call `load_dotenv()` multiple times, but this is safe — `load_dotenv()` only loads variables that are not already set in `os.environ`.

**Internal state:**

| Attribute | Type | Description |
|---|---|---|
| `config_file` | `str \| None` | Path supplied at construction |
| `config` | `dict` | Merged configuration dictionary |

**Edge case:** If `config_file` is provided but the file is empty or contains only comments, `yaml.safe_load()` returns `None` (line 33). The code does not guard against this, so `self.config` would be set to `None`, causing `AttributeError` on subsequent `.get()` calls. **Workaround:** Ensure YAML files contain at least one key-value pair, or pass `config_file=None` if no file is available.

---

### 3.2 `ConnectionManager` — `avd_manager/connection_manager.py`

**Responsibility:** Manages the full lifecycle of connections to Azure services — authentication, client instantiation, host-pool queries, and clean disconnection.

**Constructor:**

```python
ConnectionManager.__init__(self, subscription_id, resource_group)
```
`QA-Test-Repo/avd_manager/connection_manager.py` (lines 16–31)

| Parameter | Type | Description |
|---|---|---|
| `subscription_id` | `str` | Azure subscription GUID |
| `resource_group` | `str` | Azure resource group name |

**Internal state:**

| Attribute | Type | Initial value | Description |
|---|---|---|---|
| `subscription_id` | `str` | constructor arg | Subscription identifier |
| `resource_group` | `str` | constructor arg | Resource group name |
| `credential` | `DefaultAzureCredential \| None` | `None` | Azure credential object |
| `avd_client` | `DesktopVirtualizationMgmtClient \| None` | `None` | AVD management client |
| `compute_client` | `ComputeManagementClient \| None` | `None` | Compute management client |
| `network_client` | `NetworkManagementClient \| None` | `None` | Network management client |

---

### 3.3 `SessionHandler` — `avd_manager/session_handler.py`

**Responsibility:** Operates on top of an established `ConnectionManager` to enumerate session hosts, retrieve active user sessions, disconnect individual sessions, query host health, and aggregate sessions across an entire host pool.

**Constructor:**

```python
SessionHandler.__init__(self, connection_manager)
```
`QA-Test-Repo/avd_manager/session_handler.py` (lines 12–21)

| Parameter | Type | Description |
|---|---|---|
| `connection_manager` | `ConnectionManager` | A connected `ConnectionManager` instance |

**Internal state:**

| Attribute | Type | Description |
|---|---|---|
| `connection_manager` | `ConnectionManager` | Injected dependency |
| `active_sessions` | `dict` | Cache dictionary, initialised as empty `{}` (line 19). **Note:** This attribute is never written to by any `SessionHandler` method; it is intended for external callers to populate if needed. |

**Tight coupling:** `SessionHandler` directly accesses `self.connection_manager.resource_group` in every method (e.g., line 31). This creates a tight coupling to a specific attribute of `ConnectionManager`.

---

### 3.4 `AzureAuthenticator` — `avd_manager/utils/auth.py`

**Responsibility:** Encapsulates the two Azure authentication strategies — `DefaultAzureCredential` (environment/managed-identity chain) and `ClientSecretCredential` (explicit service-principal). Selects the appropriate strategy automatically via `get_credential()`.

**Constructor:**

```python
AzureAuthenticator.__init__(self, tenant_id=None, client_id=None, client_secret=None)
```
`QA-Test-Repo/avd_manager/utils/auth.py` (lines 12–24)

| Parameter | Type | Description |
|---|---|---|
| `tenant_id` | `str \| None` | Azure AD tenant ID |
| `client_id` | `str \| None` | Service principal application ID |
| `client_secret` | `str \| None` | Service principal secret |

**Internal state:**

| Attribute | Type | Initial value | Description |
|---|---|---|---|
| `tenant_id` | `str \| None` | constructor arg | Tenant ID |
| `client_id` | `str \| None` | constructor arg | Client ID |
| `client_secret` | `str \| None` | constructor arg | Client secret |
| `credential` | `DefaultAzureCredential \| ClientSecretCredential \| None` | `None` | Last-obtained credential object (line 22) |

> **Note:** `AzureAuthenticator` is imported by `ConnectionManager` (`connection_manager.py` line 8) but `ConnectionManager.authenticate()` uses `DefaultAzureCredential` directly rather than delegating to `AzureAuthenticator`. The import is present but unused in the current implementation — `AzureAuthenticator` is available for callers that need explicit service-principal control or want to switch authentication strategies at runtime.

---

## 4. Utility Functions

### 4.1 `get_logger()` — `avd_manager/utils/logger.py`

```python
def get_logger(name: str, level: int = logging.INFO) -> logging.Logger
```
`QA-Test-Repo/avd_manager/utils/logger.py` (lines 7–35)

Returns a `logging.Logger` configured with a `StreamHandler` writing to `sys.stdout`. The handler is added only once (guarded by `if not logger.handlers` at line 19) to prevent duplicate log lines when the function is called multiple times with the same `name`.

**Log format:**
```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```
Date format: `%Y-%m-%d %H:%M:%S`

**Important caveat:** The duplicate-handler guard means that if `get_logger('foo', logging.DEBUG)` is called after `get_logger('foo', logging.INFO)`, the level change is silently ignored. The logger will retain the original level set on the first call. To change the level of an existing logger, call `logging.getLogger('foo').setLevel(new_level)` directly.

**Usage pattern across the codebase** — every module acquires its logger at module level:

```python
# avd_manager/config.py line 8
logger = get_logger(__name__)

# avd_manager/connection_manager.py line 9
logger = get_logger(__name__)

# avd_manager/session_handler.py line 5
logger = get_logger(__name__)

# avd_manager/utils/auth.py line 5
logger = get_logger(__name__)
```

Using `__name__` ensures log records carry the fully-qualified module path (e.g., `avd_manager.connection_manager`).

---

### 4.2 `setup_file_logging()` — `avd_manager/utils/logger.py`

```python
def setup_file_logging(log_file: str, level: int = logging.INFO) -> None
```
`QA-Test-Repo/avd_manager/utils/logger.py` (lines 38–59)

Adds a `FileHandler` to the **root** logger. Creates any missing parent directories via `Path.mkdir(parents=True, exist_ok=True)` (line 44). Uses the same format string as `get_logger()`. Returns `None`.

**Important side effect:** This function attaches a handler to the root logger (line 57), which means all loggers in the process (including third-party libraries) will write to the specified file. This is a global side effect and should be called once at application startup.

**Intended use:** Call this once at application startup when persistent log files are required (e.g., path `logs/avd_manager.log` shown in `examples/config.yaml` line 15).

**Example:**
```python
from avd_manager.utils.logger import setup_file_logging

# At application startup
setup_file_logging('logs/avd_manager.log', level=logging.INFO)
```

---

## 5. Method Reference

### `Config` methods

| Method | Signature | Returns | Source (line) |
|---|---|---|---|
| `__init__` | `(self, config_file=None)` | `None` | config.py:14 |
| `_load_config` | `(self)` | `None` | config.py:27 |
| `get` | `(self, key, default=None)` | `Any` | config.py:62 |
| `set` | `(self, key, value)` | `None` | config.py:66 |
| `validate` | `(self)` | `bool` | config.py:70 |
| `save` | `(self, output_file)` | `None` | config.py:79 |

**`Config._load_config()`** (config.py lines 27–55):  
Reads the YAML file (if `config_file` is set and the path exists), then unconditionally overwrites five keys from environment variables, falling back to the YAML-loaded values when the environment variable is absent:

| Config key | Environment variable |
|---|---|
| `subscription_id` | `AZURE_SUBSCRIPTION_ID` |
| `resource_group` | `AZURE_RESOURCE_GROUP` |
| `tenant_id` | `AZURE_TENANT_ID` |
| `client_id` | `AZURE_CLIENT_ID` |
| `client_secret` | `AZURE_CLIENT_SECRET` |

**Precedence:** Environment variables always take precedence. If `AZURE_SUBSCRIPTION_ID` is set in `os.environ`, it will be used regardless of the YAML file value. Example:
```yaml
# config.yaml
subscription_id: "yaml-value"
```
```bash
export AZURE_SUBSCRIPTION_ID="env-value"
```
```python
config = Config('config.yaml')
config.get('subscription_id')  # Returns "env-value"
```

**Silent skip on missing file:** If `config_file` is provided but the path does not exist, the file-loading step is silently skipped (line 30). No warning or error is logged. The configuration will be populated only from environment variables.

**`Config.get()`** (config.py lines 62–64):  
```python
def get(self, key, default=None):
    """Get configuration value."""
    return self.config.get(key, default)
```
Returns the value associated with `key` in the configuration dictionary, or `default` if the key is not present.

**`Config.set()`** (config.py lines 66–69):  
```python
def set(self, key, value):
    """Set configuration value."""
    self.config[key] = value
    logger.debug(f"Set configuration: {key}")
```
Sets a configuration value. Logs at DEBUG level (not INFO) to avoid leaking sensitive values like `client_secret` into log files.

**`Config.validate()`** (config.py lines 70–77):  
Checks that `subscription_id` and `resource_group` are non-empty. Raises `ValueError` with a descriptive message listing all missing fields if validation fails. Returns `True` on success.

**Error message format:** `"Missing required configuration: subscription_id, resource_group"` (comma-separated list of missing fields).

**`Config.save()`** (config.py lines 79–83):  
```python
def save(self, output_file):
    """Save configuration to YAML file."""
    with open(output_file, 'w') as f:
        yaml.dump(self.config, f, default_flow_style=False)
    logger.info(f"Configuration saved to {output_file}")
```
Serialises `self.config` to a YAML file at `output_file` using `yaml.dump(..., default_flow_style=False)`. Creates the file if it does not exist; overwrites if it does.

**Edge case:** YAML values are parsed natively by `yaml.safe_load()`. If a YAML file contains `subscription_id: 12345` (unquoted integer), the value will be an `int`, not a `str`. This may cause downstream type errors in Azure SDK calls. **Recommendation:** Always quote string values in YAML files:
```yaml
subscription_id: "12345"  # String
resource_group: "my-rg"  # String
```

---

### `ConnectionManager` methods

| Method | Signature | Returns | Source (line) |
|---|---|---|---|
| `__init__` | `(self, subscription_id, resource_group)` | `None` | connection_manager.py:16 |
| `authenticate` | `(self)` | `bool` | connection_manager.py:33 |
| `connect` | `(self)` | `bool` | connection_manager.py:42 |
| `list_host_pools` | `(self)` | `list` | connection_manager.py:64 |
| `get_host_pool` | `(self, host_pool_name)` | `object \| None` | connection_manager.py:77 |
| `disconnect` | `(self)` | `None` | connection_manager.py:92 |

**`ConnectionManager.authenticate()`** (connection_manager.py lines 33–40):  
```python
def authenticate(self):
    """Authenticate with Azure using default credentials."""
    try:
        self.credential = DefaultAzureCredential()
        logger.info("Authentication successful")
        return True
    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}")
        return False
```
Instantiates `DefaultAzureCredential` and stores it in `self.credential`. Returns `True` on success, `False` on any exception. Does not raise exceptions.

**`ConnectionManager.connect()`** (connection_manager.py lines 42–63):  
```python
def connect(self):
    """Establish connections to Azure services."""
    if not self.credential:
        if not self.authenticate():
            raise ConnectionError("Failed to authenticate")
    # ... instantiate three SDK clients ...
    return True  # or False on exception
```
Calls `authenticate()` if `self.credential` is `None` (lazy authentication). Then instantiates all three Azure management clients (`DesktopVirtualizationMgmtClient`, `ComputeManagementClient`, `NetworkManagementClient`) using the stored credential and subscription ID. Returns `True` on success, `False` on failure.

**Raises:** `ConnectionError("Failed to authenticate")` if `authenticate()` returns `False` (line 46). This is the only method in the codebase that converts a boolean-return failure into a raised exception.

**Partial-failure state:** If `DesktopVirtualizationMgmtClient` instantiation succeeds but `ComputeManagementClient` raises an exception (line 53), `avd_client` will be set but `compute_client` and `network_client` will be `None`, and `connect()` returns `False`. The object is left in a partially-connected state. Callers should check the return value before proceeding.

**Re-calling `connect()`:** Calling `connect()` multiple times is safe. If `self.credential` is already set, the method skips `authenticate()` and re-creates all three SDK clients without re-authenticating.

**`ConnectionManager.list_host_pools()`** (connection_manager.py lines 64–75):  
```python
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
```
Calls `avd_client.host_pools.list_by_resource_group()` and eagerly materialises the paginator into a list. Returns a list of host pool objects from the Azure SDK. Returns `[]` on any exception.

**Raises:** `ConnectionError("Not connected to Azure services")` if `avd_client` is `None`.

**`ConnectionManager.get_host_pool()`** (connection_manager.py lines 77–90):  
```python
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
```
Retrieves a specific host pool by name. Returns the host pool object on success, `None` on any exception (including `ResourceNotFoundError` if the pool does not exist).

**Raises:** `ConnectionError("Not connected to Azure services")` if `avd_client` is `None`.

**Unsafe pattern in examples:** The example at `examples/basic_usage.py` (line 43) calls `pool_details.host_pool_type` without checking for `None`:
```python
pool_details = manager.get_host_pool(pool_name)
print(f"Type: {pool_details.host_pool_type}")  # AttributeError if pool_details is None
```
**Recommendation:** Always check for `None`:
```python
pool_details = manager.get_host_pool(pool_name)
if pool_details:
    print(f"Type: {pool_details.host_pool_type}")
```

**`ConnectionManager.disconnect()`** (connection_manager.py lines 92–98):  
```python
def disconnect(self):
    """Close all connections."""
    self.avd_client = None
    self.compute_client = None
    self.network_client = None
    self.credential = None
    logger.info("Disconnected from Azure services")
```
Sets all four instance attributes to `None`, effectively releasing all client references. Idempotent — calling `disconnect()` on an already-disconnected manager is safe.

---

### `SessionHandler` methods

| Method | Signature | Returns | Source (line) |
|---|---|---|---|
| `__init__` | `(self, connection_manager)` | `None` | session_handler.py:12 |
| `list_session_hosts` | `(self, host_pool_name)` | `list` | session_handler.py:23 |
| `get_user_sessions` | `(self, host_pool_name, session_host_name)` | `list` | session_handler.py:40 |
| `disconnect_user_session` | `(self, host_pool_name, session_host_name, session_id)` | `bool` | session_handler.py:58 |
| `get_session_host_status` | `(self, host_pool_name, session_host_name)` | `dict \| None` | session_handler.py:76 |
| `monitor_sessions` | `(self, host_pool_name)` | `list` | session_handler.py:100 |

**`SessionHandler.list_session_hosts()`** (session_handler.py lines 23–38):  
```python
def list_session_hosts(self, host_pool_name):
    """List all session hosts in a host pool."""
    if not self.connection_manager.avd_client:
        raise ConnectionError("Not connected to Azure services")
    try:
        session_hosts = list(
            self.connection_manager.avd_client.session_hosts.list(...)
        )
        logger.info(f"Found {len(session_hosts)} session hosts in {host_pool_name}")
        return session_hosts
    except Exception as e:
        logger.error(f"Failed to list session hosts: {str(e)}")
        return []
```
Lists all session hosts in a host pool. Eagerly materialises the paginator into a list. Returns a list of session host objects. Returns `[]` on any exception.

**Raises:** `ConnectionError("Not connected to Azure services")` if `avd_client` is `None`.

**`SessionHandler.get_user_sessions()`** (session_handler.py lines 40–56):  
```python
def get_user_sessions(self, host_pool_name, session_host_name):
    """Get active user sessions on a session host."""
    if not self.connection_manager.avd_client:
        raise ConnectionError("Not connected to Azure services")
    try:
        sessions = list(
            self.connection_manager.avd_client.user_sessions.list(...)
        )
        logger.info(f"Found {len(sessions)} active sessions on {session_host_name}")
        return sessions
    except Exception as e:
        logger.error(f"Failed to get user sessions: {str(e)}")
        return []
```
Retrieves all active user sessions on a specific session host. Eagerly materialises the paginator. Returns a list of session objects. Returns `[]` on any exception.

**Raises:** `ConnectionError("Not connected to Azure services")` if `avd_client` is `None`.

**Performance note:** Eagerly materialising paginators with `list()` may be slow for large host pools with many sessions. Consider lazy iteration if performance is critical.

**`SessionHandler.disconnect_user_session()`** (session_handler.py lines 58–74):  
```python
def disconnect_user_session(self, host_pool_name, session_host_name, session_id):
    """Disconnect a user session."""
    if not self.connection_manager.avd_client:
        raise ConnectionError("Not connected to Azure services")
    try:
        self.connection_manager.avd_client.user_sessions.disconnect(...)
        logger.info(f"Disconnected session {session_id} on {session_host_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to disconnect session: {str(e)}")
        return False
```
Disconnects a user session. The Azure SDK call is synchronous. Returns `True` on success, `False` on any exception. The return value from the SDK call is discarded.

**Raises:** `ConnectionError("Not connected to Azure services")` if `avd_client` is `None`.

**`SessionHandler.get_session_host_status()`** (session_handler.py lines 76–98):  
```python
def get_session_host_status(self, host_pool_name, session_host_name):
    """Get the status of a session host."""
    if not self.connection_manager.avd_client:
        raise ConnectionError("Not connected to Azure services")
    try:
        session_host = self.connection_manager.avd_client.session_hosts.get(...)
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
```
Returns a plain `dict` with keys `name`, `status`, `sessions`, `last_heartbeat`, `update_state` extracted from the Azure SDK response object. Returns `None` on failure.

**Name transformation:** The SDK attribute `last_heart_beat` is mapped to the dict key `last_heartbeat` (line 89). This name transformation is not immediately obvious and could confuse callers comparing SDK documentation to library output.

**Raises:** `ConnectionError("Not connected to Azure services")` if `avd_client` is `None`.

**`SessionHandler.monitor_sessions()`** (session_handler.py lines 100–112):  
```python
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
```
Convenience aggregator — calls `list_session_hosts()` then iterates each host, calling `get_user_sessions()` and extending a flat list. Returns all sessions across the pool in a single list.

**Propagates exceptions:** Calls `list_session_hosts()` which raises `ConnectionError` if `avd_client` is `None`. This exception propagates to the caller unhandled — `monitor_sessions()` itself has no guard and no try/except.

**Name extraction pattern:** Uses `host.name.split('/')[-1]` to extract the short name from the full resource ID. This pattern is fragile — if the name contains no `/`, the full string is returned. Azure SDK objects are expected to return fully-qualified resource IDs, so this assumption should hold, but it is not documented.

---

### `AzureAuthenticator` methods

| Method | Signature | Returns | Source (line) |
|---|---|---|---|
| `__init__` | `(self, tenant_id=None, client_id=None, client_secret=None)` | `None` | auth.py:12 |
| `get_default_credential` | `(self)` | `DefaultAzureCredential` | auth.py:26 |
| `get_service_principal_credential` | `(self)` | `ClientSecretCredential` | auth.py:40 |
| `get_credential` | `(self)` | `DefaultAzureCredential \| ClientSecretCredential` | auth.py:60 |

**`AzureAuthenticator.get_default_credential()`** (auth.py lines 26–37):  
```python
def get_default_credential(self):
    """Get default Azure credential."""
    try:
        self.credential = DefaultAzureCredential()
        logger.info("Using default Azure credential")
        return self.credential
    except Exception as e:
        logger.error(f"Failed to get default credential: {str(e)}")
        raise
```
Instantiates `DefaultAzureCredential` and stores it in `self.credential`. Returns the credential on success.

**Raises:** Re-raises any exception from `DefaultAzureCredential()` constructor (bare `raise` at line 37). Does not swallow exceptions.

**`AzureAuthenticator.get_service_principal_credential()`** (auth.py lines 40–57):  
```python
def get_service_principal_credential(self):
    """Get service principal credential."""
    if not all([self.tenant_id, self.client_id, self.client_secret]):
        raise ValueError("Service principal credentials not configured")
    try:
        self.credential = ClientSecretCredential(...)
        logger.info("Using service principal credential")
        return self.credential
    except Exception as e:
        logger.error(f"Failed to get service principal credential: {str(e)}")
        raise
```
Instantiates `ClientSecretCredential` using the stored tenant ID, client ID, and secret. Stores it in `self.credential`. Returns the credential on success.

**Raises:** 
- `ValueError("Service principal credentials not configured")` if any of the three required fields are `None` or empty (line 46).
- Re-raises any exception from `ClientSecretCredential()` constructor (bare `raise` at line 57).

**`AzureAuthenticator.get_credential()`** (auth.py lines 60–68):  
```python
def get_credential(self):
    """Get appropriate credential based on configuration."""
    if all([self.tenant_id, self.client_id, self.client_secret]):
        return self.get_service_principal_credential()
    else:
        return self.get_default_credential()
```
Strategy selector — if all three of `tenant_id`, `client_id`, and `client_secret` are set, delegates to `get_service_principal_credential()`; otherwise delegates to `get_default_credential()`.

**Raises:** Any exception from the delegated method (either `ValueError` or re-raised SDK exceptions).

---

## 6. Code Patterns and Conventions

### Module-level logger acquisition
Every module in `avd_manager` acquires a named logger at import time using the pattern:
```python
logger = get_logger(__name__)
```
This is consistent across `config.py` (line 8), `connection_manager.py` (line 9), `session_handler.py` (line 5), and `utils/auth.py` (line 5). Using `__name__` ensures log records carry the fully-qualified module path (e.g., `avd_manager.connection_manager`).

### Guard-before-operate pattern
All `SessionHandler` and `ConnectionManager` methods that require an active Azure client check the client attribute before proceeding and raise `ConnectionError` immediately if it is `None`:

```python
# session_handler.py line 25
if not self.connection_manager.avd_client:
    raise ConnectionError("Not connected to Azure services")
```

This pattern appears in:
- `SessionHandler.list_session_hosts()` (line 25)
- `SessionHandler.get_user_sessions()` (line 42)
- `SessionHandler.disconnect_user_session()` (line 60)
- `SessionHandler.get_session_host_status()` (line 78)
- `ConnectionManager.list_host_pools()` (line 65)
- `ConnectionManager.get_host_pool()` (line 79)

### Lazy authentication in `connect()`
`ConnectionManager.connect()` (connection_manager.py line 43) checks `if not self.credential` and calls `authenticate()` automatically, so callers can call `connect()` directly without a prior explicit `authenticate()` call.

### Docstrings on public symbols
**Note:** The documentation in Section 6 of the original document claimed "every class and every public method carries a Google-style docstring with an `Args:` section." This is **inaccurate**. Inspection of the actual source code reveals:

- **Classes** have docstrings (e.g., `Config`, `ConnectionManager`, `SessionHandler`, `AzureAuthenticator`).
- **`__init__` methods** have full Google-style docstrings with `Args:` sections.
- **All other public methods** have only one-line docstrings with no `Args:`, `Returns:`, or `Raises:` sections.

Examples of incomplete docstrings:
- `Config.get()` (line 62): `"""Get configuration value."""`
- `Config.set()` (line 66): `"""Set configuration value."""`
- `ConnectionManager.authenticate()` (line 33): `"""Authenticate with Azure using default credentials."""`
- `SessionHandler.list_session_hosts()` (line 23): `"""List all session hosts in a host pool."""`

This violates the stated convention in `CONTRIBUTING.md` (line 28: "Add docstrings to all functions and classes"), though the convention does not explicitly mandate Google-style format.

### PEP 8 compliance
All identifiers use `snake_case` for functions/variables and `PascalCase` for classes, consistent with PEP 8. `CONTRIBUTING.md` (line 26) explicitly mandates PEP 8 adherence: "Follow PEP 8 guidelines".

### Name extraction from Azure resource IDs
Azure SDK objects return fully-qualified resource IDs in `.name`. The codebase consistently strips the path prefix with:
```python
host_name = host.name.split('/')[-1]
```
Seen in `session_handler.py` (line 104) and `examples/basic_usage.py` (line 40).

**Fragility note:** This pattern silently returns the full string if no `/` is present. The assumption is that Azure SDK objects always return fully-qualified resource IDs, but this is not documented.

### Unused import
`session_handler.py` (line 3) imports `from datetime import datetime`, but `datetime` is never used anywhere in the file.

---

## 7. Error Handling Patterns

The codebase uses two complementary error-handling strategies:

### 7.1 Boolean-return with logged exception (non-fatal operations)
Methods that perform network I/O wrap their body in `try/except Exception as e`, log the error with `logger.error(f"... {str(e)}")`, and return a safe default (`False`, `[]`, or `None`). This prevents a single failed API call from crashing the caller.

Examples:
- `ConnectionManager.authenticate()` → returns `False` (connection_manager.py lines 33–40)
- `ConnectionManager.connect()` → returns `False` (lines 42–63)
- `ConnectionManager.list_host_pools()` → returns `[]` (lines 64–75)
- `ConnectionManager.get_host_pool()` → returns `None` (lines 77–90)
- `SessionHandler.list_session_hosts()` → returns `[]` (session_handler.py lines 23–38)
- `SessionHandler.get_user_sessions()` → returns `[]` (lines 40–56)
- `SessionHandler.disconnect_user_session()` → returns `False` (lines 58–74)
- `SessionHandler.get_session_host_status()` → returns `None` (lines 76–98)

### 7.2 Raise on precondition failure (programming errors)
Methods raise immediately when a required precondition is not met, rather than silently failing:

| Condition | Exception | Message | Location |
|---|---|---|---|
| `avd_client` is `None` | `ConnectionError` | `"Not connected to Azure services"` | session_handler.py lines 25, 42, 60, 78 |
| `avd_client` is `None` | `ConnectionError` | `"Not connected to Azure services"` | connection_manager.py lines 65, 79 |
| `authenticate()` returns `False` | `ConnectionError` | `"Failed to authenticate"` | connection_manager.py line 46 |
| Missing required config fields | `ValueError` | `"Missing required configuration: subscription_id, resource_group"` | config.py lines 73–75 |
| Missing service-principal fields | `ValueError` | `"Service principal credentials not configured"` | auth.py line 46 |

### 7.3 Re-raise on credential failure
`AzureAuthenticator.get_default_credential()` and `get_service_principal_credential()` log the error and then `raise` (bare re-raise), propagating the original exception to the caller rather than swallowing it (auth.py lines 37, 57).

---

## 8. Configuration System

The configuration system is layered, with environment variables always taking precedence over file-based values.

```
.env file  ──► os.environ  ──┐
                              ├──► self.config  (merged dict)
config.yaml ─────────────────┘
```

**Load order** (`Config._load_config()`, config.py lines 27–55):
1. If `config_file` is provided and the path exists, load the YAML into `self.config` via `yaml.safe_load()`.
2. For each of the five Azure keys, call `os.getenv(ENV_VAR, self.config.get(key))` — the environment variable wins if set, otherwise the YAML value is kept.

**Required fields** validated by `Config.validate()` (config.py lines 70–77):
- `subscription_id`
- `resource_group`

**Optional fields** (not validated, but loaded):
- `tenant_id`
- `client_id`
- `client_secret`

**Example YAML** (`examples/config.yaml`, lines 1–22):
```yaml
subscription_id: "your-subscription-id-here"
resource_group:  "your-resource-group-name"
tenant_id:       "your-tenant-id-here"
client_id:       "your-client-id-here"
client_secret:   "your-client-secret-here"
logging:
  level: "INFO"
  file:  "logs/avd_manager.log"
host_pools:
  - name: "production-pool"
    region: "eastus"
  - name: "development-pool"
    region: "westus"
```

**Application-level configuration sections:** The `logging` and `host_pools` sections are stored in `self.config` but are not read by any library code in the current version — they are available for application-level use via `config.get('logging')` and `config.get('host_pools')`. Example:
```python
config = Config('examples/config.yaml')
logging_config = config.get('logging')  # Returns {'level': 'INFO', 'file': 'logs/avd_manager.log'}
host_pools = config.get('host_pools')   # Returns list of dicts
```

---

## 9. Dependency and Service Wiring

The library uses **constructor injection** throughout. There is no IoC container or service-locator; dependencies are passed explicitly at object creation time.

```
Config
  └── (no dependencies on other avd_manager classes)

AzureAuthenticator
  └── (no dependencies on other avd_manager classes)

ConnectionManager(subscription_id, resource_group)
  └── imports AzureAuthenticator (available but not used internally)
  └── uses DefaultAzureCredential directly in authenticate()

SessionHandler(connection_manager: ConnectionManager)
  └── reads connection_manager.avd_client
  └── reads connection_manager.resource_group
```

**Authentication decision tree:**
1. Create `Config` object (loads `.env` and environment variables).
2. Call `config.validate()` to ensure required fields are present.
3. Create `ConnectionManager` with subscription ID and resource group from config.
4. Call `manager.connect()`:
   - Checks if `self.credential` is `None`.
   - If `None`, calls `authenticate()` to create `DefaultAzureCredential`.
   - Instantiates three Azure SDK clients using the credential.
5. Create `SessionHandler` with the connected `ConnectionManager`.
6. Call methods on `SessionHandler` to query sessions.
7. Call `manager.disconnect()` to release resources.

**Wiring example** from `examples/basic_usage.py` (lines 1–57):
```python
config          = Config()
config.set('subscription_id', '...')
config.set('resource_group',  '...')
config.validate()

manager         = ConnectionManager(
                      config.get('subscription_id'),
                      config.get('resource_group'))
manager.connect()

session_handler = SessionHandler(manager)
sessions        = session_handler.monitor_sessions('pool-name')
```

**Alternative with YAML:**
```python
config = Config('examples/config.yaml')
config.validate()

manager = ConnectionManager(
    config.get('subscription_id'),
    config.get('resource_group')
)
manager.connect()
```

**Alternative with `AzureAuthenticator` (not used by `ConnectionManager` internally, but available for custom wiring):**
```python
from avd_manager.utils.auth import AzureAuthenticator

authenticator = AzureAuthenticator(
    tenant_id='...',
    client_id='...',
    client_secret='...'
)
credential = authenticator.get_credential()  # Returns ClientSecretCredential

# Then use credential with custom Azure SDK clients
from azure.mgmt.desktopvirtualization import DesktopVirtualizationMgmtClient
client = DesktopVirtualizationMgmtClient(
    credential=credential,
    subscription_id='...'
)
```

---

## 10. External Dependencies

Declared in `QA-Test-Repo/requirements.txt` and `QA-Test-Repo/setup.py` (lines 10–18):

| Package | requirements.txt | setup.py | Role |
|---|---|---|---|
| `azure-identity` | `==1.15.0` | `>=1.15.0` | `DefaultAzureCredential`, `ClientSecretCredential` |
| `azure-mgmt-desktopvirtualization` | `==1.0.0` | `>=1.0.0` | `DesktopVirtualizationMgmtClient` (host pools, session hosts, user sessions) |
| `azure-mgmt-compute` | `==30.5.0` | `>=30.5.0` | `ComputeManagementClient` (instantiated in `connect()`, reserved for future use) |
| `azure-mgmt-network` | `==25.2.0` | `>=25.2.0` | `NetworkManagementClient` (instantiated in `connect()`, reserved for future use) |
| `python-dotenv` | `==1.0.0` | `>=1.0.0` | `load_dotenv()` called in `Config.__init__()` |
| `pyyaml` | `==6.0.1` | `>=6.0.1` | YAML file parsing in `Config._load_config()` and `Config.save()` |
| `requests` | `==2.31.0` | `>=2.31.0` | Listed as dependency; **not directly imported in current source** |

**Version constraint discrepancy:** `setup.py` uses `>=` minimum bounds (allowing newer versions) while `requirements.txt` pins exact versions (for reproducible installs). This is intentional:
- **Library consumers** who install via `pip install avd-manager` will get the minimum versions specified in `setup.py`, allowing flexibility.
- **Development and testing** use `requirements.txt` to ensure reproducible builds.

**Unused dependency:** `requests==2.31.0` is listed in both files but is not imported anywhere in the source code. It may be a transitive dependency of one of the Azure SDK packages, or it may be dead code. **Recommendation:** Verify whether `requests` is actually needed before removing it.

---

## 11. Testing Patterns

Tests live in `QA-Test-Repo/tests/` and use Python's built-in `unittest` framework.

### Test coverage

| Test class | File | Methods | Coverage |
|---|---|---|---|
| `TestConfig` | `tests/test_config.py` | 5 methods | `Config.__init__()`, `Config.get()`, `Config.set()`, `Config.validate()` |
| `TestConnectionManager` | `tests/test_connection_manager.py` | 4 methods | `ConnectionManager.__init__()`, `ConnectionManager.authenticate()`, `ConnectionManager.disconnect()` |

**Missing test classes:**
- `SessionHandler` — no `tests/test_session_handler.py` file; all five methods are completely untested.
- `AzureAuthenticator` — no `tests/test_auth.py` file; all three methods are completely untested.
- Logger utilities — no `tests/test_logger.py` file; `get_logger()` and `setup_file_logging()` are untested.

**Missing test coverage within existing classes:**
- `Config.save()` — no test exercises this method; `mock_open` is imported but unused.
- `Config._load_config()` YAML file-loading path — no test exercises the YAML file-loading branch.
- `ConnectionManager.connect()` — no test exercises the three SDK client instantiations.
- `ConnectionManager.list_host_pools()` and `get_host_pool()` — neither method has any test coverage.

### `setUp()` fixture pattern
Both test classes define `setUp()` to create shared test data and object instances before each test method runs, avoiding repetition:

```python
# tests/test_connection_manager.py lines 11–14
def setUp(self):
    self.subscription_id = "test-subscription-id"
    self.resource_group  = "test-resource-group"
    self.manager = ConnectionManager(self.subscription_id, self.resource_group)
```

```python
# tests/test_config.py lines 11–16
def setUp(self):
    self.test_config = {
        'subscription_id': 'test-sub-id',
        'resource_group':  'test-rg'
    }
```

**Note:** The `self.test_config` dict in `TestConfig.setUp()` is created but never actually used by any of the five test methods. It appears to be scaffolding for planned tests that were never written.

### Mocking Azure SDK calls
All Azure SDK interactions are mocked using `unittest.mock`. The `@patch` decorator replaces the real credential class at the import path used by the module under test:

```python
# tests/test_connection_manager.py lines 23–29
@patch('avd_manager.connection_manager.DefaultAzureCredential')
def test_authenticate_success(self, mock_credential):
    mock_credential.return_value = Mock()
    result = self.manager.authenticate()
    self.assertTrue(result)
    self.assertIsNotNone(self.manager.credential)
```

**Important:** The patch target must be the module where the name is used (e.g., `avd_manager.connection_manager.DefaultAzureCredential`), not where it is defined (e.g., `azure.identity.DefaultAzureCredential`). This is because Python's import system binds the name at the point of use.

Failure paths are tested by setting `side_effect` on the mock:

```python
# tests/test_connection_manager.py lines 31–34
@patch('avd_manager.connection_manager.DefaultAzureCredential')
def test_authenticate_failure(self, mock_credential):
    mock_credential.side_effect = Exception("Auth failed")
    result = self.manager.authenticate()
    self.assertFalse(result)
```

### Environment variable patching
`Config` tests use `@patch.dict(os.environ, {...})` to inject environment variables for the duration of a single test without affecting other tests:

```python
# tests/test_config.py lines 18–26
@patch.dict(os.environ, {
    'AZURE_SUBSCRIPTION_ID': 'env-sub-id',
    'AZURE_RESOURCE_GROUP':  'env-rg'
})
def test_load_from_environment(self):
    config = Config()
    self.assertEqual(config.get('subscription_id'), 'env-sub-id')
```

### Exception assertion pattern
`ValueError` raised by `Config.validate()` is asserted using the context-manager form:

```python
# tests/test_config.py lines 52–54
def test_validate_failure(self):
    config = Config()
    with self.assertRaises(ValueError):
        config.validate()
```

### Test gaps
**`test_initialization` gap:** The test at `tests/test_connection_manager.py` (line 17) only asserts `credential` and `avd_client` are `None` on init; `compute_client` and `network_client` are not asserted, creating a gap between the documented internal state table and test coverage.

**`test_disconnect` gap:** The test at `tests/test_connection_manager.py` (line 40) only sets and checks `credential` and `avd_client`; it does not verify that `compute_client` and `network_client` are also set to `None` after `disconnect()`, which is documented behaviour in Section 5.

### Running the test suite
```bash
python -m unittest discover tests
```
As documented in `README.md` (line 75) and `CONTRIBUTING.md` (line 19).

---

## 12. Example Usage

The complete runnable example is in `QA-Test-Repo/examples/basic_usage.py`. The canonical workflow is:

```python
from avd_manager import ConnectionManager, SessionHandler, Config

# 1. Configure
config = Config()                              # loads .env + env vars
config.set('subscription_id', 'your-sub-id')
config.set('resource_group',  'your-rg')
config.validate()                              # raises ValueError if incomplete

# 2. Connect
manager = ConnectionManager(
    config.get('subscription_id'),
    config.get('resource_group')
)
manager.connect()                              # authenticate + create SDK clients

# 3. Enumerate host pools
host_pools = manager.list_host_pools()
for pool in host_pools:
    pool_name = pool.name.split('/')[-1]
    pool_details = manager.get_host_pool(pool_name)
    if pool_details:
        print(f"Pool: {pool_details.name}")
        print(f"Type: {pool_details.host_pool_type}")
        print(f"Load Balancer: {pool_details.load_balancer_type}")

# 4. Monitor sessions
session_handler = SessionHandler(manager)
sessions = session_handler.monitor_sessions(pool_name)
print(f"Active sessions: {len(sessions)}")

# 5. Get session host status
for host in session_handler.list_session_hosts(pool_name):
    host_name = host.name.split('/')[-1]
    status = session_handler.get_session_host_status(pool_name, host_name)
    if status:
        print(f"Host: {status['name']}")
        print(f"Status: {status['status']}")
        print(f"Sessions: {status['sessions']}")
        print(f"Last Heartbeat: {status['last_heartbeat']}")

# 6. Disconnect user session (example)
# sessions = session_handler.get_user_sessions(pool_name, host_name)
# if sessions:
#     session_id = sessions[0].id
#     success = session_handler.disconnect_user_session(pool_name, host_name, session_id)

# 7. Disconnect
manager.disconnect()
```

### YAML-based configuration

For YAML-based configuration, supply the file path to `Config`:
```python
config = Config('examples/config.yaml')
config.validate()

manager = ConnectionManager(
    config.get('subscription_id'),
    config.get('resource_group')
)
manager.connect()
```

The YAML file format is documented in `QA-Test-Repo/examples/config.yaml`.

### File logging setup

To enable persistent file logging, call `setup_file_logging()` at application startup:
```python
from avd_manager.utils.logger import setup_file_logging
import logging

# At application startup
setup_file_logging('logs/avd_manager.log', level=logging.INFO)

# Now all loggers (including third-party libraries) will write to the file
config = Config('examples/config.yaml')
# ... rest of application ...
```

### Saving modified configuration

To save a modified configuration back to disk:
```python
config = Config('examples/config.yaml')
config.set('subscription_id', 'new-value')
config.save('examples/config_updated.yaml')
```

### Using `AzureAuthenticator` for service-principal authentication

To use explicit service-principal credentials instead of default credentials:
```python
from avd_manager.utils.auth import AzureAuthenticator
from avd_manager import ConnectionManager
from azure.mgmt.desktopvirtualization import DesktopVirtualizationMgmtClient

authenticator = AzureAuthenticator(
    tenant_id='your-tenant-id',
    client_id='your-client-id',
    client_secret='your-client-secret'
)

credential = authenticator.get_credential()  # Returns ClientSecretCredential

# Use credential with Azure SDK clients directly
avd_client = DesktopVirtualizationMgmtClient(
    credential=credential,
    subscription_id='your-subscription-id'
)

# Or use with ConnectionManager by manually setting the credential
manager = ConnectionManager('your-subscription-id', 'your-resource-group')
manager.credential = credential
manager.connect()  # Will skip authenticate() since credential is already set
```

### Accessing application-level configuration sections

The `logging` and `host_pools` sections in the YAML file are available for application-level use:
```python
config = Config('examples/config.yaml')

# Access logging configuration
logging_config = config.get('logging')
print(f"Log level: {logging_config['level']}")
print(f"Log file: {logging_config['file']}")

# Access host pools configuration
host_pools = config.get('host_pools')
for pool in host_pools:
    print(f"Pool: {pool['name']} in {pool['region']}")
```

---

## Appendix: Known Issues and Limitations

### 1. Empty YAML file handling
If a YAML configuration file is empty or contains only comments, `yaml.safe_load()` returns `None`. The code does not guard against this, so `self.config` would be set to `None`, causing `AttributeError` on subsequent `.get()` calls.

**Workaround:** Ensure YAML files contain at least one key-value pair.

### 2. YAML type coercion
YAML values are parsed natively by `yaml.safe_load()`. Unquoted integers and booleans are parsed as `int` and `bool` types, not strings. This may cause downstream type errors in Azure SDK calls.

**Workaround:** Always quote string values in YAML files:
```yaml
subscription_id: "12345"  # String, not int
```

### 3. Duplicate handler guard in `get_logger()`
The guard `if not logger.handlers` means that if `get_logger('foo', logging.DEBUG)` is called after `get_logger('foo', logging.INFO)`, the level change is silently ignored.

**Workaround:** To change the level of an existing logger, call `logging.getLogger('foo').setLevel(new_level)` directly.

### 4. Global side effect of `setup_file_logging()`
This function attaches a handler to the root logger, which means all loggers in the process (including third-party libraries) will write to the file. This is a global side effect.

**Recommendation:** Call this once at application startup.

### 5. Unsafe pattern in `examples/basic_usage.py`
The example calls `pool_details.host_pool_type` without checking for `None`:
```python
pool_details = manager.get_host_pool(pool_name)
print(f"Type: {pool_details.host_pool_type}")  # AttributeError if pool_details is None
```

**Recommendation:** Always check for `None`:
```python
pool_details = manager.get_host_pool(pool_name)
if pool_details:
    print(f"Type: {pool_details.host_pool_type}")
```

### 6. Partial-failure state in `ConnectionManager.connect()`
If `DesktopVirtualizationMgmtClient` instantiation succeeds but `ComputeManagementClient` raises an exception, `avd_client` will be set but `compute_client` and `network_client` will be `None`, and `connect()` returns `False`. The object is left in a partially-connected state.

**Recommendation:** Check the return value of `connect()` before proceeding.

### 7. Unused import in `session_handler.py`
`from datetime import datetime` is imported at line 3 but never used anywhere in the file.

### 8. Unused dependency
`requests==2.31.0` is listed in `requirements.txt` and `setup.py` but is not imported anywhere in the source code.

### 9. Missing test coverage
- `SessionHandler` — all five methods are completely untested.
- `AzureAuthenticator` — all three methods are completely untested.
- Logger utilities — `get_logger()` and `setup_file_logging()` are untested.
- `Config.save()` — no test exercises this method.
- `Config._load_config()` YAML file-loading path — no test exercises the YAML file-loading branch.
- `ConnectionManager.connect()` — no test exercises the three SDK client instantiations.
- `ConnectionManager.list_host_pools()` and `get_host_pool()` — neither method has any test coverage.

### 10. Docstring incompleteness
All public methods except `__init__` have only one-line docstrings with no `Args:`, `Returns:`, or `Raises:` sections. This violates the stated convention in `CONTRIBUTING.md` (line 28: "Add docstrings to all functions and classes").

### 11. Project structure discrepancy
`README.md` (line 87) lists a `docs/` directory in the project structure, but no such directory exists in the repository.

### 12. `find_packages()` scope
`setup.py` (line 9) uses `find_packages()` without exclusions, which will discover both `avd_manager` and `tests` packages. The `tests` package will be included in the distribution. **Recommendation:** Use `find_packages(exclude=['tests'])` to exclude the test package from the distribution.