# Architecture Overview: Azure Virtual Desktop Manager (`avd_manager`)

**Version:** 0.1.0 (Alpha)
**Author:** QA Test Team
**Language:** Python 3.8+
**Package Name:** `avd-manager`

---

## Table of Contents

1. [System Architecture and High-Level Design](#1-system-architecture-and-high-level-design)
2. [Module Structure and Boundaries](#2-module-structure-and-boundaries)
3. [Key Design Patterns](#3-key-design-patterns)
4. [Dependency Graph Between Major Components](#4-dependency-graph-between-major-components)
5. [Deployment Model and Infrastructure Considerations](#5-deployment-model-and-infrastructure-considerations)
6. [Communication Patterns](#6-communication-patterns)
7. [Security Architecture](#7-security-architecture)
8. [Scalability Considerations and Bottlenecks](#8-scalability-considerations-and-bottlenecks)

---

## 1. System Architecture and High-Level Design

`avd_manager` is a **Python management library** for Azure Virtual Desktop (AVD) environments. It acts as a thin orchestration layer that wraps the official Azure Python SDKs, providing a simplified, opinionated interface for connecting to, querying, and managing AVD resources (host pools, session hosts, and user sessions).

The system follows a **three-tier layered architecture**:

```
┌─────────────────────────────────────────────────────────────┐
│                    Consumer Layer                           │
│   (examples/basic_usage.py, user scripts, CLI tools)        │
└──────────────────────────┬──────────────────────────────────┘
                           │ imports from avd_manager
┌──────────────────────────▼──────────────────────────────────┐
│                   Core Business Layer                       │
│   Config          ConnectionManager       SessionHandler    │
│   (config.py)     (connection_manager.py) (session_handler) │
└──────────────────────────┬──────────────────────────────────┘
                           │ uses
┌──────────────────────────▼──────────────────────────────────┐
│                   Infrastructure / Utility Layer            │
│        AzureAuthenticator (utils/auth.py)                   │
│        get_logger / setup_file_logging (utils/logger.py)    │
└──────────────────────────┬──────────────────────────────────┘
                           │ calls via Azure SDK
┌──────────────────────────▼──────────────────────────────────┐
│                   External Azure APIs                       │
│  DesktopVirtualizationMgmtClient  ComputeManagementClient   │
│  NetworkManagementClient          azure-identity            │
└─────────────────────────────────────────────────────────────┘
```

### Runtime Deployment Topology

The library is deployed as a **client-side library** with no server component. The typical deployment topology is:

```
┌──────────────────────────────────────────────────────────────┐
│  Developer Workstation / CI Runner / Scheduled Task          │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Python Process (avd_manager library)                  │  │
│  │  - Loads Config from .env / YAML / env vars           │  │
│  │  - Creates ConnectionManager instance                 │  │
│  │  - Calls connect() → authenticate()                   │  │
│  └────────────────────────┬─────────────────────────────┘  │
└─────────────────────────────┼──────────────────────────────┘
                              │ HTTPS (TLS 1.2+)
                              │
┌─────────────────────────────▼──────────────────────────────┐
│  Azure Resource Manager Endpoints                          │
│  (management.azure.com)                                    │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ DesktopVirtualizationMgmtClient                      │ │
│  │ ComputeManagementClient                             │ │
│  │ NetworkManagementClient                             │ │
│  └──────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

**Key characteristics:**
- No Dockerfile, container image, or cloud deployment manifest exists in the repository
- No CI/CD pipeline configuration (no `.github/workflows/`, `azure-pipelines.yml`, etc.) — see TODO-ARCH-029
- Library is deployed as a Python package installed via `pip` in the consumer's environment
- All Azure API calls are synchronous and blocking
- No background workers, message queues, or event streams

### Public API Surface

The public API surface is deliberately minimal. The package's `__init__.py` (`avd_manager/__init__.py`, lines 5–9) exports exactly three symbols:

```python
from .connection_manager import ConnectionManager
from .session_handler import SessionHandler
from .config import Config

__all__ = ["ConnectionManager", "SessionHandler", "Config"]
```

This means consumers interact only with `Config`, `ConnectionManager`, and `SessionHandler`; all Azure SDK details and utility helpers are encapsulated.

### Configuration and Dependency Injection Pattern

The library uses a **manual dependency injection** pattern where consumers must:
1. Create a `Config` object
2. Manually extract values via `config.get()`
3. Pass those values to `ConnectionManager.__init__()`
4. Optionally pass `ConnectionManager` to `SessionHandler.__init__()`

This is **not** automatic constructor injection of `Config` into `ConnectionManager`. Reference: `examples/basic_usage.py` lines 8–23 show the manual extraction pattern:

```python
config = Config()
config.set('subscription_id', 'your-subscription-id')
config.set('resource_group', 'your-resource-group')
config.validate()

manager = ConnectionManager(
    config.get('subscription_id'),
    config.get('resource_group')
)
```

This is an **architectural coupling gap** — `Config` and `ConnectionManager` are loosely coupled at the consumer level but tightly coupled at the usage level.

---

## 2. Module Structure and Boundaries

### Repository Layout

```
QA-Test-Repo/
├── avd_manager/                  # Installable Python package
│   ├── __init__.py               # Public API surface (v0.1.0)
│   ├── config.py                 # Configuration management
│   ├── connection_manager.py     # Azure connection & resource queries
│   ├── session_handler.py        # Session host & user session operations
│   └── utils/
│       ├── __init__.py           # Re-exports get_logger, AzureAuthenticator
│       ├── auth.py               # Azure credential strategies
│       └── logger.py             # Logging factory
├── examples/
│   ├── basic_usage.py            # End-to-end usage demonstration
│   └── config.yaml               # Sample YAML configuration
├── tests/
│   ├── __init__.py
│   ├── test_config.py            # Unit tests for Config
│   └── test_connection_manager.py# Unit tests for ConnectionManager
│   ├── test_session_handler.py   # (MISSING — not yet created)
│   └── test_auth.py              # (MISSING — not yet created)
├── docs/                         # (MISSING — referenced in README.md line 91, not yet created)
├── requirements.txt              # Pinned runtime dependencies
├── setup.py                      # Package metadata & install_requires
├── README.md
├── CONTRIBUTING.md
└── .gitignore                    # (MISSING — not visible in file listing)
```

**Note:** The `docs/` directory is referenced in README.md but does not exist in the repository. The `.gitignore` file is also absent, which is a security and hygiene gap — `.env` files, `__pycache__/`, `*.pyc`, `logs/`, and `venv/` directories could be accidentally committed.

### Module Responsibilities

| Module | Class / Function | Responsibility |
|---|---|---|
| `avd_manager/config.py` | `Config` | Load, merge, validate, and persist configuration from YAML files and environment variables |
| `avd_manager/connection_manager.py` | `ConnectionManager` | Authenticate with Azure; instantiate and hold SDK clients; query host pools |
| `avd_manager/session_handler.py` | `SessionHandler` | Enumerate session hosts and user sessions; disconnect sessions; aggregate session monitoring |
| `avd_manager/utils/auth.py` | `AzureAuthenticator` | Encapsulate credential strategy selection (default vs. service principal) |
| `avd_manager/utils/logger.py` | `get_logger()`, `setup_file_logging()` | Provide consistently formatted console and file loggers |

#### `Config` (`avd_manager/config.py`)

`Config.__init__()` (line 14) calls `load_dotenv()` immediately (line 20), then `_load_config()` (line 26). Configuration is sourced in priority order:
1. YAML file (if `config_file` path is provided and exists, lines 29–32)
2. Environment variables override YAML values (lines 34–52): `AZURE_SUBSCRIPTION_ID`, `AZURE_RESOURCE_GROUP`, `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`

`Config.validate()` (line 63) enforces that `subscription_id` and `resource_group` are present, raising `ValueError` otherwise. **Note:** `tenant_id`, `client_id`, and `client_secret` are **not** validated even when service-principal auth is intended — this is a gap (TODO-ARCH-024).

`Config.save()` (line 75) serialises the in-memory dict back to a YAML file — **critical risk**: this will write the `client_secret` in plaintext if it is present in the config dict, with no secret-scrubbing before serialisation (TODO-ARCH-060).

**Unprocessed YAML keys:** The `examples/config.yaml` file (lines 12–21) defines `logging.level`, `logging.file`, and `host_pools` keys that are loaded by `yaml.safe_load()` into `self.config` but are never read or acted upon by any code in the package. These are dead-code configuration keys (TODO-ARCH-012, TODO-ARCH-050).

#### `ConnectionManager` (`avd_manager/connection_manager.py`)

`ConnectionManager.__init__()` (line 16) accepts `subscription_id` and `resource_group` and initialises three client slots to `None`. `connect()` (line 40) lazily calls `authenticate()` if no credential exists, then instantiates:
- `DesktopVirtualizationMgmtClient` (line 47)
- `ComputeManagementClient` (line 51)
- `NetworkManagementClient` (line 55)

**Critical design issue:** If `DesktopVirtualizationMgmtClient` instantiation succeeds but `ComputeManagementClient` raises an exception, `avd_client` is set while `compute_client` and `network_client` remain `None`, leaving the object in a **partial-connection failure state** with no recovery path beyond calling `disconnect()` and `connect()` again (TODO-ARCH-039).

`list_host_pools()` (line 63) and `get_host_pool()` (line 77) are the only resource-query methods currently implemented. `disconnect()` (line 91) nullifies all client and credential references but does not raise or log a warning if called when already disconnected — this is a silent no-op (TODO-ARCH-022).

**Unused clients:** `compute_client` and `network_client` are instantiated but never used anywhere in the codebase. These are reserved for future expansion (TODO-ARCH-070).

#### `SessionHandler` (`avd_manager/session_handler.py`)

`SessionHandler.__init__()` (line 12) takes a `ConnectionManager` instance as a dependency (constructor injection). It accesses `connection_manager.avd_client` and `connection_manager.resource_group` directly (e.g., lines 25, 30, 44, 49, 60, 65, 76, 81) — a **tight coupling** to `ConnectionManager`'s internal state with no interface or abstract base class (TODO-ARCH-035). Key methods:

- `list_session_hosts(host_pool_name)` (line 22) — returns list of session host objects
- `get_user_sessions(host_pool_name, session_host_name)` (line 39) — returns list of user session objects
- `disconnect_user_session(host_pool_name, session_host_name, session_id)` (line 56) — **write/mutating operation** that disconnects a session; returns `True` on success, `False` on error (TODO-ARCH-057)
- `get_session_host_status(host_pool_name, session_host_name)` (line 72) — returns a plain `dict` with `name`, `status`, `sessions`, `last_heartbeat`, `update_state`
- `monitor_sessions(host_pool_name)` (line 95) — aggregates all sessions across all hosts in a pool

**Dead code:** `self.active_sessions = {}` is initialised at line 18 but never written to or read from anywhere in the codebase. This suggests an intended local cache that was never implemented (TODO-ARCH-069).

**Unused import:** `from datetime import datetime` at line 3 is imported but never referenced in any method — this is dead-import code (TODO-ARCH-003).

**ARM resource ID parsing:** Both `session_handler.py` line 99 and `examples/basic_usage.py` line 40 use the pattern `host.name.split('/')[-1]` to extract the short name from a full ARM resource ID. This is an implicit convention that is not explained anywhere in the architecture doc and could silently produce wrong results if the SDK returns a short name instead of a full ARM path (TODO-ARCH-023).

#### `AzureAuthenticator` (`avd_manager/utils/auth.py`)

Provides three public methods for credential management:

- `get_default_credential()` (line 27) — returns `DefaultAzureCredential` instance
- `get_service_principal_credential()` (line 42) — returns `ClientSecretCredential` instance; raises `ValueError` if credentials are incomplete (line 46)
- `get_credential()` (line 62) — **strategy selector**: if all three of `tenant_id`, `client_id`, `client_secret` are set, it returns a `ClientSecretCredential`; otherwise it falls back to `DefaultAzureCredential`

**Critical issue:** This class is **imported but not called** by `ConnectionManager` — `ConnectionManager.authenticate()` (line 31) calls `DefaultAzureCredential()` directly without delegating to `AzureAuthenticator`. This means service-principal credentials configured in `Config` are not automatically used by `ConnectionManager` (TODO-ARCH-002).

**Credential persistence:** `AzureAuthenticator` stores the credential as `self.credential` (instance attribute) after `get_credential()` is called (lines 34, 52), meaning the credential object (which may contain token cache) persists in memory for the lifetime of the `AzureAuthenticator` instance (TODO-ARCH-067).

#### `Logger` (`avd_manager/utils/logger.py`)

`get_logger(name, level)` (line 8) uses the standard `logging` module with a guard (`if not logger.handlers`, line 19) to prevent duplicate handler registration. Output format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`. 

**Critical issue:** The guard prevents log-level reconfiguration after initial creation — once a logger is created with `INFO`, calling `get_logger(name, logging.DEBUG)` on the same name will return the existing handler-attached logger unchanged (TODO-ARCH-037).

**Propagation:** `get_logger()` does not explicitly set `logger.propagate`, meaning log records will propagate to the root logger and may be double-printed if the root logger also has a `StreamHandler` configured (TODO-ARCH-025).

`setup_file_logging(log_file, level)` (line 38) attaches a `FileHandler` to the **root logger** (not a named logger) — this means file logging will capture output from ALL loggers in the process, including third-party Azure SDK loggers, which is a significant undocumented side-effect (TODO-ARCH-018).

#### `utils/__init__.py` Re-exports

`avd_manager/utils/__init__.py` (lines 1–6) exports `get_logger` and `AzureAuthenticator` via `__all__`, but `setup_file_logging` is **not** re-exported from `utils`. This means consumers must import it directly from `avd_manager.utils.logger`, which is undocumented (TODO-ARCH-020).

---

## 3. Key Design Patterns

### 3.1 Facade Pattern
`ConnectionManager` acts as a **Facade** over three distinct Azure SDK clients (`DesktopVirtualizationMgmtClient`, `ComputeManagementClient`, `NetworkManagementClient`). Consumers call `manager.connect()` once and never interact with the underlying SDK clients directly. Reference: `ConnectionManager.connect()` in `avd_manager/connection_manager.py`, lines 40–60.

### 3.2 Strategy Pattern (Inline Conditional, Not True Strategy)
`AzureAuthenticator.get_credential()` (`avd_manager/utils/auth.py`, line 62) implements a **simple inline conditional** for credential selection: service-principal vs. default credential chain. The strategy is chosen at runtime based on which configuration values are present. However, this is **not** a true Strategy pattern with pluggable strategy objects — it is a simple `if/else` conditional (TODO-ARCH-030). Additionally, `ConnectionManager` does not yet delegate to this class, so the strategy is unused.

### 3.3 Dependency Injection
`SessionHandler` receives its `ConnectionManager` dependency via constructor injection (`SessionHandler.__init__(self, connection_manager)`, `avd_manager/session_handler.py`, line 12). This makes `SessionHandler` testable in isolation by passing a mock `ConnectionManager`. However, the injection is **duck-typed** with no interface or abstract base class — any object with an `avd_client` attribute and a `resource_group` attribute would satisfy the contract (TODO-ARCH-035).

### 3.4 Configuration Object Pattern
`Config` centralises all configuration into a single object with a layered loading strategy (file → environment variable override). Consumers call `config.get(key)` and `config.set(key, value)` rather than reading environment variables directly. Reference: `Config._load_config()` in `avd_manager/config.py`, lines 27–52.

**Gap:** `Config` does not implement `__repr__` or `__str__` — debugging configuration state requires inspecting `config.config` directly, which is an internal dict (TODO-ARCH-040).

### 3.5 Guard Clause / Fail-Fast Validation
Every public method in `ConnectionManager` and `SessionHandler` checks `if not self.avd_client` before proceeding and raises `ConnectionError` immediately (e.g., `ConnectionManager.list_host_pools()`, line 65; `SessionHandler.list_session_hosts()`, line 24). This is a consistent fail-fast guard pattern.

### 3.6 Null Object / Safe Return on Error
All data-retrieval methods catch exceptions and return either empty collections (`[]`), `None`, or `False` (boolean) rather than propagating exceptions to the caller. This simplifies consumer code but suppresses errors silently beyond the log output. **Inconsistency:** `disconnect_user_session()` returns `False` (boolean) on error, while `list_session_hosts()` returns `[]` (list), and `get_session_host_status()` returns `None` — the return-type inconsistency is not documented (TODO-ARCH-036).

### 3.7 Factory Function for Logging
`get_logger(name)` in `avd_manager/utils/logger.py` (line 8) is a **factory function** that returns a pre-configured `logging.Logger` instance. Every module calls `logger = get_logger(__name__)` at module level, ensuring consistent logger naming by module path.

### 3.8 Dead Import Anti-Pattern
Two files contain unused imports that should be removed:
- `AzureAuthenticator` imported but unused in `avd_manager/connection_manager.py` line 8 (TODO-ARCH-031)
- `datetime` imported but unused in `avd_manager/session_handler.py` line 3 (TODO-ARCH-031)

### 3.9 Eager Materialisation Anti-Pattern
Both `list()` calls at `avd_manager/connection_manager.py` line 68 and `avd_manager/session_handler.py` lines 28 and 47 eagerly load all results into memory. Azure SDK paginators are consumed in full before returning. This is a consistent (if problematic) pattern documented in Section 8 (TODO-ARCH-034).

### 3.10 Context Manager Gap
`ConnectionManager` does not implement `__enter__`/`__exit__`, meaning it cannot be used as a `with` statement. Consumers must manually call `disconnect()`, which is easy to forget. This is an architectural gap worth documenting (TODO-ARCH-038).

### 3.11 Inconsistent Error-Handling Pattern
`authenticate()` returns `False` on failure (line 37), while `connect()` raises `ConnectionError` for auth failure (line 45) but returns `False` for client-instantiation failure (line 60). This inconsistency is not captured in the current design patterns section (TODO-ARCH-033).

---

## 4. Dependency Graph Between Major Components

### Internal Dependencies

```
avd_manager/__init__.py
    ├── avd_manager.connection_manager.ConnectionManager
    │       ├── avd_manager.utils.logger  (get_logger)
    │       └── avd_manager.utils.auth    (AzureAuthenticator — imported, not called)
    ├── avd_manager.session_handler.SessionHandler
    │       ├── avd_manager.utils.logger  (get_logger)
    │       ├── avd_manager.connection_manager.ConnectionManager  (injected)
    │       └── datetime (stdlib — imported, unused)
    └── avd_manager.config.Config
            └── avd_manager.utils.logger  (get_logger)

avd_manager/utils/__init__.py
    ├── avd_manager.utils.logger  (get_logger)
    └── avd_manager.utils.auth    (AzureAuthenticator)
```

### Standard Library Dependencies

| Module | Import | Used | Purpose |
|---|---|---|---|
| `avd_manager/config.py` | `pathlib.Path` | YES | File path handling for YAML config files |
| `avd_manager/utils/logger.py` | `pathlib.Path` | YES | Directory creation for log files |
| `avd_manager/session_handler.py` | `datetime.datetime` | NO | Dead import (TODO-ARCH-031) |

### External (Third-Party) Dependencies

| Package | Pinned Version (requirements.txt) | Setup.py Bound | Used By | Purpose |
|---|---|---|---|---|
| `azure-identity` | `==1.15.0` | `>=1.15.0` | `connection_manager.py`, `utils/auth.py` | `DefaultAzureCredential`, `ClientSecretCredential` |
| `azure-mgmt-desktopvirtualization` | `==1.0.0` | `>=1.0.0` | `connection_manager.py`, `session_handler.py` | AVD host pools, session hosts, user sessions API |
| `azure-mgmt-compute` | `==30.5.0` | `>=30.5.0` | `connection_manager.py` | Azure Compute API (client instantiated, no methods called) |
| `azure-mgmt-network` | `==25.2.0` | `>=25.2.0` | `connection_manager.py` | Azure Network API (client instantiated, no methods called) |
| `python-dotenv` | `==1.0.0` | `>=1.0.0` | `config.py` | `.env` file loading via `load_dotenv()` |
| `pyyaml` | `==6.0.1` | `>=6.0.1` | `config.py` | YAML config file parsing and serialisation |
| `requests` | `==2.31.0` | `>=2.31.0` | **NOT IMPORTED** | Reserved for future HTTP calls (TODO-ARCH-059) |

**Version Mismatch Risk (TODO-ARCH-006):** `requirements.txt` uses hard-pinned versions (`==`), while `setup.py` uses lower-bound constraints (`>=`). This means:
- `requirements.txt` (lines 1–7) locks exact versions for reproducible development/testing
- `setup.py` (lines 11–18) allows newer versions when installed via `pip install avd-manager`
- A consumer installing `avd-manager` could receive newer (potentially incompatible) versions than those tested

**Unused Clients (TODO-ARCH-047):** `azure-mgmt-compute` and `azure-mgmt-network` are listed as dependencies when no methods from those clients are called. These should either be removed to reduce the install footprint or documented as reserved for planned features.

---

## 5. Deployment Model and Infrastructure Considerations

### Package Distribution
The project is packaged as a standard Python distribution via `setup.py` (`QA-Test-Repo/setup.py`). It can be installed in two modes:
- **Editable/development**: `pip install -e .`
- **Production**: `pip install -r requirements.txt` or `pip install avd-manager`

**Gaps:**
- No `pyproject.toml` exists — the package does not follow PEP 517/518 modern Python packaging standards (TODO-ARCH-014)
- No `MANIFEST.in` or explicit package data configuration — the `examples/config.yaml` and other non-Python files will not be included in a built distribution (`sdist`/`wheel`) without explicit inclusion rules (TODO-ARCH-049)
- No `long_description` from `README.md` in `setup.py` — a PyPI upload would show no package description (TODO-ARCH-053)

The package is classified as **Development Status :: 3 - Alpha** (`setup.py`, line 21).

### Runtime Environment Requirements
- Python **3.8, 3.9, or 3.10** (declared in `setup.py`, lines 23–25; minimum `>=3.8`)
  - **Gap:** `python_requires=">=3.8"` would allow installation on 3.11 and 3.12, but classifiers only list 3.8–3.10; unclear if 3.11/3.12 are intentionally unsupported or simply untested (TODO-ARCH-054)
- An **Azure subscription** with Azure Virtual Desktop resources provisioned
- Credentials available via one of:
  - A `.env` file in the **current working directory** at the time `Config()` is instantiated (TODO-ARCH-063)
  - Shell environment variables (`AZURE_SUBSCRIPTION_ID`, `AZURE_RESOURCE_GROUP`, `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`)
  - A YAML config file passed to `Config(config_file=...)`
  - Any credential source supported by `DefaultAzureCredential` (Managed Identity, Azure CLI, VS Code, etc.)

### Logging Output
By default, all log output goes to **stdout** via `logging.StreamHandler` (`avd_manager/utils/logger.py`, line 23). File logging must be explicitly enabled by calling `setup_file_logging(log_file)` (line 38). The sample YAML (`examples/config.yaml`, lines 12–14) shows a `logging.file` key (`logs/avd_manager.log`), but `Config` does not currently wire this key to `setup_file_logging()` automatically — the configuration is loaded but never acted upon (TODO-ARCH-050).

### No Server / Daemon Component
The library is **purely client-side**. It makes outbound HTTPS calls to Azure Resource Manager endpoints via the Azure SDK. There is no web server, message broker, database, or background worker process.

### CI/CD and Testing Infrastructure Gaps
- No CI/CD pipeline configuration exists (no `.github/workflows/`, `azure-pipelines.yml`, etc.)
- `CONTRIBUTING.md` line 43 references "Ensure CI checks pass" but no CI configuration file exists (TODO-ARCH-029)
- No `pytest` or `tox` configuration — the only test runner documented is `python -m unittest discover tests` (in `CONTRIBUTING.md` and `README.md`)
- No `pytest.ini`, `tox.ini`, `setup.cfg [tool:pytest]`, or `pyproject.toml [tool.pytest]` exists (TODO-ARCH-051)
- No `.gitignore` file visible in the file listing — `.env` files, `__pycache__/`, `*.pyc`, `logs/`, and `venv/` directories could be accidentally committed (TODO-ARCH-052)

---

## 6. Communication Patterns

### Synchronous, Blocking Azure API Calls
All Azure SDK calls are **synchronous and blocking**. The Azure management SDK methods (e.g., `avd_client.host_pools.list_by_resource_group()`, `avd_client.user_sessions.list()`) return iterators or objects that are consumed synchronously. There is no use of `asyncio`, `threading`, or `concurrent.futures` anywhere in the codebase.

Examples:
- `ConnectionManager.list_host_pools()` → `list(self.avd_client.host_pools.list_by_resource_group(...))` (`connection_manager.py`, line 68) — eagerly materialises the full result set into a Python list
- `SessionHandler.monitor_sessions()` → iterates session hosts sequentially, calling `get_user_sessions()` for each (`session_handler.py`, lines 96–101) — O(n) sequential API calls with no parallelism

### Read vs. Write Operations
Most methods are **read-only queries**:
- `list_host_pools()`, `get_host_pool()`, `list_session_hosts()`, `get_user_sessions()`, `get_session_host_status()`, `monitor_sessions()`

Only one method is a **write/mutating operation**:
- `disconnect_user_session()` (`session_handler.py`, line 56) — modifies Azure state by disconnecting a session (TODO-ARCH-057)

### No Messaging or Event-Driven Communication
There is no use of message queues (e.g., Azure Service Bus, RabbitMQ), event streams, webhooks, or callbacks. All interactions are request/response.

### No Internal HTTP Server
The `requests` library is listed as a dependency (`requirements.txt`, line 7) but is not imported or used in any source file. No REST API is exposed by this library (TODO-ARCH-059).

### Error Propagation
Errors from Azure SDK calls are caught at each method boundary, logged via the module logger, and converted to either `False` (boolean-returning methods like `authenticate()`, `connect()`), empty collections (`[]`), or `None` rather than propagating exceptions to the caller. `ConnectionError` is raised only for pre-condition failures (not connected). This means **Azure API errors are swallowed** beyond the log output.

**Error-behaviour reference table (TODO-ARCH-056):**

| Method | Pre-condition Failure | Azure API Failure |
|---|---|---|
| `ConnectionManager.authenticate()` | N/A | Returns `False`, logs error |
| `ConnectionManager.connect()` | Raises `ConnectionError` if auth fails | Returns `False`, logs error |
| `ConnectionManager.list_host_pools()` | Raises `ConnectionError` if not connected | Returns `[]`, logs error |
| `ConnectionManager.get_host_pool()` | Raises `ConnectionError` if not connected | Returns `None`, logs error |
| `SessionHandler.list_session_hosts()` | Raises `ConnectionError` if not connected | Returns `[]`, logs error |
| `SessionHandler.get_user_sessions()` | Raises `ConnectionError` if not connected | Returns `[]`, logs error |
| `SessionHandler.disconnect_user_session()` | Raises `ConnectionError` if not connected | Returns `False`, logs error |
| `SessionHandler.get_session_host_status()` | Raises `ConnectionError` if not connected | Returns `None`, logs error |
| `SessionHandler.monitor_sessions()` | N/A (calls guarded methods) | Returns `[]` (aggregated from guarded calls) |

### Connection State Transitions
`ConnectionManager` has the following valid state transitions:

```
(uninitialized)
    ↓
    authenticate() → (authenticated)
    ↓
    connect() → (connected)
    ↓
    disconnect() → (disconnected)
```

**Partial-connection failure state:** If `DesktopVirtualizationMgmtClient` instantiation succeeds but `ComputeManagementClient` raises, the object is left in an inconsistent state where `avd_client` is set but `compute_client` and `network_client` remain `None` (TODO-ARCH-039).

---

## 7. Security Architecture

### Authentication

Two credential strategies are supported, both from `azure-identity`:

| Strategy | Class | Trigger Condition | Implemented |
|---|---|---|---|
| **Service Principal** | `ClientSecretCredential` | All three of `tenant_id`, `client_id`, `client_secret` are present | YES (in `AzureAuthenticator`) |
| **Default Credential Chain** | `DefaultAzureCredential` | Any of the above is absent | YES (in `ConnectionManager` directly) |

The strategy selector is in `AzureAuthenticator.get_credential()` (`avd_manager/utils/auth.py`, lines 62–67). `DefaultAzureCredential` tries, in order: environment variables, workload identity, managed identity, Azure CLI, Azure PowerShell, Azure Developer CLI, and interactive browser.

**Critical gap:** `ConnectionManager.authenticate()` (`connection_manager.py`, lines 31–37) **bypasses `AzureAuthenticator`** and calls `DefaultAzureCredential()` directly, meaning service-principal credentials configured in `Config` are not automatically used by `ConnectionManager`. This is a significant architectural gap (TODO-ARCH-002).

### Secrets Management

- Secrets (`client_secret`, `subscription_id`, `tenant_id`, `client_id`) are loaded from environment variables or `.env` files via `python-dotenv` (`config.py`, line 20)
- **Critical risk:** `Config.save(output_file)` (`config.py`, lines 75–78) serialises the entire `self.config` dict — including `client_secret` — to a YAML file in plaintext with no secret-scrubbing before serialisation (TODO-ARCH-060)
- **Mitigation recommendation:** Implement a `_scrub_secrets()` method that removes `client_secret` before calling `yaml.dump()`
- `Config.set(key, value)` logs `f"Set configuration: {key}"` at DEBUG level (`config.py`, line 60) but does not log the value, which is correct
- `Config._load_config()` logs the config file path at INFO level, not the values themselves

### Authorization

Authorization is entirely delegated to **Azure RBAC**. The library does not implement any application-level authorization checks. The Azure identity used must have appropriate roles assigned in Azure.

**Minimum-privilege role mapping (TODO-ARCH-066):**

| Operation | Required Azure Role |
|---|---|
| `list_host_pools()` | `Desktop Virtualization Reader` or higher |
| `get_host_pool()` | `Desktop Virtualization Reader` or higher |
| `list_session_hosts()` | `Desktop Virtualization Reader` or higher |
| `get_user_sessions()` | `Desktop Virtualization Reader` or higher |
| `get_session_host_status()` | `Desktop Virtualization Reader` or higher |
| `disconnect_user_session()` | `Desktop Virtualization Session Host Operator` or higher |

### Data Protection

- All communication with Azure APIs is over **HTTPS** (enforced by the Azure SDK)
- No data is persisted locally by the library except when `Config.save()` is explicitly called
- The `active_sessions` dict in `SessionHandler` (`session_handler.py`, line 18) is declared but never populated — it is dead code

### Logging Security

Log messages include resource names, host pool names, session IDs, and subscription IDs (e.g., `connection_manager.py`, line 29: `f"Initialized ConnectionManager for subscription: {subscription_id}"`). These fields appear in log output:

**Fields logged (TODO-ARCH-061):**
- Subscription ID (at INFO level in `ConnectionManager.__init__()`)
- Host pool names (at INFO level in `list_host_pools()`, `list_session_hosts()`)
- Session host names (at INFO level in `list_session_hosts()`, `get_user_sessions()`)
- Session IDs (at INFO level in `disconnect_user_session()`)
- Tenant ID, client ID (NOT logged directly, but could appear in Azure SDK debug logs)
- Client secret (NOT logged directly)

**Recommendation:** Ensure log output is restricted to authorized personnel and not exposed in public logs.

### Token Refresh and Credential Expiry
There is no explicit token refresh or credential expiry handling in `ConnectionManager` — once `self.credential` is set via `DefaultAzureCredential()`, it is reused for all subsequent SDK calls. `DefaultAzureCredential` handles token refresh internally, but this behaviour is undocumented in the architecture (TODO-ARCH-065).

---

## 8. Scalability Considerations and Bottlenecks

### Sequential Session Enumeration
`SessionHandler.monitor_sessions()` (`session_handler.py`, lines 95–102) iterates all session hosts in a host pool sequentially, making one `get_user_sessions()` API call per host. In large deployments with many session hosts, this is an **O(n) sequential bottleneck** with no parallelism or batching:

```python
for host in session_hosts:
    host_name = host.name.split('/')[-1]
    sessions = self.get_user_sessions(host_pool_name, host_name)
    all_sessions.extend(sessions)
```

A `ThreadPoolExecutor` or `asyncio` approach would be required for scale.

### Eager List Materialisation
Multiple locations eagerly load all results into memory:
- `ConnectionManager.list_host_pools()` → `list(self.avd_client.host_pools.list_by_resource_group(...))` (`connection_manager.py`, line 68)
- `SessionHandler.list_session_hosts()` → `list(self.connection_manager.avd_client.session_hosts.list(...))` (`session_handler.py`, line 28)
- `SessionHandler.get_user_sessions()` → `list(self.connection_manager.avd_client.user_sessions.list(...))` (`session_handler.py`, line 47)

Azure SDK paginators are consumed in full before returning. For environments with hundreds of host pools or thousands of session hosts, this could cause high memory usage and long initial response times. **No page-size limit, no timeout, no streaming** (TODO-ARCH-058).

### No Connection Pooling or Client Reuse Strategy
`ConnectionManager` holds a single set of SDK clients. There is no connection pool, retry policy, or circuit breaker. If `connect()` fails partway through (e.g., `ComputeManagementClient` raises), the `avd_client` may already be set while `network_client` remains `None` — a partially-connected state with no recovery path beyond calling `disconnect()` and `connect()` again.

### No Caching
There is no caching of host pool lists, session host inventories, or session data. Every call to `list_host_pools()` or `list_session_hosts()` issues a live API request. For polling or monitoring use cases, this will generate high API call volumes.

### No Rate Limiting or Retry Logic
The library does not implement exponential backoff, retry on throttle (`429 Too Many Requests`), or jitter. Azure Management APIs enforce per-subscription rate limits; sustained polling without retry logic will result in failed requests that are silently swallowed and logged as errors.

### Single-Threaded, Single-Process
The library is designed for single-threaded, single-process use. There is no thread-safety mechanism around the shared `ConnectionManager` state (`credential`, `avd_client`, etc.). Concurrent use from multiple threads would require external locking.

### `active_sessions` Dict is Unused
`self.active_sessions = {}` is initialised in `SessionHandler.__init__()` (`session_handler.py`, line 18) but never written to or read from anywhere in the codebase. This suggests an intended local cache that was never implemented. **Recommended resolution (TODO-ARCH-069):**
- Either remove it to reduce confusion
- Or implement it as a local cache for `monitor_sessions()` results to avoid repeated API calls on subsequent invocations

### Dependency Version Pinning
All dependencies in `requirements.txt` are hard-pinned to exact versions (e.g., `azure-mgmt-compute==30.5.0`). While this ensures reproducibility, it means the library will not automatically receive security patches in transitive dependencies without manual updates.

### Future Expansion: Compute and Network Operations
`compute_client` and `network_client` are instantiated in `ConnectionManager.connect()` but never used. These are reserved for planned features (TODO-ARCH-070):
- **Compute operations:** VM power state management (start, stop, restart) via `compute_client`
- **Network operations:** NIC/IP queries, network security group rules via `network_client`

---

## 9. End-to-End Usage Flow Sequence Diagram

The happy-path flow illustrated in `examples/basic_usage.py` follows this sequence:

```
Consumer Code
    │
    ├─→ Config() [lines 8–10]
    │   └─→ load_dotenv() [config.py:20]
    │   └─→ _load_config() [config.py:27–52]
    │       └─→ yaml.safe_load() if config_file exists
    │       └─→ os.getenv() for each key
    │
    ├─→ config.validate() [lines 12–14]
    │   └─→ Check subscription_id and resource_group present
    │
    ├─→ ConnectionManager(subscription_id, resource_group) [lines 20–23]
    │   └─→ __init__() initialises credential=None, avd_client=None
    │
    ├─→ manager.connect() [line 26]
    │   ├─→ authenticate() [connection_manager.py:31–37]
    │   │   └─→ DefaultAzureCredential() [bypasses AzureAuthenticator]
    │   └─→ Instantiate three SDK clients [lines 47–55]
    │       ├─→ DesktopVirtualizationMgmtClient
    │       ├─→ ComputeManagementClient
    │       └─→ NetworkManagementClient
    │
    ├─→ manager.list_host_pools() [line 29]
    │   └─→ list(avd_client.host_pools.list_by_resource_group(...))
    │
    ├─→ manager.get_host_pool(pool_name) [line 40]
    │   └─→ avd_client.host_pools.get(resource_group, pool_name)
    │
    ├─→ SessionHandler(manager) [line 44]
    │   └─→ __init__() stores connection_manager reference
    │
    ├─→ session_handler.monitor_sessions(pool_name) [line 45]
    │   ├─→ list_session_hosts(pool_name)
    │   │   └─→ list(avd_client.session_hosts.list(...))
    │   └─→ For each host:
    │       └─→ get_user_sessions(pool_name, host_name)
    │           └─→ list(avd_client.user_sessions.list(...))
    │
    └─→ manager.disconnect() [line 49]
        └─→ Set all clients and credential to None
```

**Reference:** `examples/basic_usage.py` lines 8–49 (TODO-ARCH-005).

---

## 10. Configuration Usage Patterns

### Pattern 1: YAML File (README.md example)
```python
config = Config('config.yaml')
config.validate()
```

### Pattern 2: Environment Variables + Manual Set (basic_usage.py example)
```python
config = Config()
config.set('subscription_id', 'your-subscription-id')
config.set('resource_group', 'your-resource-group')
config.validate()
```

**Inconsistency (TODO-ARCH-010):** The two usage patterns are documented differently in README.md vs. examples/basic_usage.py. The README shows YAML file usage, while the example shows manual `set()` calls. These should be reconciled with clear guidance on when to use each pattern.

---

## Summary Table

| Concern | Current State | Risk / Gap |
|---|---|---|
| Authentication | `DefaultAzureCredential` only in `ConnectionManager`; `AzureAuthenticator` unused | Service-principal path not wired into `ConnectionManager` |
| Secret persistence | `Config.save()` writes secrets to YAML plaintext | High — credential leakage risk |
| Session monitoring | Sequential, blocking, no parallelism | Performance bottleneck at scale |
| Error handling | Exceptions swallowed, return `None`/`[]` | Silent failures; hard to diagnose in production |
| Caching | None | High API call volume for repeated queries |
| Retry / rate limiting | None | Fragile under Azure throttling |
| Async support | None | Not suitable for high-concurrency scenarios |
| Test coverage | `Config` and `ConnectionManager` only; `SessionHandler` and `AzureAuthenticator` untested | Gaps in coverage |
| `active_sessions` | Declared, never used | Dead code / incomplete feature |
| CI/CD pipeline | None | No automated testing or deployment |
| `.gitignore` | Missing | Risk of committing `.env` files and `__pycache__/` |
| `pyproject.toml` | Missing | Not PEP 517/518 compliant |
| Context manager | Not implemented | Manual `disconnect()` calls required |
| Unused imports | `AzureAuthenticator` in `connection_manager.py`, `datetime` in `session_handler.py` | Dead code / technical debt |
| Unused clients | `compute_client`, `network_client` instantiated but never used | Reserved for future expansion (undocumented) |
| Unprocessed config keys | `logging.level`, `logging.file`, `host_pools` loaded but never used | Dead code configuration |