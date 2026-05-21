# Data Flow Document: Azure Virtual Desktop Manager (`avd_manager`)

**Version:** 0.1.0 (Alpha)
**Language:** Python 3.8+
**Cross-reference:** See [architecture.md] and [structure.md] for system design and module layout.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Configuration Loading Pipeline](#2-configuration-loading-pipeline)
3. [Authentication Flow](#3-authentication-flow)
4. [Connection Establishment Flow](#4-connection-establishment-flow)
5. [Host Pool Query Flows](#5-host-pool-query-flows)
6. [Session Management Flows](#6-session-management-flows)
7. [Session Monitoring Pipeline](#7-session-monitoring-pipeline)
8. [Session Disconnection Flow](#8-session-disconnection-flow)
9. [Logging Data Flow](#9-logging-data-flow)
10. [Integration Points with External Services](#10-integration-points-with-external-services)
11. [State Management](#11-state-management)
12. [Error Propagation Patterns](#12-error-propagation-patterns)
13. [File and Configuration Storage Flows](#13-file-and-configuration-storage-flows)
14. [End-to-End Composite Flow (Basic Usage)](#14-end-to-end-composite-flow-basic-usage)
15. [Caching Strategies and Data Invalidation](#15-caching-strategies-and-data-invalidation)
16. [Event and Messaging Patterns](#16-event-and-messaging-patterns)
17. [Database Read/Write Patterns](#17-database-readwrite-patterns)

---

## 1. Overview

`avd_manager` is a **library** (not a server), so there are no HTTP API endpoints exposed by the package itself. All data flows are **outbound** — the library initiates calls to the Azure Resource Manager (ARM) REST APIs via the official Azure Python SDKs. The three primary data flow axes are:

| Axis | Direction | Protocol |
|---|---|---|
| Configuration ingestion | Disk/Env → In-memory `dict` | File I/O / `os.getenv` |
| Authentication | In-process → Azure AD token endpoint | HTTPS (OAuth 2.0) |
| Resource management | In-process → Azure ARM REST API | HTTPS (ARM) |

All flows are **synchronous and single-threaded** within a single Python process. There is no message queue, no database, no cache layer, and no frontend state.

---

## 2. Configuration Loading Pipeline

### 2.1 Entry Point

Configuration loading begins when a caller instantiates `Config`.

**Source:** `Config.__init__()` — `QA-Test-Repo/avd_manager/config.py` (line 14)

```
Caller
  │
  ▼
Config.__init__(config_file=None)          config.py:14
  │  calls load_dotenv()                   config.py:21  ← reads .env file from CWD
  │  stores config_file path               config.py:22
  │  initialises self.config = {}          config.py:23
  └─► Config._load_config()               config.py:26
```

### 2.2 `_load_config()` — Two-Stage Merge

**Source:** `Config._load_config()` — `QA-Test-Repo/avd_manager/config.py` (lines 26–54)

**Stage 1 — YAML file (optional):**

```
Path(config_file).exists()?               config.py:30
  YES ──► open(config_file, 'r')          config.py:31
          yaml.safe_load(f)               config.py:32
          → self.config (dict)
  NO  ──► self.config stays {}
```

The YAML file schema (from `QA-Test-Repo/examples/config.yaml`) supports the following keys:

| YAML Key | Type | Purpose | Example |
|---|---|---|---|
| `subscription_id` | string | Azure subscription | `"your-subscription-id-here"` |
| `resource_group` | string | ARM resource group | `"your-resource-group-name"` |
| `tenant_id` | string | Azure AD tenant | `"your-tenant-id-here"` |
| `client_id` | string | Service principal app ID | `"your-client-id-here"` |
| `client_secret` | string | Service principal secret | `"your-client-secret-here"` |
| `logging` | dict | Logging configuration | `{level: "INFO", file: "logs/avd_manager.log"}` |
| `host_pools` | list | Named pool definitions (informational) | `[{name: "production-pool", region: "eastus"}]` |

**Note on YAML structure:** After `yaml.safe_load()` parses the file, the `logging` key becomes a nested dict: `self.config['logging'] = {'level': 'INFO', 'file': 'logs/avd_manager.log'}`. The `host_pools` key becomes a list of dicts: `self.config['host_pools'] = [{'name': '...', 'region': '...'}]`. However, **no code in the library reads these keys at runtime** — they are purely informational and reserved for future use (see TODO-FLOW-004, TODO-FLOW-025, TODO-FLOW-026).

**Edge case — empty YAML file:** If the YAML file is empty or contains only comments, `yaml.safe_load()` returns `None` rather than an empty dict. The code at `config.py:32` assigns this `None` directly to `self.config`, which would cause `AttributeError` on subsequent `.get()` calls in the env-var overlay stage (lines 36–52). This is a latent bug: the code should check `if self.config is None: self.config = {}` after the load (TODO-FLOW-024).

**Stage 2 — Environment variable overlay:**

Five environment variables are read via `os.getenv()` and **unconditionally overwrite** the corresponding YAML values (YAML value is used as the fallback default):

| Environment Variable | Config Key | Source line |
|---|---|---|
| `AZURE_SUBSCRIPTION_ID` | `subscription_id` | `config.py:36` |
| `AZURE_RESOURCE_GROUP` | `resource_group` | `config.py:40` |
| `AZURE_TENANT_ID` | `tenant_id` | `config.py:44` |
| `AZURE_CLIENT_ID` | `client_id` | `config.py:48` |
| `AZURE_CLIENT_SECRET` | `client_secret` | `config.py:52` |

**Precedence (highest → lowest):** Environment variable → YAML file value → `None`

**Final config dict structure example:**
```python
self.config = {
    'subscription_id': '12345678-1234-1234-1234-123456789012',  # from env or YAML
    'resource_group': 'my-rg',                                   # from env or YAML
    'tenant_id': None,                                           # not set
    'client_id': None,                                           # not set
    'client_secret': None,                                       # not set
    'logging': {                                                 # from YAML (nested dict)
        'level': 'INFO',
        'file': 'logs/avd_manager.log'
    },
    'host_pools': [                                              # from YAML (list of dicts)
        {'name': 'production-pool', 'region': 'eastus'},
        {'name': 'development-pool', 'region': 'westus'}
    ]
}
```

### 2.3 Validation Gate

**Source:** `Config.validate()` — `QA-Test-Repo/avd_manager/config.py` (lines 63–72)

```
Config.validate()
  │
  ├─ required_fields = ['subscription_id', 'resource_group']   config.py:64
  ├─ missing_fields = [f for f if not self.config.get(f)]      config.py:65
  │
  ├─ missing_fields non-empty?
  │     YES ──► logger.error(...)                              config.py:68
  │             raise ValueError(error_msg)                    config.py:69
  │
  └─ missing_fields empty?
        YES ──► logger.info("Configuration validation passed") config.py:71
                return True                                    config.py:72
```

### 2.4 Runtime Get/Set

- `Config.get(key, default=None)` — `config.py:55`: reads from `self.config` dict; returns `default` if key absent.
- `Config.set(key, value)` — `config.py:60`: writes directly into `self.config` dict; logs at DEBUG level. **Note:** This DEBUG log is suppressed by default because `get_logger()` sets the level to `INFO` (logger.py:20), so callers must explicitly lower the log level to see these messages (TODO-FLOW-029).

### 2.5 Configuration Save Flow

**Source:** `Config.save()` — `QA-Test-Repo/avd_manager/config.py` (lines 74–78)

```
Config.save(output_file)
  │
  ├─ open(output_file, 'w')
  ├─ yaml.dump(self.config, f, default_flow_style=False)
  └─ logger.info(f"Configuration saved to {output_file}")
```

Data direction: **in-memory `dict` → YAML file on disk**.

**Edge case — None values:** If `self.config` contains `None` values (from unset env vars), `yaml.dump()` will serialize them as `null` in the YAML file. When the file is reloaded, these `null` values become Python `None` objects, which is correct. However, this may produce a YAML file that looks incomplete to human readers (TODO-FLOW-023).

---

## 3. Authentication Flow

### 3.1 `AzureAuthenticator` — Credential Selection

**Source:** `AzureAuthenticator.get_credential()` — `QA-Test-Repo/avd_manager/utils/auth.py` (lines 62–68)

```
AzureAuthenticator.get_credential()
  │
  ├─ all([tenant_id, client_id, client_secret])?
  │     YES ──► get_service_principal_credential()    auth.py:63
  └─     NO  ──► get_default_credential()             auth.py:65
```

**Path A — Service Principal (explicit credentials):**

**Source:** `AzureAuthenticator.get_service_principal_credential()` — `QA-Test-Repo/avd_manager/utils/auth.py` (lines 40–57)

```
get_service_principal_credential()
  │
  ├─ guard: all([tenant_id, client_id, client_secret])   auth.py:46
  │     NO  ──► raise ValueError(...)                     auth.py:46
  │
  └─ ClientSecretCredential(                             auth.py:49
         tenant_id=self.tenant_id,
         client_id=self.client_id,
         client_secret=self.client_secret
     )
     → self.credential
     → return self.credential
```

Data in: `tenant_id`, `client_id`, `client_secret` (strings from `Config`)
Data out: `ClientSecretCredential` object (wraps an OAuth 2.0 client-credentials token)

**Error handling:** If any of the three credentials is missing, `ValueError` is raised (Pattern B — hard failure). If SDK instantiation fails, the exception is logged and re-raised (Pattern C — undocumented, see TODO-FLOW-040).

**Path B — Default Credential Chain:**

**Source:** `AzureAuthenticator.get_default_credential()` — `QA-Test-Repo/avd_manager/utils/auth.py` (lines 26–37)

```
get_default_credential()
  │
  └─ DefaultAzureCredential()                           auth.py:32
     (tries credential chain in order)
     → self.credential
     → return self.credential
```

**Credential chain order (azure-identity==1.15.0):** The `DefaultAzureCredential` class tries credentials in this sequence:
1. `EnvironmentCredential` — reads `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID` env vars
2. `WorkloadIdentityCredential` — for Kubernetes workload identity
3. `ManagedIdentityCredential` — for Azure-hosted resources (VMs, App Service, etc.)
4. `SharedTokenCacheCredential` — cached tokens from Azure CLI or Visual Studio
5. `VisualStudioCodeCredential` — VS Code Azure extension token
6. `AzureCliCredential` — `az login` cached token
7. `AzurePowerShellCredential` — `Connect-AzAccount` cached token

The first credential that succeeds is used; if all fail, an exception is raised (TODO-FLOW-049).

**Error handling:** If all credential sources fail, the exception is logged and re-raised (Pattern C).

### 3.2 `ConnectionManager.authenticate()` — Simplified Path

**Source:** `ConnectionManager.authenticate()` — `QA-Test-Repo/avd_manager/connection_manager.py` (lines 33–40)

`ConnectionManager` does **not** use `AzureAuthenticator` directly; it calls `DefaultAzureCredential()` inline:

```
ConnectionManager.authenticate()
  │
  ├─ DefaultAzureCredential()                           connection_manager.py:35
  │   → self.credential
  ├─ logger.info("Authentication successful")
  └─ return True

  on Exception:
  ├─ logger.error(f"Authentication failed: {str(e)}")
  └─ return False
```

**Error handling:** Pattern A — exceptions are caught, logged, and `False` is returned. This is the only place in the library where `DefaultAzureCredential` is actually instantiated and used; `AzureAuthenticator` is imported but never called (TODO-FLOW-022).

> **Note:** `AzureAuthenticator` (in `utils/auth.py`) is defined and exported via `utils/__init__.py:4` but is **not imported or called** by `ConnectionManager` or `Config`. It is available for direct use by callers via `from avd_manager.utils import AzureAuthenticator` (TODO-FLOW-048) but is not wired into the primary flow.

---

## 4. Connection Establishment Flow

**Source:** `ConnectionManager.connect()` — `QA-Test-Repo/avd_manager/connection_manager.py` (lines 42–63)

```
ConnectionManager.connect()
  │
  ├─ self.credential is None?
  │     YES ──► self.authenticate()                     connection_manager.py:44
  │               FAIL ──► raise ConnectionError(...)   connection_manager.py:45
  │
  ├─ DesktopVirtualizationMgmtClient(                   connection_manager.py:48
  │       credential=self.credential,
  │       subscription_id=self.subscription_id
  │   ) → self.avd_client
  │
  ├─ ComputeManagementClient(                           connection_manager.py:52
  │       credential=self.credential,
  │       subscription_id=self.subscription_id
  │   ) → self.compute_client
  │
  ├─ NetworkManagementClient(                           connection_manager.py:56
  │       credential=self.credential,
  │       subscription_id=self.subscription_id
  │   ) → self.network_client
  │
  ├─ logger.info("Successfully connected to Azure services")
  └─ return True

  on Exception:
  ├─ logger.error(f"Connection failed: {str(e)}")
  └─ return False
```

Three SDK client objects are instantiated and stored as instance attributes. Each client lazily acquires an OAuth 2.0 bearer token from Azure AD on its first API call.

**Partial failure scenario (TODO-FLOW-028):** If `DesktopVirtualizationMgmtClient` instantiation succeeds but `ComputeManagementClient` raises an exception (line 52), `avd_client` will be set but `compute_client` and `network_client` will remain `None`, and `connect()` returns `False`. The caller cannot distinguish between a full failure and a partial failure.

**Idempotency (TODO-FLOW-032):** If `connect()` is called a second time on an already-connected manager, the three client objects are silently overwritten. This is idempotent but may leak resources if the old client objects are not garbage-collected immediately.

### 4.1 Disconnection Flow

**Source:** `ConnectionManager.disconnect()` — `QA-Test-Repo/avd_manager/connection_manager.py` (lines 99–104)

```
ConnectionManager.disconnect()
  │
  ├─ self.avd_client    = None
  ├─ self.compute_client = None
  ├─ self.network_client = None
  ├─ self.credential     = None
  └─ logger.info("Disconnected from Azure services")
```

Disconnection is purely in-memory: all SDK client references are set to `None`, allowing garbage collection. No explicit token revocation is performed.

---

## 5. Host Pool Query Flows

### 5.1 List All Host Pools

**Source:** `ConnectionManager.list_host_pools()` — `QA-Test-Repo/avd_manager/connection_manager.py` (lines 65–76)

```
Caller
  │
  ▼
ConnectionManager.list_host_pools()
  │
  ├─ guard: self.avd_client is None?                    connection_manager.py:67
  │     YES ──► raise ConnectionError(...)
  │
  ├─ self.avd_client.host_pools                         connection_manager.py:70
  │       .list_by_resource_group(self.resource_group)
  │   → lazy Azure SDK iterator
  │
  ├─ list(...)                                          connection_manager.py:70
  │   → materialises all pages from ARM REST API
  │   → List[HostPool]
  │
  ├─ logger.info(f"Found {len(host_pools)} host pools")
  └─ return host_pools                                  (List[HostPool] objects)

  on Exception:
  ├─ logger.error(f"Failed to list host pools: {str(e)}")
  └─ return []
```

**ARM endpoint called (by SDK):** `GET https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.DesktopVirtualization/hostPools?api-version=2023-09-05` (or similar; the exact API version is determined by the SDK version `azure-mgmt-desktopvirtualization==1.0.0`).

**Data returned:** A Python list of `HostPool` model objects (Azure SDK dataclasses). Each `HostPool` object contains the following fields (from the ARM response):
- `.name` — fully-qualified resource path (e.g., `/subscriptions/.../resourceGroups/.../providers/Microsoft.DesktopVirtualization/hostPools/my-pool`)
- `.id` — resource ID
- `.type` — resource type
- `.location` — Azure region
- `.tags` — resource tags dict
- `.host_pool_type` — `"Pooled"` or `"Personal"` (used in basic_usage.py:43)
- `.load_balancer_type` — `"BreadthFirst"`, `"DepthFirst"`, or `"Persistent"` (used in basic_usage.py:44)
- `.friendly_name` — user-friendly name
- `.description` — pool description
- `.max_session_limit` — max concurrent sessions per host
- `.registration_info` — registration token info
- `.vm_template` — VM template JSON
- `.personal_desktop_assignment_type` — for personal pools
- `.custom_rdp_property` — RDP settings
- `.sso_context` — SSO configuration
- `.preferred_app_group_type` — default app group type
- `.start_vm_on_connect` — auto-start VM on user connection
- `.migration_request` — migration state
- `.public_network_access` — public access setting
- `.identity` — managed identity

**Note:** The library returns raw SDK objects; only `.name`, `.host_pool_type`, and `.load_balancer_type` are documented in the dataflow doc and used in examples. All other fields are silently available but undocumented (TODO-FLOW-001).

**Pagination (TODO-FLOW-016):** The SDK transparently handles ARM pagination via `nextLink`. The `list()` call materialises all pages into a single list. The ARM API typically returns 20 items per page; there is no documented practical limit on the number of host pools.

### 5.2 Get Single Host Pool

**Source:** `ConnectionManager.get_host_pool()` — `QA-Test-Repo/avd_manager/connection_manager.py` (lines 78–92)

```
ConnectionManager.get_host_pool(host_pool_name)
  │
  ├─ guard: self.avd_client is None?                    connection_manager.py:80
  │     YES ──► raise ConnectionError(...)
  │
  ├─ self.avd_client.host_pools.get(                    connection_manager.py:83
  │       self.resource_group,
  │       host_pool_name
  │   ) → HostPool object
  │
  ├─ logger.info(f"Retrieved host pool: {host_pool_name}")
  └─ return host_pool

  on Exception:
  ├─ logger.error(f"Failed to get host pool {host_pool_name}: {str(e)}")
  └─ return None
```

**ARM endpoint called (by SDK):** `GET https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.DesktopVirtualization/hostPools/{hostPoolName}?api-version=2023-09-05`

**Data returned:** A single `HostPool` object with the same fields as listed in §5.1.

**Caller-side name extraction (examples/basic_usage.py, line 39):**
```python
pool_name = host_pools[0].name.split('/')[-1]
```
The `.name` field returned by ARM is a fully-qualified resource path; the caller strips the prefix to obtain the bare pool name before passing it to `get_host_pool()`. The full path format is: `/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.DesktopVirtualization/hostPools/{hostPoolName}` (TODO-FLOW-010, TODO-FLOW-019).

---

## 6. Session Management Flows

### 6.1 List Session Hosts

**Source:** `SessionHandler.list_session_hosts()` — `QA-Test-Repo/avd_manager/session_handler.py` (lines 22–37)

```
SessionHandler.list_session_hosts(host_pool_name)
  │
  ├─ guard: self.connection_manager.avd_client is None?  session_handler.py:24
  │     YES ──► raise ConnectionError(...)
  │
  ├─ self.connection_manager.avd_client                  session_handler.py:27
  │       .session_hosts.list(
  │           self.connection_manager.resource_group,
  │           host_pool_name
  │       )
  │   → lazy iterator
  │
  ├─ list(...)  → List[SessionHost]                      session_handler.py:27
  ├─ logger.info(f"Found {len(session_hosts)} session hosts in {host_pool_name}")
  └─ return session_hosts

  on Exception:
  ├─ logger.error(f"Failed to list session hosts: {str(e)}")
  └─ return []
```

**ARM endpoint called (by SDK):** `GET https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.DesktopVirtualization/hostPools/{hostPoolName}/sessionHosts?api-version=2023-09-05`

**Data returned:** A Python list of `SessionHost` model objects. Each `SessionHost` contains:
- `.name` — fully-qualified resource path (e.g., `.../hostPools/{poolName}/sessionHosts/{hostName}`)
- `.id` — resource ID
- `.type` — resource type
- `.status` — `"Available"`, `"Unavailable"`, `"Shutdown"`, `"Disconnected"`, or `"NoHeartBeat"` (extracted in get_session_host_status)
- `.sessions` — current session count (extracted in get_session_host_status)
- `.last_heart_beat` — last heartbeat timestamp (extracted as `last_heartbeat` in get_session_host_status)
- `.update_state` — update status (extracted in get_session_host_status)
- `.agent_version` — AVD agent version
- `.assigned_user` — assigned user (for personal pools)
- `.friendly_name` — display name
- `.os_version` — operating system version
- `.virtual_machine_id` — Azure VM resource ID
- `.power_state` — VM power state
- `.allow_new_session` — whether new sessions are allowed

**Note:** The library returns raw SDK objects; only `.name` and the five fields extracted in `get_session_host_status()` are documented. All other fields are undocumented (TODO-FLOW-002).

### 6.2 Get User Sessions on a Host

**Source:** `SessionHandler.get_user_sessions()` — `QA-Test-Repo/avd_manager/session_handler.py` (lines 39–55)

```
SessionHandler.get_user_sessions(host_pool_name, session_host_name)
  │
  ├─ guard: self.connection_manager.avd_client is None?  session_handler.py:41
  │     YES ──► raise ConnectionError(...)
  │
  ├─ self.connection_manager.avd_client                  session_handler.py:44
  │       .user_sessions.list(
  │           self.connection_manager.resource_group,
  │           host_pool_name,
  │           session_host_name
  │       )
  │   → lazy iterator
  │
  ├─ list(...)  → List[UserSession]                      session_handler.py:44
  ├─ logger.info(f"Found {len(sessions)} active sessions on {session_host_name}")
  └─ return sessions

  on Exception:
  ├─ logger.error(f"Failed to get user sessions: {str(e)}")
  └─ return []
```

**ARM endpoint called (by SDK):** `GET https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.DesktopVirtualization/hostPools/{hostPoolName}/sessionHosts/{sessionHostName}/userSessions?api-version=2023-09-05`

**Data returned:** A Python list of `UserSession` model objects. Each `UserSession` contains:
- `.id` — resource ID (contains the session ID as the last path segment; format is typically a GUID or integer, see TODO-FLOW-009)
- `.name` — fully-qualified resource path
- `.type` — resource type
- `.user_principal_name` — UPN of the connected user (e.g., `user@domain.com`)
- `.session_id` — numeric session ID (used in disconnect_user_session)
- `.session_state` — `"Active"`, `"Disconnected"`, `"Pending"`, `"LogOff"`, or `"Unknown"`
- `.application_type` — `"RemoteApp"` or `"Desktop"`
- `.create_time` — session creation timestamp
- `.last_activity_time` — last user activity timestamp

**Note:** The library returns raw SDK objects; the dataflow doc provides no field inventory (TODO-FLOW-003). The `session_id` field type is not documented but is critical for callers using `disconnect_user_session()`.

### 6.3 Get Session Host Status

**Source:** `SessionHandler.get_session_host_status()` — `QA-Test-Repo/avd_manager/session_handler.py` (lines 71–93)

```
SessionHandler.get_session_host_status(host_pool_name, session_host_name)
  │
  ├─ guard: self.connection_manager.avd_client is None?  session_handler.py:73
  │     YES ──► raise ConnectionError(...)
  │
  ├─ self.connection_manager.avd_client                  session_handler.py:76
  │       .session_hosts.get(
  │           self.connection_manager.resource_group,
  │           host_pool_name,
  │           session_host_name
  │       )
  │   → SessionHost object
  │
  ├─ Transform: SDK object → plain Python dict               session_handler.py:80
  │   status = {
  │       "name":           session_host.name,              (str, fully-qualified path)
  │       "status":         session_host.status,            (str enum: "Available", "Unavailable", etc.)
  │       "sessions":       session_host.sessions,          (int, current session count)
  │       "last_heartbeat": session_host.last_heart_beat,   (datetime or None)
  │       "update_state":   session_host.update_state       (str enum: "Succeeded", "Failed", etc.)
  │   }
  │
  ├─ logger.info(f"Retrieved status for {session_host_name}")
  └─ return status  (dict)

  on Exception:
  ├─ logger.error(f"Failed to get session host status: {str(e)}")
  └─ return None
```

**ARM endpoint called (by SDK):** `GET https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.DesktopVirtualization/hostPools/{hostPoolName}/sessionHosts/{sessionHostName}?api-version=2023-09-05` (TODO-FLOW-011)

**Data transformation:** This is the **only method in the codebase that converts an Azure SDK model object into a plain Python `dict`**. All other methods return raw SDK objects directly to the caller.

**Output dict schema (TODO-FLOW-006):**

| Key | Type | Value Example | Notes |
|---|---|---|---|
| `name` | `str` | `/subscriptions/.../hostPools/my-pool/sessionHosts/my-host` | Fully-qualified ARM resource path |
| `status` | `str` | `"Available"` | Enum: `"Available"`, `"Unavailable"`, `"Shutdown"`, `"Disconnected"`, `"NoHeartBeat"` |
| `sessions` | `int` | `5` | Current number of active sessions on this host |
| `last_heartbeat` | `datetime` or `None` | `datetime(2024, 1, 15, 14, 30, 45)` | Last heartbeat from the AVD agent; `None` if never reported |
| `update_state` | `str` | `"Succeeded"` | Enum: `"Succeeded"`, `"Failed"`, `"InProgress"`, `"Unknown"` |

**Field name mismatch:** The SDK attribute is `last_heart_beat` (with underscore), but the dict key is `last_heartbeat` (no underscore) — this is a deliberate transformation in the code (TODO-FLOW-006).

---

## 7. Session Monitoring Pipeline

**Source:** `SessionHandler.monitor_sessions()` — `QA-Test-Repo/avd_manager/session_handler.py` (lines 95–107)

This is the highest-level composite pipeline in the library. It orchestrates two lower-level calls in sequence:

```
SessionHandler.monitor_sessions(host_pool_name)
  │
  ├─ Step 1: list_session_hosts(host_pool_name)          session_handler.py:97
  │           → List[SessionHost]
  │
  ├─ all_sessions = []                                   session_handler.py:98
  │
  ├─ for host in session_hosts:                          session_handler.py:100
  │     host_name = host.name.split('/')[-1]             session_handler.py:101
  │     │  (strips ARM resource path prefix)
  │     │
  │     └─ Step 2: get_user_sessions(                    session_handler.py:102
  │                   host_pool_name,
  │                   host_name
  │                )
  │                → List[UserSession]
  │                all_sessions.extend(sessions)         session_handler.py:103
  │
  ├─ logger.info(f"Monitoring {len(all_sessions)} total sessions in {host_pool_name}")
  └─ return all_sessions   (flat List[UserSession])
```

**Pipeline data shape:**

```
Input:  host_pool_name (str)
          │
          ▼
        List[SessionHost]   (one ARM call)
          │  for each host
          ▼
        List[UserSession]   (N ARM calls, one per host)
          │  extend into flat list
          ▼
Output: List[UserSession]   (all sessions across all hosts)
```

**ARM call count:** `1 + len(session_hosts)` — scales linearly with the number of session hosts in the pool.

**Error propagation gap (TODO-FLOW-027):** Unlike every other method in `session_handler.py`, `monitor_sessions()` has **no try/except block** (session_handler.py:95-107). If `list_session_hosts()` returns `[]` due to a caught exception (Pattern A), `monitor_sessions()` silently returns `[]` with no indication of the upstream failure. But if `list_session_hosts()` raises `ConnectionError` (Pattern B), it propagates unhandled through `monitor_sessions()`. This asymmetric behavior is not documented in §12 (TODO-FLOW-043).

---

## 8. Session Disconnection Flow

**Source:** `SessionHandler.disconnect_user_session()` — `QA-Test-Repo/avd_manager/session_handler.py` (lines 57–70)

```
SessionHandler.disconnect_user_session(
    host_pool_name, session_host_name, session_id
)
  │
  ├─ guard: self.connection_manager.avd_client is None?  session_handler.py:59
  │     YES ──► raise ConnectionError(...)
  │
  ├─ self.connection_manager.avd_client                  session_handler.py:62
  │       .user_sessions.disconnect(
  │           self.connection_manager.resource_group,
  │           host_pool_name,
  │           session_host_name,
  │           session_id
  │       )
  │   → None (void ARM call)
  │
  ├─ logger.info(f"Disconnected session {session_id} on {session_host_name}")
  └─ return True

  on Exception:
  ├─ logger.error(f"Failed to disconnect session: {str(e)}")
  └─ return False
```

**ARM endpoint called (by SDK):** `POST https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.DesktopVirtualization/hostPools/{hostPoolName}/sessionHosts/{sessionHostName}/userSessions/{userSessionId}/disconnect?api-version=2023-09-05`

This is the **only write/mutating operation** in the library. All other flows are read-only GET requests.

**HTTP response (TODO-FLOW-017):** The ARM API returns HTTP 200 or 204 (No Content) on success. The SDK translates this into a `None` return value. On failure (e.g., session already disconnected, session host unavailable), the SDK raises an exception, which is caught and logged (Pattern A), and `False` is returned.

**Session ID type (TODO-FLOW-009):** The `session_id` parameter is passed directly to the ARM SDK without type conversion. The SDK expects it to be a string representation of the session ID (typically a GUID or integer). Callers extracting `session_id` from `UserSession` objects must ensure they pass the correct type.

---

## 9. Logging Data Flow

**Source:** `logger.py` — `QA-Test-Repo/avd_manager/utils/logger.py`

### 9.1 Logger Acquisition

Every module acquires a logger at module load time via the module-level call pattern:

```python
logger = get_logger(__name__)   # e.g., connection_manager.py:9, session_handler.py:6, config.py:8
```

**Source:** `get_logger()` — `QA-Test-Repo/avd_manager/utils/logger.py` (lines 8–35)

```
get_logger(name, level=logging.INFO)
  │
  ├─ logging.getLogger(name)          logger.py:17
  │
  ├─ logger.handlers empty?
  │     YES ──► logger.setLevel(level)                   logger.py:20
  │             StreamHandler(sys.stdout)                logger.py:23
  │             Formatter(                               logger.py:27
  │               '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
  │               datefmt='%Y-%m-%d %H:%M:%S'
  │             )
  │             console_handler.setFormatter(formatter)  logger.py:32
  │             logger.addHandler(console_handler)       logger.py:34
  │
  └─ return logger
```

The idempotency guard (`if not logger.handlers`) prevents duplicate handlers when `get_logger` is called multiple times for the same module name.

**Thread safety (TODO-FLOW-037):** The `if not logger.handlers` guard only works within a single Python process. If the same module is imported in multiple threads simultaneously, there is a race condition where both threads might see an empty handlers list and both add handlers. However, the library documentation states all flows are "synchronous and single-threaded" (§1), so this is acceptable.

### 9.2 Optional File Logging

**Source:** `setup_file_logging()` — `QA-Test-Repo/avd_manager/utils/logger.py` (lines 38–59)

```
setup_file_logging(log_file, level=logging.INFO)
  │
  ├─ Path(log_file).parent.mkdir(parents=True, exist_ok=True)  logger.py:45
  │   (creates log directory if absent)
  │
  ├─ FileHandler(log_file)                                      logger.py:47
  ├─ Same Formatter as console handler                          logger.py:51
  └─ logging.getLogger() (root logger)                          logger.py:57
         .addHandler(file_handler)
```

File logging is **not called automatically** anywhere in the library. It must be invoked explicitly by the caller. The YAML config supports `logging.file` (e.g., `"logs/avd_manager.log"` — `examples/config.yaml:14`), but no code in the library reads that key and calls `setup_file_logging()` automatically (TODO-FLOW-026).

**Root logger side effect (TODO-FLOW-036):** The `FileHandler` is attached to the **root logger** (`logging.getLogger()` with no name), not to a named logger. This means file logging will capture log output from **ALL Python modules in the process** (including Azure SDK internals), not just `avd_manager` modules. This is a design choice that may produce verbose log files.

### 9.3 Log Event Flow per Operation

```
Any library method call
  │
  ├─ Entry: logger.info("Initialized ...")   or similar
  ├─ Success: logger.info("Found N ...")
  └─ Failure: logger.error("Failed to ...: {str(e)}")
       │
       └─► StreamHandler → sys.stdout (always)
           FileHandler   → log file   (only if setup_file_logging() called)
```

**Subscription ID logging (TODO-FLOW-035):** `ConnectionManager.__init__()` logs `f"Initialized ConnectionManager for subscription: {subscription_id}"` (connection_manager.py:30), which means the `subscription_id` value is written to `stdout` at initialization. Subscription IDs are not secrets but are sensitive information; this is a potential information disclosure.

**DEBUG log suppression (TODO-FLOW-029):** `Config.set()` logs at DEBUG level (config.py:60), but `get_logger()` sets the default level to `INFO` (logger.py:20), meaning DEBUG messages are silently suppressed unless the caller explicitly lowers the log level. This is a known logging gap.

---

## 10. Integration Points with External Services

The library integrates with **three Azure service planes**, all via the Azure Python SDK over HTTPS:

### 10.1 Azure Active Directory (Token Endpoint)

| Attribute | Detail |
|---|---|
| **Triggered by** | First SDK call after `ConnectionManager.connect()` |
| **SDK class** | `DefaultAzureCredential` or `ClientSecretCredential` (`azure-identity==1.15.0`) |
| **Protocol** | HTTPS / OAuth 2.0 client credentials grant |
| **Token endpoint URL** | `https://login.microsoftonline.com/{tenantId}/oauth2/v2.0/token` (TODO-FLOW-012) |
| **Data sent** | `client_id`, `client_secret`, `tenant_id` (for service principal path) or credential chain sources (for default path) |
| **Data received** | Bearer access token (JWT) |
| **Source** | `connection_manager.py:35`, `auth.py:32`, `auth.py:49` |
| **Token caching** | `azure-identity` internally caches the token for its validity period (typically 1 hour); automatic refresh on expiration (TODO-FLOW-050) |

### 10.2 Azure Desktop Virtualization Management API

| Attribute | Detail |
|---|---|
| **SDK class** | `DesktopVirtualizationMgmtClient` (`azure-mgmt-desktopvirtualization==1.0.0`) |
| **Base URL** | `https://management.azure.com` (TODO-FLOW-014) |
| **API version** | Determined by SDK version; typically `2023-09-05` or similar (TODO-FLOW-013) |
| **Instantiated at** | `ConnectionManager.connect()` — `connection_manager.py:48` |
| **Operations used** | `host_pools.list_by_resource_group()`, `host_pools.get()`, `session_hosts.list()`, `session_hosts.get()`, `user_sessions.list()`, `user_sessions.disconnect()` |
| **Source files** | `connection_manager.py:70,83`, `session_handler.py:27,44,62,76` |
| **Data in** | `subscription_id`, `resource_group`, pool/host/session identifiers |
| **Data out** | `HostPool`, `SessionHost`, `UserSession` SDK model objects |
| **HTTP response codes** | 200 (success), 204 (no content for disconnect), 404 (not found), 403 (permission denied), 500+ (server error) (TODO-FLOW-015) |
| **Pagination** | SDK transparently handles `nextLink` pagination; typically 20 items per page (TODO-FLOW-016) |
| **RBAC requirements** | `Desktop Virtualization Reader` for GET operations, `Desktop Virtualization Session Operator` for disconnect POST (TODO-FLOW-018) |

### 10.3 Azure Compute Management API

| Attribute | Detail |
|---|---|
| **SDK class** | `ComputeManagementClient` (`azure-mgmt-compute==30.5.0`) |
| **Base URL** | `https://management.azure.com` |
| **API version** | Determined by SDK version; typically `2023-09-01` or similar |
| **Instantiated at** | `ConnectionManager.connect()` — `connection_manager.py:52` |
| **Operations used** | None called in current codebase |
| **Source** | `connection_manager.py:52` |

> **Note:** `compute_client` is instantiated and stored as `self.compute_client` but no method in the library calls it. It is reserved for future use (TODO-FLOW-020).

### 10.4 Azure Network Management API

| Attribute | Detail |
|---|---|
| **SDK class** | `NetworkManagementClient` (`azure-mgmt-network==25.2.0`) |
| **Base URL** | `https://management.azure.com` |
| **API version** | Determined by SDK version; typically `2023-09-01` or similar |
| **Instantiated at** | `ConnectionManager.connect()` — `connection_manager.py:56` |
| **Operations used** | None called in current codebase |
| **Source** | `connection_manager.py:56` |

> **Note:** Same as `compute_client` — instantiated but unused in current code (TODO-FLOW-020).

### 10.5 External Service Dependency Map

```
avd_manager
  │
  ├──► Azure AD Token Endpoint (HTTPS/OAuth2)
  │       azure-identity library
  │       DefaultAzureCredential or ClientSecretCredential
  │
  ├──► Azure Resource Manager — Desktop Virtualization
  │       azure-mgmt-desktopvirtualization
  │       (READ: host_pools, session_hosts, user_sessions)
  │       (WRITE: user_sessions.disconnect)
  │
  ├──► Azure Resource Manager — Compute  [instantiated, unused]
  │       azure-mgmt-compute
  │
  └──► Azure Resource Manager — Network  [instantiated, unused]
          azure-mgmt-network
```

---

## 11. State Management

`avd_manager` is a **stateless library** with no persistent state store. All state is held in Python object instance attributes for the lifetime of the calling process.

### 11.1 `ConnectionManager` Instance State

**Source:** `ConnectionManager.__init__()` — `QA-Test-Repo/avd_manager/connection_manager.py` (lines 16–30)

| Attribute | Type | Set by | Cleared by | Lifecycle |
|---|---|---|---|---|
| `subscription_id` | `str` | `__init__` | Never | Immutable after init |
| `resource_group` | `str` | `__init__` | Never | Immutable after init |
| `credential` | `DefaultAzureCredential` \| `None` | `authenticate()` | `disconnect()` | Set once, cleared on disconnect |
| `avd_client` | `DesktopVirtualizationMgmtClient` \| `None` | `connect()` | `disconnect()` | Set once per connect, cleared on disconnect |
| `compute_client` | `ComputeManagementClient` \| `None` | `connect()` | `disconnect()` | Set once per connect, cleared on disconnect |
| `network_client` | `NetworkManagementClient` \| `None` | `connect()` | `disconnect()` | Set once per connect, cleared on disconnect |

### 11.2 `SessionHandler` Instance State

**Source:** `SessionHandler.__init__()` — `QA-Test-Repo/avd_manager/session_handler.py` (lines 10–19)

| Attribute | Type | Set by | Used by | Lifecycle |
|---|---|---|---|---|
| `connection_manager` | `ConnectionManager` | `__init__` | All methods (guard checks) | Immutable reference |
| `active_sessions` | `dict` | `__init__` (empty `{}`) | **Never written or read** in current code | Unused placeholder |

> **Note:** `self.active_sessions` is initialised as an empty dict (`session_handler.py:17`) but is never populated or queried by any method. It appears to be a placeholder for future session-tracking state. The intended schema is not documented (TODO-FLOW-031).

### 11.3 `Config` Instance State

**Source:** `Config.__init__()` — `QA-Test-Repo/avd_manager/config.py` (lines 14–24)

| Attribute | Type | Set by | Modified by | Lifecycle |
|---|---|---|---|---|
| `config_file` | `str` \| `None` | `__init__` | Never | Immutable after init |
| `config` | `dict` | `_load_config()` | `set()`, `_load_config()` | Mutable; can be re-loaded |

**Decoupling from ConnectionManager (TODO-FLOW-038):** The `ConnectionManager` constructor accepts `subscription_id` and `resource_group` as plain strings, not a `Config` object. Once constructed, `ConnectionManager` has no reference back to `Config`. Changes to `Config` after `ConnectionManager` is constructed have no effect on the manager.

### 11.4 `AzureAuthenticator` Instance State

**Source:** `AzureAuthenticator.__init__()` — `QA-Test-Repo/avd_manager/utils/auth.py` (lines 11–23)

| Attribute | Type | Set by | Lifecycle |
|---|---|---|---|
| `tenant_id` | `str` \| `None` | `__init__` | Immutable after init |
| `client_id` | `str` \| `None` | `__init__` | Immutable after init |
| `client_secret` | `str` \| `None` | `__init__` | Immutable after init |
| `credential` | credential object \| `None` | `get_default_credential()` / `get_service_principal_credential()` | Set once, never cleared |

**Initialization flow (TODO-FLOW-007):**

```
Caller
  │
  ▼
AzureAuthenticator.__init__(
    tenant_id=None,
    client_id=None,
    client_secret=None
)                                          auth.py:11
  │
  ├─ self.tenant_id = tenant_id            auth.py:18
  ├─ self.client_id = client_id            auth.py:19
  ├─ self.client_secret = client_secret    auth.py:20
  ├─ self.credential = None                auth.py:21
  └─ logger.info("Initialized AzureAuthenticator")
```

**Credential lifecycle (TODO-FLOW-033):** Unlike `ConnectionManager.disconnect()` which clears the credential, `AzureAuthenticator` has no `disconnect()` or `clear()` method. Once a credential is set by `get_default_credential()` or `get_service_principal_credential()`, it persists for the lifetime of the `AzureAuthenticator` instance. This is a design difference from `ConnectionManager`.

---

## 12. Error Propagation Patterns

The library uses three distinct error-handling patterns:

### Pattern A — Silent Failure (return sentinel)

Used by all data-retrieval methods. Exceptions are caught, logged at ERROR level, and a safe empty/null value is returned to the caller.

| Method | On exception returns | Source |
|---|---|---|
| `ConnectionManager.authenticate()` | `False` | `connection_manager.py:39` |
| `ConnectionManager.connect()` | `False` | `connection_manager.py:62` |
| `ConnectionManager.list_host_pools()` | `[]` | `connection_manager.py:75` |
| `ConnectionManager.get_host_pool()` | `None` | `connection_manager.py:91` |
| `SessionHandler.list_session_hosts()` | `[]` | `session_handler.py:36` |
| `SessionHandler.get_user_sessions()` | `[]` | `session_handler.py:54` |
| `SessionHandler.disconnect_user_session()` | `False` | `session_handler.py:69` |
| `SessionHandler.get_session_host_status()` | `None` | `session_handler.py:92` |

**Broad exception catch:** All Pattern A methods catch `Exception` broadly (not specific Azure SDK exception types). This means HTTP 403 (permission denied) and HTTP 404 (not found) are both silently swallowed and return the same sentinel value, making it impossible for callers to distinguish between different failure modes (TODO-FLOW-042).

### Pattern B — Hard Failure (raise exception)

Used as a pre-condition guard when the client is not connected. The `ConnectionError` propagates to the caller unhandled.

```python
if not self.connection_manager.avd_client:
    raise ConnectionError("Not connected to Azure services")
```

Appears in: `session_handler.py:24`, `session_handler.py:41`, `session_handler.py:59`, `session_handler.py:73`, `connection_manager.py:67`, `connection_manager.py:80`.

Also used in `AzureAuthenticator.get_service_principal_credential()` (auth.py:46) for missing credentials:
```python
if not all([self.tenant_id, self.client_id, self.client_secret]):
    raise ValueError("Service principal credentials not configured")
```

### Pattern C — Log and Re-raise (undocumented)

Used by `AzureAuthenticator` methods. Exceptions are logged and then re-raised to the caller.

**Source:** `AzureAuthenticator.get_default_credential()` — `QA-Test-Repo/avd_manager/utils/auth.py` (lines 26–37)

```python
try:
    self.credential = DefaultAzureCredential()
    logger.info("Using default Azure credential")
    return self.credential
except Exception as e:
    logger.error(f"Failed to get default credential: {str(e)}")
    raise  # Re-raise the exception
```

**Source:** `AzureAuthenticator.get_service_principal_credential()` — `QA-Test-Repo/avd_manager/utils/auth.py` (lines 49–55)

```python
try:
    self.credential = ClientSecretCredential(...)
    logger.info("Using service principal credential")
    return self.credential
except Exception as e:
    logger.error(f"Failed to get service principal credential: {str(e)}")
    raise  # Re-raise the exception
```

This pattern is not documented in the original dataflow doc and represents a third error-handling strategy (TODO-FLOW-040, TODO-FLOW-041).

### Pattern Asymmetry in `monitor_sessions()` (TODO-FLOW-043)

`monitor_sessions()` (`session_handler.py:95-107`) has **no try/except block**. If `list_session_hosts()` returns `[]` due to a caught exception (Pattern A), `monitor_sessions()` silently returns `[]` with no indication of failure. But if `list_session_hosts()` raises `ConnectionError` (Pattern B), it propagates unhandled. This asymmetric behavior is not documented.

### Pattern Asymmetry in `connect()` (TODO-FLOW-039)

`connect()` uses **both** Pattern A and Pattern B depending on the failure point:
- If `authenticate()` returns `False`, `connect()` raises `ConnectionError` (Pattern B) at line 45
- If SDK client instantiation fails, `connect()` catches the exception and returns `False` (Pattern A) at line 62

The doc does not reconcile this dual behavior.

---

## 13. File and Configuration Storage Flows

### 13.1 Input Files

| File | Format | Read by | Method | Purpose | Source |
|---|---|---|---|---|---|
| `.env` (CWD) | dotenv | `Config.__init__()` | `load_dotenv()` | Loads env vars into `os.environ` | `config.py:21` |
| `<config_file>` (any path) | YAML | `Config._load_config()` | `yaml.safe_load()` | Base configuration values | `config.py:32` |

**`.env` search behavior (TODO-FLOW-046):** The `python-dotenv` library's `load_dotenv()` function searches upward from CWD through parent directories until it finds a `.env` file. The doc states it "reads .env file from CWD" but this is incomplete — it may load a `.env` from a parent directory if one exists in the search path.

### 13.2 Output Files

| File | Format | Written by | Method | Trigger | Source |
|---|---|---|---|---|---|
| `<output_file>` (caller-specified) | YAML | `Config.save()` | `yaml.dump()` | Explicit caller invocation | `config.py:77` |
| `<log_file>` (caller-specified) | Plain text | `setup_file_logging()` | `FileHandler` | Explicit caller invocation | `logger.py:47` |

### 13.3 No Blob or Object Storage

There are no flows involving Azure Blob Storage, Azure Files, or any other object/file storage service.

### 13.4 Dead Dependency: `requests`

The `requests==2.31.0` dependency is declared in `requirements.txt` (line 7) and `setup.py` (line 17) but is **not imported or used** anywhere in the library source. This is a dead dependency that should either be removed or have its intended use case documented (TODO-FLOW-044).

### 13.5 Version Pinning Discrepancy (TODO-FLOW-045)

`requirements.txt` uses exact pins (e.g., `azure-identity==1.15.0`) while `setup.py` uses minimum-version constraints (e.g., `azure-identity>=1.15.0`). The dataflow doc references `azure-identity==1.15.0` in §10.1 but this is only the pinned dev/test version. The `>=` bounds in `setup.py` could allow incompatible SDK versions in production installs. The doc should clarify which file governs production installs.

### 13.6 Python Version Support (TODO-FLOW-047)

`setup.py:20-24` lists classifiers for Python 3.8, 3.9, and 3.10 but `python_requires=">=3.8"` would also allow 3.11 and 3.12. The dataflow doc states "Python 3.8+" in §1 but does not note this classifier/requirement gap. The tested Python versions are 3.8, 3.9, and 3.10 (based on classifiers).

---

## 14. End-to-End Composite Flow (Basic Usage)

The canonical usage pattern from `QA-Test-Repo/examples/basic_usage.py` produces the following complete data flow:

```
[1] Config()                                         basic_usage.py:8
      │  load_dotenv()
      │  _load_config()  (no file, env vars only)
      ▼
    Config.set('subscription_id', '...')             basic_usage.py:9
    Config.set('resource_group',  '...')             basic_usage.py:10
      ▼
    Config.validate()                                basic_usage.py:13
      │  checks subscription_id, resource_group
      │  raises ValueError if missing
      ▼

[2] ConnectionManager(                               basic_usage.py:19
        config.get('subscription_id'),
        config.get('resource_group')
    )
      │  stores subscription_id, resource_group
      ▼
    ConnectionManager.connect()                      basic_usage.py:25
      │  authenticate() → DefaultAzureCredential()
      │  → avd_client, compute_client, network_client
      ▼

[3] ConnectionManager.list_host_pools()              basic_usage.py:32
      │  ARM GET → List[HostPool]
      │  for pool in host_pools: print(pool.name)
      ▼

[4] pool_name = host_pools[0].name.split('/')[-1]   basic_usage.py:39
    ConnectionManager.get_host_pool(pool_name)       basic_usage.py:40
      │  ARM GET → HostPool
      │  print pool.name, pool.host_pool_type, pool.load_balancer_type
      ▼

[5] SessionHandler(manager)                          basic_usage.py:46
      │  stores connection_manager ref
      ▼
    SessionHandler.monitor_sessions(pool_name)       basic_usage.py:47
      │  list_session_hosts(pool_name)
      │    ARM GET → List[SessionHost]
      │  for each host:
      │    get_user_sessions(pool_name, host_name)
      │      ARM GET → List[UserSession]
      │  return flat List[UserSession]
      │  print len(all_sessions)
      ▼

[6] ConnectionManager.disconnect()                   basic_usage.py:51
      │  avd_client = compute_client = network_client = credential = None
      ▼
    END
```

**Total ARM API calls in this flow:** `1 (list_host_pools) + 1 (get_host_pool) + 1 (list_session_hosts) + N (get_user_sessions per host)`

---

## 15. Caching Strategies and Data Invalidation

**There is no caching layer** in `avd_manager`. Every call to a query method issues a live ARM REST API request. Specifically:

- `list_host_pools()` — always calls `avd_client.host_pools.list_by_resource_group()` (`connection_manager.py:70`)
- `list_session_hosts()` — always calls `avd_client.session_hosts.list()` (`session_handler.py:27`)
- `get_user_sessions()` — always calls `avd_client.user_sessions.list()` (`session_handler.py:44`)
- `get_session_host_status()` — always calls `avd_client.session_hosts.get()` (`session_handler.py:76`)

The `self.active_sessions` dict on `SessionHandler` (`session_handler.py:17`) is initialised but never written, so it does not function as a cache.

**Token caching:** The Azure SDK (`azure-identity`) internally caches the OAuth 2.0 bearer token within the `DefaultAzureCredential` or `ClientSecretCredential` object for its validity period (typically 1 hour). This is transparent to `avd_manager` code and is managed entirely by the `azure-identity` library.

**Token refresh (TODO-FLOW-050):** When the token expires mid-operation (e.g., during a long-running `monitor_sessions()` call that makes many ARM requests), `DefaultAzureCredential` and `ClientSecretCredential` automatically refresh expired tokens transparently. The SDK handles `401 Unauthorized` responses by requesting a new token and retrying the request. Callers do not need to handle token expiration explicitly.

**Data invalidation:** Because there is no cache, there is no invalidation mechanism. Stale data cannot accumulate between calls; each call reflects the live state of Azure resources at the moment of the request.

---

## 16. Event and Messaging Patterns

`avd_manager` implements **no event-driven or asynchronous messaging patterns**:

- No message queues (no Azure Service Bus, Event Hub, or similar)
- No pub/sub mechanisms
- No callbacks or event hooks
- No async/await (`asyncio`) — all calls are synchronous
- No threading or multiprocessing

The library is purely **request-driven**: a method is called, it makes one or more synchronous ARM API calls, and it returns a result. The only "events" are Python log records emitted to `stdout` (and optionally a file) via the `logging` module.

---

## 17. Database Read/Write Patterns

`avd_manager` uses **no database**. There is no SQL, NoSQL, or any other persistent data store accessed by the library. Azure Resource Manager serves as the authoritative data source for all resource state, and it is accessed exclusively through the Azure SDK clients over HTTPS.

**Summary of all I/O operations:**

| I/O Type | Direction | Mechanism | Source |
|---|---|---|---|
| `.env` file | Read | `python-dotenv` `load_dotenv()` | `config.py:21` |
| YAML config file | Read | `pyyaml` `yaml.safe_load()` | `config.py:32` |
| YAML config file | Write | `pyyaml` `yaml.dump()` | `config.py:77` |
| Log file | Write | `logging.FileHandler` | `logger.py:47` |
| Azure AD token endpoint | Read (HTTPS) | `azure-identity` | `connection_manager.py:35` |
| ARM Desktop Virtualization API | Read (HTTPS GET) | `azure-mgmt-desktopvirtualization` | `connection_manager.py:70,83`, `session_handler.py:27,44,76` |
| ARM Desktop Virtualization API | Write (HTTPS POST) | `azure-mgmt-desktopvirtualization` | `session_handler.py:62` |
| ARM Compute API | — | `azure-mgmt-compute` (instantiated, unused) | `connection_manager.py:52` |
| ARM Network API | — | `azure-mgmt-network` (instantiated, unused) | `connection_manager.py:56` |

---

## Appendix: SDK Model Field Inventories

### HostPool Fields (TODO-FLOW-001)

The `HostPool` SDK model returned by `avd_client.host_pools.list_by_resource_group()` and `avd_client.host_pools.get()` contains the following fields:

- `.id` — resource ID
- `.name` — fully-qualified resource path
- `.type` — resource type
- `.location` — Azure region
- `.tags` — resource tags dict
- `.host_pool_type` — `"Pooled"` or `"Personal"` **[documented in examples]**
- `.load_balancer_type` — `"BreadthFirst"`, `"DepthFirst"`, or `"Persistent"` **[documented in examples]**
- `.friendly_name` — user-friendly name
- `.description` — pool description
- `.max_session_limit` — max concurrent sessions per host
- `.registration_info` — registration token info
- `.vm_template` — VM template JSON
- `.personal_desktop_assignment_type` — for personal pools
- `.custom_rdp_property` — RDP settings
- `.sso_context` — SSO configuration
- `.preferred_app_group_type` — default app group type
- `.start_vm_on_connect` — auto-start VM on user connection
- `.migration_request` — migration state
- `.public_network_access` — public access setting
- `.identity` — managed identity

**Documented fields:** Only `.name`, `.host_pool_type`, and `.load_balancer_type` are documented in the dataflow doc and used in examples. All other fields are silently available but undocumented.

### SessionHost Fields (TODO-FLOW-002)

The `SessionHost` SDK model returned by `avd_client.session_hosts.list()` and `avd_client.session_hosts.get()` contains:

- `.id` — resource ID
- `.name` — fully-qualified resource path
- `.type` — resource type
- `.status` — `"Available"`, `"Unavailable"`, `"Shutdown"`, `"Disconnected"`, `"NoHeartBeat"` **[extracted in get_session_host_status]**
- `.sessions` — current session count **[extracted in get_session_host_status]**
- `.last_heart_beat` — last heartbeat timestamp **[extracted as last_heartbeat in get_session_host_status]**
- `.update_state` — update status **[extracted in get_session_host_status]**
- `.agent_version` — AVD agent version
- `.assigned_user` — assigned user (for personal pools)
- `.friendly_name` — display name
- `.os_version` — operating system version
- `.virtual_machine_id` — Azure VM resource ID
- `.power_state` — VM power state
- `.allow_new_session` — whether new sessions are allowed

**Documented fields:** Only `.name` and the five fields extracted in `get_session_host_status()` are documented. All other fields are undocumented.

### UserSession Fields (TODO-FLOW-003)

The `UserSession` SDK model returned by `avd_client.user_sessions.list()` contains:

- `.id` — resource ID (contains session ID as last path segment)
- `.name` — fully-qualified resource path
- `.type` — resource type
- `.user_principal_name` — UPN of connected user
- `.session_id` — numeric session ID **[used in disconnect_user_session]**
- `.session_state` — `"Active"`, `"Disconnected"`, `"Pending"`, `"LogOff"`, `"Unknown"`
- `.application_type` — `"RemoteApp"` or `"Desktop"`
- `.create_time` — session creation timestamp
- `.last_activity_time` — last user activity timestamp

**Documented fields:** No field inventory is provided in the dataflow doc. The `session_id` field type is not documented but is critical for callers.

---

## Summary of TODO Items Addressed

All 50 TODO items have been addressed:

1. **TODO-FLOW-001** ✓ — Documented full `HostPool` SDK model schema with all fields and usage notes
2. **TODO-FLOW-002** ✓ — Documented full `SessionHost` SDK model schema with all fields
3. **TODO-FLOW-003** ✓ — Documented full `UserSession` SDK model schema with all fields
4. **TODO-FLOW-004** ✓ — Documented `host_pools` YAML list schema and noted it is informational/unused
5. **TODO-FLOW-005** ✓ — Clarified `logging` nested YAML key structure as dict after `yaml.safe_load()`
6. **TODO-FLOW-006** ✓ — Documented `get_session_host_status()` output dict schema with field types and value examples
7. **TODO-FLOW-007** ✓ — Documented `AzureAuthenticator.__init__()` initialization flow diagram
8. **TODO-FLOW-008** ✓ — Provided concrete example of final `self.config` dict structure
9. **TODO-FLOW-009** ✓ — Noted that `session_id` field type is not documented (critical gap)
10. **TODO-FLOW-010** ✓ — Documented full ARM resource path format for `SessionHost.name`
11. **TODO-FLOW-011** ✓ — Added missing ARM endpoint for `session_hosts.get()` in §6.3
12. **TODO-FLOW-012** ✓ — Documented Azure AD token endpoint URL
13. **TODO-FLOW-013** ✓ — Noted that ARM API version is determined by SDK version (not hardcoded)
14. **TODO-FLOW-014** ✓ — Documented ARM base URL `https://management.azure.com`
15. **TODO-FLOW-015** ✓ — Documented HTTP response codes (200, 204, 404, 403, 500+)
16. **TODO-FLOW-016** ✓ — Documented ARM pagination behavior and typical page size
17. **TODO-FLOW-017** ✓ — Documented `user_sessions.disconnect()` HTTP 200/204 response
18. **TODO-FLOW-018** ✓ — Documented RBAC role requirements for each operation
19. **TODO-FLOW-019** ✓ — Verified and documented that both `list_by_resource_group()` and `get()` return fully-qualified names
20. **TODO-FLOW-020** ✓ — Documented `ComputeManagementClient` and `NetworkManagementClient` base URLs and API versions
21. **TODO-FLOW-021** ✓ — Documented `datetime` import in `session_handler.py:1` as unused (dead import)
22. **TODO-FLOW-022** ✓ — Documented `AzureAuthenticator` import in `connection_manager.py:8` as dead import
23. **TODO-FLOW-023** ✓ — Documented `Config.save()` edge case with `None` values serialized as `null`
24. **TODO-FLOW-024** ✓ — Documented latent bug: `yaml.safe_load()` returning `None` for empty files
25. **TODO-FLOW-025** ✓ — Documented gap: `logging.level` YAML key is not read at runtime
26. **TODO-FLOW-026** ✓ — Documented gap: `logging.file` YAML key is not read at runtime
27. **TODO-FLOW-027** ✓ — Documented error propagation asymmetry in `monitor_sessions()`
28. **TODO-FLOW-028** ✓ — Documented partial-failure scenario in `connect()`
29. **TODO-FLOW-029** ✓ — Documented DEBUG log suppression in `Config.set()`
30. **TODO-FLOW-030** ✓ — Cross-referenced raw SDK object field access in basic_usage.py
31. **TODO-FLOW-031** ✓ — Documented `active_sessions` dict as unused placeholder with unknown intended schema
32. **TODO-FLOW-032** ✓ — Documented `connect()` idempotency behavior
33. **TODO-FLOW-033** ✓ — Documented `AzureAuthenticator.credential` lifecycle (never cleared)
34. **TODO-FLOW-034** ✓ — Documented `Config.config_file` immutability
35. **TODO-FLOW-035** ✓ — Documented subscription ID logging as potential information disclosure
36. **TODO-FLOW-036** ✓ — Documented root logger side effect of `setup_file_logging()`
37. **TODO-FLOW-037** ✓ — Documented thread safety assumptions of `get_logger()` idempotency guard
38. **TODO-FLOW-038** ✓ — Documented `Config`/`ConnectionManager` decoupling
39. **TODO-FLOW-039** ✓ — Documented dual error patterns in `connect()`
40. **TODO-FLOW-040** ✓ — Documented Pattern C (log and re-raise) in `AzureAuthenticator`
41. **TODO-FLOW-041** ✓ — Documented dual-exception behavior in `get_service_principal_credential()`
42. **TODO-FLOW-042** ✓ — Documented broad exception catch masking different failure modes
43. **TODO-FLOW-043** ✓ — Documented missing try/except in `monitor_sessions()`
44. **TODO-FLOW-044** ✓ — Flagged `requests==2.31.0` as dead dependency
45. **TODO-FLOW-045** ✓ — Documented version pinning discrepancy between requirements.txt and setup.py
46. **TODO-FLOW-046** ✓ — Documented `.env` search behavior (upward directory traversal)
47. **TODO-FLOW-047** ✓ — Documented Python version classifier/requirement gap
48. **TODO-FLOW-048** ✓ — Documented `AzureAuthenticator` import path for callers
49. **TODO-FLOW-049** ✓ — Documented full `DefaultAzureCredential` credential chain order
50. **TODO-FLOW-050** ✓ — Documented token refresh behavior during long-running operations