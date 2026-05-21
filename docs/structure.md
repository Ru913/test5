# Azure Virtual Desktop Manager — Project Structure Document

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Directory Layout and Organization Rationale](#2-directory-layout-and-organization-rationale)
3. [Module Organization and Boundaries](#3-module-organization-and-boundaries)
4. [Key Files and Their Purposes](#4-key-files-and-their-purposes)
5. [Naming Conventions and Patterns](#5-naming-conventions-and-patterns)
6. [Build and Configuration File Structure](#6-build-and-configuration-file-structure)
7. [Entry Points](#7-entry-points)
8. [Test Organization and Patterns](#8-test-organization-and-patterns)
9. [Shared / Common Code Organization](#9-shared--common-code-organization)
10. [Dependency Map](#10-dependency-map)
11. [Known Gaps and Inconsistencies](#11-known-gaps-and-inconsistencies)

---

## 1. Project Overview

**Package name:** `avd-manager` (PyPI distribution name, as declared in `setup.py`)
**Importable name:** `avd_manager`
**Version:** `0.1.0` (Alpha)
**Python requirement:** ≥ 3.8
**Purpose:** A Python library and toolset for managing Azure Virtual Desktop (AVD) environments — authenticating to Azure, enumerating host pools, and monitoring/disconnecting user sessions.

The repository root is `QA-Test-Repo/` and contains **exactly 16 files** across 5 logical areas: the installable package (7 files), a test suite (3 files), usage examples (2 files), and project-level configuration/documentation (4 files).

**Note:** The `README.md` file lists a `docs/` directory in its project structure diagram, but **this directory does not exist** in the actual repository. This is a documentation error that should be corrected in `README.md`.

---

## 2. Directory Layout and Organization Rationale

```
QA-Test-Repo/
├── avd_manager/                  # Installable Python package (core library) — 7 files
│   ├── __init__.py               (285 bytes)
│   ├── config.py                 (2,764 bytes)
│   ├── connection_manager.py     (3,724 bytes)
│   ├── session_handler.py        (4,256 bytes)
│   └── utils/                    # Internal utility sub-package — 3 files
│       ├── __init__.py           (155 bytes)
│       ├── auth.py               (2,334 bytes)
│       └── logger.py             (1,543 bytes)
├── tests/                        # Unit test suite — 3 files
│   ├── __init__.py               (33 bytes)
│   ├── test_config.py            (1,780 bytes)
│   └── test_connection_manager.py (1,829 bytes)
├── examples/                     # Runnable usage demonstrations — 2 files
│   ├── basic_usage.py            (1,611 bytes)
│   └── config.yaml               (559 bytes)
├── README.md                     # User-facing documentation (2,729 bytes)
├── CONTRIBUTING.md               # Contributor guidelines (1,507 bytes)
├── requirements.txt              # Pinned runtime dependencies (168 bytes)
└── setup.py                      # Package build/install metadata (811 bytes)
```

**File Count by Layer:**

| Layer | File Count | Files |
|---|---|---|
| `avd_manager/` | 7 | `__init__.py`, `config.py`, `connection_manager.py`, `session_handler.py`, `utils/__init__.py`, `utils/auth.py`, `utils/logger.py` |
| `tests/` | 3 | `__init__.py`, `test_config.py`, `test_connection_manager.py` |
| `examples/` | 2 | `basic_usage.py`, `config.yaml` |
| Project root | 4 | `README.md`, `CONTRIBUTING.md`, `requirements.txt`, `setup.py` |
| **Total** | **16** | — |

**Rationale observed in the codebase:**

| Layer | Rationale |
|---|---|
| `avd_manager/` | Encapsulates all library code under a single importable namespace. `setup.py` uses `find_packages()`, so any directory with an `__init__.py` is auto-discovered. |
| `avd_manager/utils/` | Cross-cutting concerns (logging, authentication) are isolated in a dedicated sub-package to avoid circular imports and keep core modules focused on business logic. |
| `tests/` | Kept at the project root (sibling to the package) so that `python -m unittest discover tests` works without path manipulation, as documented in `README.md` and `CONTRIBUTING.md`. |
| `examples/` | Separated from the package and tests so that demonstration scripts are never accidentally imported or executed as part of the test run. The `config.yaml` template is co-located with the example script for convenience, though it is not automatically loaded by `basic_usage.py` (which calls `Config()` with no arguments). |

**Virtual Environment Directory:** `CONTRIBUTING.md` instructs contributors to create a `venv/` directory via `python -m venv venv`. This directory is runtime-only and should be excluded from version control (typically via `.gitignore`).

---

## 3. Module Organization and Boundaries

### 3.1 Public Package API — `avd_manager/`

The package exposes exactly three public symbols via `avd_manager/__init__.py` (line 6–7):

```python
from .connection_manager import ConnectionManager
from .session_handler import SessionHandler
from .config import Config

__all__ = ["ConnectionManager", "SessionHandler", "Config"]
```

This means consumers only need a single import:

```python
from avd_manager import ConnectionManager, SessionHandler, Config
```

Internal modules (`utils.*`) are **not** re-exported at the top level, enforcing a clear public/private boundary. However, `AzureAuthenticator` and `get_logger` are available via `avd_manager.utils` (see §9).

### 3.2 Module Responsibilities

| Module | Class / Symbol | Responsibility |
|---|---|---|
| `avd_manager/config.py` | `Config` | Loads configuration from a YAML file and/or environment variables; validates required fields (`subscription_id`, `resource_group`); supports get/set/save operations. Calls `load_dotenv()` on instantiation to auto-load `.env` files. |
| `avd_manager/connection_manager.py` | `ConnectionManager` | Authenticates to Azure and creates SDK clients for AVD, Compute, and Network services; lists and retrieves host pools; manages connection lifecycle. |
| `avd_manager/session_handler.py` | `SessionHandler` | Wraps the AVD SDK to list session hosts, retrieve user sessions, disconnect sessions, and aggregate session monitoring across a host pool. |
| `avd_manager/utils/auth.py` | `AzureAuthenticator` | Abstracts credential selection with three public methods: `get_credential()` (auto-selects based on config), `get_default_credential()` (uses `DefaultAzureCredential`), and `get_service_principal_credential()` (uses `ClientSecretCredential` when tenant/client/secret are provided). |
| `avd_manager/utils/logger.py` | `get_logger()`, `setup_file_logging()` | Provides a consistently formatted logger (console + optional file handler) used by every module in the package. `get_logger(name, level)` returns a named logger with a `StreamHandler` to `sys.stdout`; `setup_file_logging(log_file, level)` attaches a `FileHandler` to the root logger and auto-creates log directories. |

### 3.3 Inter-Module Dependency Flow

```
Config  ──► stdlib: os, pathlib
        ──► pyyaml
        ──► python-dotenv
        ──► utils/logger

ConnectionManager  ──► azure-identity (DefaultAzureCredential)
                   ──► azure-mgmt-desktopvirtualization
                   ──► azure-mgmt-compute
                   ──► azure-mgmt-network
                   ──► utils/logger
                   ──► utils/auth (AzureAuthenticator — imported but not used)

SessionHandler     ──► stdlib: logging
                   ──► utils/logger
                   ──► ConnectionManager (injected via constructor)

utils/auth         ──► azure-identity (DefaultAzureCredential, ClientSecretCredential)
                   ──► utils/logger

utils/logger       ──► stdlib: logging, sys, pathlib
```

**Key observations:**
- `SessionHandler` depends on `ConnectionManager` through **constructor injection** (not a direct import of the class), which keeps the coupling loose and simplifies mocking in tests.
- `ConnectionManager` imports `AzureAuthenticator` from `utils/auth` but does **not use it** — it calls `DefaultAzureCredential()` directly in the `authenticate()` method (line 35). This is an architectural inconsistency (dead import).
- `SessionHandler` imports `datetime` from the standard library (line 1) but **never uses it** anywhere in the module — this is an unused import that should be removed.

---

## 4. Key Files and Their Purposes

### `avd_manager/__init__.py` (285 bytes)
Declares `__version__ = "0.1.0"` and `__author__ = "QA Test Team"` (lines 3–4). Re-exports the three public classes (`ConnectionManager`, `SessionHandler`, `Config`) and defines `__all__` (lines 6–9). This is the sole file that determines the package's public surface area.

### `avd_manager/config.py` (2,764 bytes)
Implements the `Config` class. Key behaviors:
- Constructor calls `load_dotenv()` (line 17) on instantiation to pick up `.env` files automatically.
- `_load_config()` (lines 24–54) merges YAML file values with environment variable overrides; environment variables always win. Maps five Azure credential keys: `subscription_id`, `resource_group`, `tenant_id`, `client_id`, `client_secret`. Also loads `logging` and `host_pools` keys from YAML but **does not validate or expose them** via the public API.
- `validate()` (lines 62–70) checks that `subscription_id` and `resource_group` are non-empty; raises `ValueError` if not. Does **not** validate `tenant_id`, `client_id`, or `client_secret` even when service-principal auth is intended.
- `save(output_file)` (lines 72–76) serializes the in-memory config back to a YAML file.
- Uses `pathlib.Path` to check if a config file exists before opening it (line 28).

### `avd_manager/connection_manager.py` (3,724 bytes)
Implements `ConnectionManager`. Key behaviors:
- Constructor (lines 15–26) initializes subscription ID, resource group, and sets all client references to `None`.
- `authenticate()` (lines 28–35) creates a `DefaultAzureCredential` and stores it on the instance; returns `True` on success, `False` on failure.
- `connect()` (lines 37–56) lazily calls `authenticate()` if needed, then instantiates three Azure SDK management clients: `DesktopVirtualizationMgmtClient`, `ComputeManagementClient`, `NetworkManagementClient`.
- `list_host_pools()` (lines 58–70) and `get_host_pool()` (lines 72–85) delegate to `avd_client.host_pools`.
- `disconnect()` (lines 87–92) sets all client references to `None`, releasing SDK resources.
- Imports `AzureAuthenticator` from `utils/auth` (line 6) but does not use it — `authenticate()` calls `DefaultAzureCredential()` directly.

### `avd_manager/session_handler.py` (4,256 bytes)
Implements `SessionHandler`. Key behaviors:
- Constructor (lines 11–18) stores a reference to `ConnectionManager` and initializes `self.active_sessions = {}` (line 16), which is **never populated or read** by any method in the class.
- All methods guard against a disconnected state by checking `connection_manager.avd_client` (e.g., line 22).
- `list_session_hosts()` (lines 20–35), `get_user_sessions()` (lines 37–52), and `disconnect_user_session()` (lines 54–68) are low-level wrappers around AVD SDK calls.
- `get_session_host_status()` (lines 70–90) returns a plain `dict` (not an SDK object), normalizing the data shape for callers.
- `monitor_sessions()` (lines 92–104) is a higher-level aggregator that calls `list_session_hosts()` and `get_user_sessions()` in a loop, returning a flat list of all sessions across a host pool. Uses the `host.name.split('/')[-1]` pattern to strip the ARM resource path prefix (line 99).
- Imports `datetime` from the standard library (line 1) but **never uses it** — this is an unused import.

### `avd_manager/utils/__init__.py` (155 bytes)
Re-exports the two utility symbols (lines 3–4):
```python
from .logger import get_logger
from .auth import AzureAuthenticator

__all__ = ["get_logger", "AzureAuthenticator"]
```

This allows consumers to import from either `avd_manager.utils` or the specific sub-module, making both of these valid:
```python
from avd_manager.utils import get_logger, AzureAuthenticator
from avd_manager.utils.logger import get_logger
from avd_manager.utils.auth import AzureAuthenticator
```

### `avd_manager/utils/auth.py` (2,334 bytes)
Implements `AzureAuthenticator`. Key behaviors:
- Constructor (lines 10–21) stores tenant ID, client ID, and client secret for later use.
- `get_default_credential()` (lines 23–32) returns a `DefaultAzureCredential` instance.
- `get_service_principal_credential()` (lines 34–50) returns a `ClientSecretCredential` instance; raises `ValueError` if service principal fields are not fully configured.
- `get_credential()` (lines 52–60) is the primary entry point: it automatically selects `ClientSecretCredential` when all three of `tenant_id`, `client_id`, and `client_secret` are provided, otherwise uses `DefaultAzureCredential`.

### `avd_manager/utils/logger.py` (1,543 bytes)
Provides two functions:
- `get_logger(name, level)` (lines 7–34) — returns a named `logging.Logger` with a `StreamHandler` to `sys.stdout`. Uses a guard (`if not logger.handlers`) on line 17 to prevent duplicate handlers when called multiple times. Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s` with `%Y-%m-%d %H:%M:%S` timestamps.
- `setup_file_logging(log_file, level)` (lines 37–59) — attaches a `FileHandler` to the root logger and auto-creates parent directories using `Path.mkdir(parents=True, exist_ok=True)` (line 41).

### `tests/__init__.py` (33 bytes)
Contains only a module docstring: `"""Test suite for AVD Manager."""` This file makes the `tests/` directory a Python package, enabling `unittest discover` to find and run test modules.

### `tests/test_config.py` (1,780 bytes)
Implements `TestConfig` class inheriting from `unittest.TestCase`. Test methods:
- `test_load_from_environment()` — uses `@patch.dict(os.environ, {...})` to inject environment variables and verify `Config` loads them correctly.
- `test_get_default_value()` — verifies `get()` returns a default when a key is missing.
- `test_set_value()` — verifies `set()` stores a value that can be retrieved.
- `test_validate_success()` — verifies `validate()` returns `True` when required fields are present.
- `test_validate_failure()` — verifies `validate()` raises `ValueError` when required fields are missing.

Imports `mock_open` from `unittest.mock` (line 3) but **never uses it** in any test method — this signals incomplete test coverage for `Config._load_config()` with a real YAML file.

### `tests/test_connection_manager.py` (1,829 bytes)
Implements `TestConnectionManager` class inheriting from `unittest.TestCase`. Test methods:
- `test_initialization()` — verifies the constructor sets subscription ID, resource group, and initializes client references to `None`.
- `test_authenticate_success()` — uses `@patch('avd_manager.connection_manager.DefaultAzureCredential')` to mock the credential and verify `authenticate()` returns `True`.
- `test_authenticate_failure()` — mocks `DefaultAzureCredential` to raise an exception and verifies `authenticate()` returns `False`.
- `test_disconnect()` — verifies `disconnect()` sets all client references to `None`.

**Missing test coverage:** `connect()`, `list_host_pools()`, and `get_host_pool()` are not tested.

### `examples/basic_usage.py` (1,611 bytes)
A standalone runnable script demonstrating the full workflow. Key steps:
1. Instantiate `Config()` with no file argument (line 9).
2. Set `subscription_id` and `resource_group` via `config.set()` (lines 10–11).
3. Call `config.validate()` (line 14).
4. Instantiate `ConnectionManager` and call `connect()` (lines 18–24).
5. Call `list_host_pools()` (line 28).
6. Extract the first host pool name using `host_pools[0].name.split('/')[-1]` (line 34) and call `get_host_pool()` (line 35).
7. Instantiate `SessionHandler` and call `monitor_sessions()` (lines 39–40).
8. Call `manager.disconnect()` (line 44).

Protected by `if __name__ == '__main__': main()` (line 56).

**Note:** The example does **not** call `disconnect_user_session()` or `get_session_host_status()`, leaving these public methods undocumented from a consumer perspective.

### `examples/config.yaml` (559 bytes)
A template YAML configuration file showing all supported keys:
- `subscription_id`, `resource_group` (required)
- `tenant_id`, `client_id`, `client_secret` (optional; enable service principal auth)
- `logging.level`, `logging.file` (optional; define logging behavior)
- `host_pools` list with `name` and `region` entries (optional; for reference only)

**Important:** This file is a **template/example only**. The `basic_usage.py` script calls `Config()` with no file argument, not `Config('examples/config.yaml')` as shown in `README.md`. A real runtime config file would be placed at the project root or a user-specified path passed to `Config(config_file=...)`.

### `setup.py` (811 bytes)
Standard `setuptools` build script. Key metadata:
- `name = "avd-manager"` (PyPI distribution name)
- `version = "0.1.0"`
- `description = "Azure Virtual Desktop Management Tool"`
- `author = "QA Test Team"`, `author_email = "qa@example.com"`
- `packages = find_packages()` (auto-discovers all directories with `__init__.py`)
- `python_requires = ">=3.8"`
- `install_requires` uses **minimum-version constraints** (`>=`) for flexible library compatibility:
  - `azure-identity>=1.15.0`
  - `azure-mgmt-desktopvirtualization>=1.0.0`
  - `azure-mgmt-compute>=30.5.0`
  - `azure-mgmt-network>=25.2.0`
  - `python-dotenv>=1.0.0`
  - `pyyaml>=6.0.1`
  - `requests>=2.31.0`

**Missing metadata fields:** `long_description`, `url`, and `license` are standard `setuptools` fields absent from `setup.py`. This is a gap, especially since `README.md` declares an MIT license but no `LICENSE` file exists in the repository.

### `requirements.txt` (168 bytes)
Pinned (exact-version) dependency list using `==` specifiers, mirroring `setup.py`'s `install_requires` but with exact versions for reproducible development environments:
```
azure-identity==1.15.0
azure-mgmt-desktopvirtualization==1.0.0
azure-mgmt-compute==30.5.0
azure-mgmt-network==25.2.0
python-dotenv==1.0.0
pyyaml==6.0.1
requests==2.31.0
```

**Version pinning strategy:** `requirements.txt` uses `==` (exact pinned) for reproducible installs, while `setup.py` uses `>=` (minimum version) for flexible library compatibility. This is an intentional dual-file strategy: developers use `requirements.txt` for consistency, while library consumers use `setup.py` for flexibility.

**Unused dependency:** `requests==2.31.0` appears in both files but **no file in the codebase imports `requests`**. This is declared as "available for future use" but should be documented or removed.

### `README.md` (2,729 bytes)
User-facing documentation. Contains:
- Feature overview
- Installation instructions (via `pip install -r requirements.txt` or `pip install -e .`)
- Configuration instructions (environment variables and YAML file)
- Basic usage example (shows `Config('config.yaml')` but `basic_usage.py` calls `Config()` with no arguments — this is a discrepancy)
- Testing instructions (`python -m unittest discover tests`)
- **Phantom directory:** Lists a `docs/` directory in the project structure diagram that does not exist in the actual repository

### `CONTRIBUTING.md` (1,507 bytes)
Contributor guidelines. Key sections:
- Getting started (fork, clone, create `venv/`, activate, install dependencies)
- Development workflow (branch, test, commit, push, PR)
- Code style (PEP 8, docstrings)
- Testing (write unit tests, use mocking for Azure API calls)
- Documentation (update README, add docstrings, update examples)

---

## 5. Naming Conventions and Patterns

### File and Directory Names
- **Package/module names:** `snake_case` throughout (`avd_manager`, `connection_manager`, `session_handler`, `config`, `utils`, `auth`, `logger`).
- **Test files:** Prefixed with `test_` followed by the name of the module under test (`test_config.py` → `config.py`, `test_connection_manager.py` → `connection_manager.py`).
- **Example files:** Descriptive lowercase names (`basic_usage.py`, `config.yaml`).

### Class Names
- `PascalCase` for all classes: `Config`, `ConnectionManager`, `SessionHandler`, `AzureAuthenticator`.

### Method Names
- `snake_case` for all methods.
- Private/internal methods are prefixed with a single underscore: `_load_config()` in `Config`.
- Public methods follow a consistent verb-noun pattern: `list_host_pools()`, `get_host_pool()`, `list_session_hosts()`, `get_user_sessions()`, `disconnect_user_session()`, `get_session_host_status()`, `monitor_sessions()`, `authenticate()`, `connect()`, `disconnect()`.

### Constants and Metadata
- Module-level dunder attributes in `__init__.py`: `__version__`, `__author__`, `__all__`.

### Docstrings
- Every module, class, and public method carries a docstring. Constructor docstrings use the `Args:` section format. Return-value documentation uses `Returns:` (visible in `auth.py` and `logger.py`).

### Logging
- Every module instantiates its logger at module level using `logger = get_logger(__name__)`, ensuring logger names mirror the Python module hierarchy (e.g., `avd_manager.config`, `avd_manager.utils.auth`).

### Shared Patterns
- **ARM resource path parsing:** Both `examples/basic_usage.py` (line 34) and `session_handler.py` `monitor_sessions()` (line 99) use `host.name.split('/')[-1]` to strip the ARM resource path prefix and extract the simple name. This pattern should be documented as a shared convention.

---

## 6. Build and Configuration File Structure

### `setup.py`

| Field | Value |
|---|---|
| `name` | `avd-manager` |
| `version` | `0.1.0` |
| `description` | `Azure Virtual Desktop Management Tool` |
| `author` | `QA Test Team` |
| `author_email` | `qa@example.com` |
| `packages` | Auto-discovered via `find_packages()` |
| `python_requires` | `>=3.8` |
| `install_requires` | See table below (uses `>=` minimum-version constraints) |

### `requirements.txt` — Pinned Dependencies

| Package | Pinned Version | Purpose |
|---|---|---|
| `azure-identity` | `1.15.0` | Azure credential providers (`DefaultAzureCredential`, `ClientSecretCredential`) |
| `azure-mgmt-desktopvirtualization` | `1.0.0` | AVD management SDK (host pools, session hosts, user sessions) |
| `azure-mgmt-compute` | `30.5.0` | Azure Compute management SDK |
| `azure-mgmt-network` | `25.2.0` | Azure Network management SDK |
| `python-dotenv` | `1.0.0` | `.env` file loading in `Config.__init__` |
| `pyyaml` | `6.0.1` | YAML config file parsing and serialization |
| `requests` | `2.31.0` | HTTP client (declared but **not used** anywhere in the codebase) |

### `examples/config.yaml` — Runtime Configuration Schema

```yaml
subscription_id: string        # Required (or AZURE_SUBSCRIPTION_ID env var)
resource_group:  string        # Required (or AZURE_RESOURCE_GROUP env var)
tenant_id:       string        # Optional; enables service principal auth
client_id:       string        # Optional; enables service principal auth
client_secret:   string        # Optional; enables service principal auth
logging:
  level:         string        # e.g. "INFO"
  file:          string        # e.g. "logs/avd_manager.log"
host_pools:
  - name:        string
    region:      string
```

Environment variables (`AZURE_SUBSCRIPTION_ID`, `AZURE_RESOURCE_GROUP`, `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`) always override YAML file values when both are present.

**Important:** The `logging` and `host_pools` keys are loaded from YAML but **never validated or accessed** via `Config.get()` in any module. They are present in the schema but undocumented and unused in the actual implementation.

### Missing Configuration Files

- **`.env` template:** `README.md` instructs users to create a `.env` file, and `config.py` calls `load_dotenv()`, but no `.env.example` or `.env` template exists in the repository.
- **`LICENSE` file:** `README.md` declares "MIT License" but no `LICENSE` or `LICENSE.txt` file is present in the repository.
- **`CHANGELOG.md` or `HISTORY.md`:** The project is versioned at `0.1.0` but no change log exists.

---

## 7. Entry Points

### Library Entry Point
The package has no CLI entry point defined in `setup.py`. It is designed as an **importable library**. The canonical entry point for consumers is:

```python
from avd_manager import ConnectionManager, SessionHandler, Config
```

**Note:** The package is **not published to PyPI**. Consumers must install via `pip install -e .` (development mode) or `pip install -r requirements.txt` from a local clone.

### Advanced Authentication Entry Point
For consumers requiring service-principal authentication or advanced credential selection, `AzureAuthenticator` is available via:

```python
from avd_manager.utils import AzureAuthenticator

authenticator = AzureAuthenticator(
    tenant_id="...",
    client_id="...",
    client_secret="..."
)
credential = authenticator.get_credential()  # Auto-selects based on config
```

### File Logging Entry Point
For consumers requiring file-based logging, `setup_file_logging()` is available via:

```python
from avd_manager.utils import get_logger
from avd_manager.utils.logger import setup_file_logging

setup_file_logging("logs/avd_manager.log", level=logging.INFO)
logger = get_logger(__name__)
```

**Note:** This function is described in §4 and §9 but is never demonstrated in `examples/basic_usage.py` or in any test. A consumer would typically read `logging.file` from `Config` and pass it to `setup_file_logging()`, but this pattern is not shown anywhere.

### Example Script Entry Point
`examples/basic_usage.py` serves as the primary runnable demonstration. It defines a `main()` function and is guarded by:

```python
if __name__ == '__main__':
    main()
```

The `main()` function demonstrates the full lifecycle:
1. Instantiate `Config()` with no file argument.
2. Set `subscription_id` and `resource_group` via `config.set()`.
3. Call `config.validate()`.
4. Instantiate `ConnectionManager` and call `connect()`.
5. Call `list_host_pools()` to retrieve all host pools.
6. Extract the first host pool name and call `get_host_pool()` to retrieve its details.
7. Instantiate `SessionHandler` and call `monitor_sessions()` to list all active sessions.
8. Call `manager.disconnect()` to close all connections.

**Missing from the example:** The `disconnect_user_session()` and `get_session_host_status()` methods are not demonstrated, leaving these public entry points undocumented from a consumer perspective.

### Test Runner Entry Points
Tests are discovered and executed via Python's built-in `unittest` runner:

```bash
python -m unittest discover tests
```

This is documented in both `README.md` and `CONTRIBUTING.md`. Individual test files also include `if __name__ == '__main__': unittest.main()` guards for direct execution:

```bash
python tests/test_config.py
python tests/test_connection_manager.py
```

---

## 8. Test Organization and Patterns

### Location
All tests reside in `tests/`, a top-level directory sibling to `avd_manager/`. The `tests/__init__.py` file (containing only a module docstring) makes the directory a Python package, enabling `unittest discover` to find and run test modules.

### Test Files

| Test File | Tested Module | Test Class | Test Methods |
|---|---|---|---|
| `tests/test_config.py` | `avd_manager/config.py` | `TestConfig` | `test_load_from_environment`, `test_get_default_value`, `test_set_value`, `test_validate_success`, `test_validate_failure` |
| `tests/test_connection_manager.py` | `avd_manager/connection_manager.py` | `TestConnectionManager` | `test_initialization`, `test_authenticate_success`, `test_authenticate_failure`, `test_disconnect` |

### Test Class and Method Patterns
- All test classes inherit from `unittest.TestCase`.
- Each class uses `setUp()` to create shared fixtures (e.g., a `ConnectionManager` instance with test subscription/resource-group IDs).
- Test method names follow `test_<scenario>` naming.

### Mocking Strategy
- **Azure SDK calls** are mocked using `unittest.mock.patch` to avoid real network calls. Example from `test_connection_manager.py` (line 23–26):
  ```python
  @patch('avd_manager.connection_manager.DefaultAzureCredential')
  def test_authenticate_success(self, mock_credential):
      mock_credential.return_value = Mock()
      result = self.manager.authenticate()
      self.assertTrue(result)
  ```
- **Environment variables** are injected using `@patch.dict(os.environ, {...})` in `test_config.py` to test environment-variable-driven configuration without polluting the real environment.
- **File I/O** — `mock_open` is imported in `test_config.py` (line 3) but **never used** in any test method, signaling incomplete test coverage for `Config._load_config()` with a real YAML file.

### Coverage Scope and Gaps

**Tested modules:**
- `TestConfig` covers: env-var loading, default value fallback, `set()`, `validate()` success, and `validate()` failure (missing required fields).
- `TestConnectionManager` covers: object initialization state, successful authentication, authentication failure handling, and disconnection (client references set to `None`). **Does not test:** `connect()`, `list_host_pools()`, `get_host_pool()`.

**Untested modules:**
- `avd_manager/session_handler.py` — **No `tests/test_session_handler.py` file exists**. All methods (`list_session_hosts()`, `get_user_sessions()`, `disconnect_user_session()`, `get_session_host_status()`, `monitor_sessions()`) are untested.
- `avd_manager/utils/auth.py` — `AzureAuthenticator` has no corresponding test file. All three public methods (`get_credential()`, `get_default_credential()`, `get_service_principal_credential()`) are untested.
- `avd_manager/utils/logger.py` — `get_logger()` and `setup_file_logging()` have no test file. The duplicate-handler guard (`if not logger.handlers`) and the `mkdir(parents=True, exist_ok=True)` behavior are untested code paths.

---

## 9. Shared / Common Code Organization

All shared/common code lives in `avd_manager/utils/`, a dedicated sub-package with its own `__init__.py`.

### `avd_manager/utils/__init__.py` (155 bytes)
Re-exports the two utility symbols (lines 3–4):
```python
from .logger import get_logger
from .auth import AzureAuthenticator

__all__ = ["get_logger", "AzureAuthenticator"]
```

This allows consumers to import from either `avd_manager.utils` or the specific sub-module.

### Logging (`avd_manager/utils/logger.py`)
- **Used by:** `config.py`, `connection_manager.py`, `session_handler.py`, `utils/auth.py` — every module in the package.
- **Pattern:** Each module calls `logger = get_logger(__name__)` at module scope, creating a named logger that inherits the package hierarchy.
- **Format:** `%(asctime)s - %(name)s - %(levelname)s - %(message)s` with `%Y-%m-%d %H:%M:%S` timestamps.
- **File logging** is opt-in via `setup_file_logging()`, which attaches to the root logger and auto-creates log directories using `Path.mkdir(parents=True, exist_ok=True)`.
- **Stdlib dependencies:** `logging`, `sys`, `pathlib`.

### Authentication (`avd_manager/utils/auth.py`)
- **Used by:** `connection_manager.py` (imported but not used in the current implementation; `ConnectionManager.authenticate()` calls `DefaultAzureCredential()` directly).
- **Pattern:** Credential selection logic is centralized here so that `ConnectionManager` and any future modules do not duplicate Azure auth logic.
- **Three public methods:**
  - `get_credential()` — auto-selects based on whether service principal fields are configured.
  - `get_default_credential()` — explicitly uses `DefaultAzureCredential`.
  - `get_service_principal_credential()` — explicitly uses `ClientSecretCredential`.

### Shared Conventions Across All Modules
- All modules import `get_logger` from `utils.logger` as their first internal import.
- All public methods follow a consistent error-handling pattern: wrap SDK calls in `try/except Exception`, log the error with `logger.error(f"... {str(e)}")`, and return a safe fallback (`False`, `None`, or `[]`) rather than propagating exceptions to callers — except where a `ConnectionError` is raised to signal a programming error (calling methods before `connect()`).
- **Pathlib usage:** Both `config.py` and `logger.py` use `pathlib.Path` for file operations. `config.py` uses `Path` to check if a config file exists before opening it (line 28); `logger.py` uses `Path` to auto-create log directories (line 41).
- **OS module usage:** `config.py` calls `os.getenv()` five times for the five Azure environment variables (lines 34–54).

---

## 10. Dependency Map

```
avd_manager (public API)
│
├── Config
│   ├── stdlib: os, pathlib
│   ├── pyyaml          (YAML parsing/serialization)
│   ├── python-dotenv   (.env file loading)
│   └── utils.logger
│
├── ConnectionManager
│   ├── azure-identity                        (DefaultAzureCredential)
│   ├── azure-mgmt-desktopvirtualization      (DesktopVirtualizationMgmtClient)
│   ├── azure-mgmt-compute                    (ComputeManagementClient)
│   ├── azure-mgmt-network                    (NetworkManagementClient)
│   ├── utils.auth                            (AzureAuthenticator — imported but not used)
│   └── utils.logger
│
├── SessionHandler
│   ├── stdlib: logging (unused import: datetime)
│   ├── ConnectionManager  (injected dependency)
│   └── utils.logger
│
└── utils/
    ├── auth.py
    │   ├── azure-identity  (DefaultAzureCredential, ClientSecretCredential)
    │   └── utils.logger
    └── logger.py
        └── stdlib: logging, sys, pathlib
```

---

## 11. Known Gaps and Inconsistencies

### Documentation Gaps

1. **Phantom `docs/` directory:** `README.md` lists a `docs/` directory in its project structure diagram (line 96), but this directory does not exist in the actual repository. This is a documentation error that should be corrected.

2. **Missing `.env` template:** `README.md` instructs users to create a `.env` file, and `config.py` calls `load_dotenv()`, but no `.env.example` or `.env` template exists in the repository.

3. **Missing `LICENSE` file:** `README.md` declares "MIT License" but no `LICENSE` or `LICENSE.txt` file is present in the repository.

4. **Missing `CHANGELOG.md`:** The project is versioned at `0.1.0` but no change log exists.

5. **Undocumented `logging` and `host_pools` YAML keys:** `examples/config.yaml` defines `logging.level`, `logging.file`, and `host_pools` list entries, but `config.py`'s `_load_config()` method only maps the five Azure credential keys via `os.getenv()`. The `logging` and `host_pools` keys are loaded from YAML but never validated or accessed via `Config.get()` in any module.

6. **Missing usage examples:** The `disconnect_user_session()` and `get_session_host_status()` methods are public but not demonstrated in `examples/basic_usage.py`. A second example script showing session disconnection and status monitoring would be helpful.

7. **Missing file logging example:** `setup_file_logging()` is a public entry point but is never demonstrated in `examples/basic_usage.py` or in any test.

8. **Discrepancy in `Config` usage:** `README.md` shows `Config('config.yaml')` but `examples/basic_usage.py` calls `Config()` with no arguments. The example script then uses `config.set()` to populate values, which is not shown in the README.

### Code Quality Issues

1. **Unused import in `session_handler.py`:** `from datetime import datetime` (line 1) is imported but never used. This should be removed.

2. **Unused attribute in `SessionHandler`:** `self.active_sessions = {}` (line 16) is initialized but never populated or read by any method. This should be removed or documented.

3. **Dead import in `connection_manager.py`:** `AzureAuthenticator` is imported (line 6) but not used in the `authenticate()` method, which calls `DefaultAzureCredential()` directly. This is an architectural inconsistency.

4. **Unused import in `test_config.py`:** `mock_open` is imported (line 3) but never used in any test method. This signals incomplete test coverage for `Config._load_config()` with a real YAML file.

5. **Unused dependency:** `requests==2.31.0` is declared in both `requirements.txt` and `setup.py` but is not imported or used anywhere in the codebase.

### Test Coverage Gaps

1. **No tests for `SessionHandler`:** All methods in `session_handler.py` are untested.

2. **No tests for `AzureAuthenticator`:** All three public methods are untested.

3. **No tests for logging utilities:** `get_logger()` and `setup_file_logging()` are untested.

4. **Incomplete `ConnectionManager` tests:** `connect()`, `list_host_pools()`, and `get_host_pool()` are not tested.

5. **Incomplete `Config` tests:** YAML file loading is not tested (despite `mock_open` being imported).

### Architectural Inconsistencies

1. **Partial validation in `Config.validate()`:** Only `subscription_id` and `resource_group` are validated. `tenant_id`, `client_id`, and `client_secret` are loaded but never validated even when service-principal auth is intended.

2. **Unused `AzureAuthenticator` in `ConnectionManager`:** The class is imported but `authenticate()` calls `DefaultAzureCredential()` directly instead of delegating to `AzureAuthenticator.get_credential()`.

3. **Version pinning strategy:** `setup.py` uses `>=` (minimum version) while `requirements.txt` uses `==` (exact pinned). While this is intentional, it should be documented more clearly.

4. **Missing `setup.py` metadata:** `long_description`, `url`, and `license` fields are absent from `setup.py`, which is a gap in standard package metadata.