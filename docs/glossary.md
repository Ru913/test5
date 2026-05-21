# Domain Glossary: Azure Virtual Desktop Manager (`avd_manager`)

**Version:** 0.1.0 (Alpha)
**Package:** `avd-manager` (PyPI) / `avd_manager` (importable)
**Cross-references:** See [architecture.md], [dataflow.md], [structure.md], and [code.md] for system design, data flow, project structure, and code documentation respectively.

---

## Table of Contents

1. [Domain-Specific Terms](#1-domain-specific-terms)
2. [Technical Terms Unique to This Project](#2-technical-terms-unique-to-this-project)
3. [Abbreviations and Acronyms](#3-abbreviations-and-acronyms)
4. [Entity Names and Business Meaning](#4-entity-names-and-business-meaning)
5. [API Terminology and Conventions](#5-api-terminology-and-conventions)
6. [Configuration Keys and Environment Variables](#6-configuration-keys-and-environment-variables)
7. [External Dependencies and SDK Terms](#7-external-dependencies-and-sdk-terms)

---

## 1. Domain-Specific Terms

Terms drawn directly from the Azure Virtual Desktop (AVD) domain as used in the codebase.

---

### `active_sessions`

A dictionary instance attribute on `SessionHandler` that is initialized as an empty `{}` at construction time. Intended as an in-memory store for tracking currently known user sessions within a `SessionHandler` instance. **Note:** This attribute is currently a placeholder stub; no current method in `SessionHandler` writes to it. The `monitor_sessions()` method builds a local `all_sessions` list instead of populating `self.active_sessions`, indicating this field is reserved for future stateful session caching functionality.

- **`SessionHandler.__init__`** in `QA-Test-Repo/avd_manager/session_handler.py` (line 20)

---

### Authentication

The process of proving identity to Azure before any management operations can be performed. The library supports two authentication strategies: **Default Credential** (environment-aware, chain-based) and **Service Principal** (explicit client-secret-based). Authentication is a prerequisite to calling `connect()`.

- **`ConnectionManager.authenticate()`** in `QA-Test-Repo/avd_manager/connection_manager.py` (lines 34–41)
- **`AzureAuthenticator`** in `QA-Test-Repo/avd_manager/utils/auth.py` (lines 9–70)

---

### Connection

The act of instantiating the three Azure management SDK clients (`avd_client`, `compute_client`, `network_client`) against a specific subscription, using a previously obtained credential. A successful `connect()` call is required before any resource-query methods can be invoked.

- **`ConnectionManager.connect()`** in `QA-Test-Repo/avd_manager/connection_manager.py` (lines 43–65)

---

### ConnectionError

A Python built-in exception raised by `ConnectionManager` and `SessionHandler` methods when called before `connect()` has been successfully invoked. Raised in guard clauses across the codebase:

- **`ConnectionManager.connect()`** in `QA-Test-Repo/avd_manager/connection_manager.py` (line 45): raised if `authenticate()` fails
- **`ConnectionManager.list_host_pools()`** in `QA-Test-Repo/avd_manager/connection_manager.py` (line 68): raised if `avd_client` is `None`
- **`ConnectionManager.get_host_pool()`** in `QA-Test-Repo/avd_manager/connection_manager.py` (line 82): raised if `avd_client` is `None`
- **`SessionHandler.list_session_hosts()`** in `QA-Test-Repo/avd_manager/session_handler.py` (line 25): raised if `avd_client` is `None`
- **`SessionHandler.get_user_sessions()`** in `QA-Test-Repo/avd_manager/session_handler.py` (line 44): raised if `avd_client` is `None`
- **`SessionHandler.disconnect_user_session()`** in `QA-Test-Repo/avd_manager/session_handler.py` (line 63): raised if `avd_client` is `None`
- **`SessionHandler.get_session_host_status()`** in `QA-Test-Repo/avd_manager/session_handler.py` (line 81): raised if `avd_client` is `None`

Unlike methods that return `False` or `None` on transient errors, `ConnectionError` signals a fatal precondition violation and should not be caught by application code expecting normal operation.

---

### Credential

An Azure SDK token-provider object (either `DefaultAzureCredential` or `ClientSecretCredential`) that is passed to each management client at construction time. Stored as `self.credential` on both `ConnectionManager` and `AzureAuthenticator`.

- **`ConnectionManager.credential`** in `QA-Test-Repo/avd_manager/connection_manager.py` (line 27)
- **`AzureAuthenticator.credential`** in `QA-Test-Repo/avd_manager/utils/auth.py` (line 22)

---

### Default Credential

The `DefaultAzureCredential` authentication path, which automatically tries a chain of credential sources (environment variables, managed identity, Azure CLI, etc.) without requiring explicit service-principal parameters. Used by `ConnectionManager.authenticate()` and `AzureAuthenticator.get_default_credential()`.

- **`ConnectionManager.authenticate()`** in `QA-Test-Repo/avd_manager/connection_manager.py` (lines 34–41)
- **`AzureAuthenticator.get_default_credential()`** in `QA-Test-Repo/avd_manager/utils/auth.py` (lines 26–36)

---

### Disconnection

The explicit teardown of all Azure client references and the credential object, performed by `ConnectionManager.disconnect()`. Sets `avd_client`, `compute_client`, `network_client`, and `credential` to `None`.

- **`ConnectionManager.disconnect()`** in `QA-Test-Repo/avd_manager/connection_manager.py` (lines 99–103)

---

### Host Pool

An Azure Virtual Desktop resource that groups one or more **session hosts** (virtual machines) and defines how users connect to desktops or remote apps. Host pools are the primary organizational unit in AVD. The library enumerates them via `list_host_pools()` and retrieves individual details via `get_host_pool()`.

- **`ConnectionManager.list_host_pools()`** in `QA-Test-Repo/avd_manager/connection_manager.py` (lines 67–79)
- **`ConnectionManager.get_host_pool()`** in `QA-Test-Repo/avd_manager/connection_manager.py` (lines 81–95)
- **`examples/config.yaml`** `host_pools` key (lines 18–22)
- **`examples/basic_usage.py`** (lines 33–44)

---

### `host_pool_name`

A string parameter used throughout `ConnectionManager` and `SessionHandler` to identify a specific host pool by its short name (the last path segment after splitting on `/`). Passed to Azure SDK calls as the pool identifier within a resource group.

- **`ConnectionManager.get_host_pool(host_pool_name)`** in `QA-Test-Repo/avd_manager/connection_manager.py` (line 81)
- **`SessionHandler.list_session_hosts(host_pool_name)`** in `QA-Test-Repo/avd_manager/session_handler.py` (line 23)
- **`SessionHandler.get_user_sessions(host_pool_name, ...)`** in `QA-Test-Repo/avd_manager/session_handler.py` (line 42)
- **`SessionHandler.disconnect_user_session(host_pool_name, ...)`** in `QA-Test-Repo/avd_manager/session_handler.py` (line 61)
- **`SessionHandler.get_session_host_status(host_pool_name, ...)`** in `QA-Test-Repo/avd_manager/session_handler.py` (line 78)
- **`SessionHandler.monitor_sessions(host_pool_name)`** in `QA-Test-Repo/avd_manager/session_handler.py` (line 101)

---

### `host_pool_type`

A property on the host pool object returned by the Azure SDK, indicating the type of the pool (e.g., pooled vs. personal). Accessed in the example script to display pool metadata.

- **`examples/basic_usage.py`** (line 44): `pool_details.host_pool_type`

---

### Last Heartbeat (`last_heart_beat` / `last_heartbeat`)

A timestamp property on a session host object indicating the most recent time the host reported its health status to the AVD control plane. Surfaced in the status dictionary returned by `get_session_host_status()` under the key `"last_heartbeat"`.

- **`SessionHandler.get_session_host_status()`** in `QA-Test-Repo/avd_manager/session_handler.py` (line 91): `session_host.last_heart_beat`

---

### Load Balancer Type (`load_balancer_type`)

A property on the host pool object returned by the Azure SDK, describing the algorithm used to distribute incoming user connections across session hosts (e.g., breadth-first or depth-first). Accessed in the example script.

- **`examples/basic_usage.py`** (line 45): `pool_details.load_balancer_type`

---

### Resource Group

An Azure logical container that holds related Azure resources (host pools, VMs, networks, etc.) under a single subscription. Used as a required scoping parameter in all Azure SDK calls made by `ConnectionManager` and `SessionHandler`.

- **`ConnectionManager.__init__(subscription_id, resource_group)`** in `QA-Test-Repo/avd_manager/connection_manager.py` (line 17)
- **`Config._load_config()`** in `QA-Test-Repo/avd_manager/config.py` (line 43)
- **`examples/config.yaml`** (line 5): `resource_group`

---

### Service Principal

An Azure Active Directory application identity used for non-interactive (automated) authentication. Requires `tenant_id`, `client_id`, and `client_secret`. Represented in the library by `AzureAuthenticator.get_service_principal_credential()`, which produces a `ClientSecretCredential`.

- **`AzureAuthenticator.get_service_principal_credential()`** in `QA-Test-Repo/avd_manager/utils/auth.py` (lines 38–57)

---

### Session

A single user's active remote desktop or remote application connection to a session host within a host pool. Sessions are enumerated via `get_user_sessions()` and can be forcibly terminated via `disconnect_user_session()`.

- **`SessionHandler.get_user_sessions()`** in `QA-Test-Repo/avd_manager/session_handler.py` (lines 42–57)
- **`SessionHandler.disconnect_user_session()`** in `QA-Test-Repo/avd_manager/session_handler.py` (lines 59–73)

---

### Session Host

A virtual machine registered with a host pool that accepts and runs user sessions. Session hosts report a `status`, a session count (`sessions`), a `last_heart_beat`, and an `update_state`. Enumerated via `list_session_hosts()` and individually queried via `get_session_host_status()`.

- **`SessionHandler.list_session_hosts()`** in `QA-Test-Repo/avd_manager/session_handler.py` (lines 23–37)
- **`SessionHandler.get_session_host_status()`** in `QA-Test-Repo/avd_manager/session_handler.py` (lines 78–97)

---

### `session_host_name`

A string parameter identifying a specific session host within a host pool. Derived at runtime by splitting the full Azure resource path on `/` and taking the last segment.

- **`SessionHandler.get_user_sessions(host_pool_name, session_host_name)`** in `QA-Test-Repo/avd_manager/session_handler.py` (line 42)
- **`SessionHandler.disconnect_user_session(..., session_host_name, ...)`** in `QA-Test-Repo/avd_manager/session_handler.py` (line 61)
- **`SessionHandler.get_session_host_status(..., session_host_name)`** in `QA-Test-Repo/avd_manager/session_handler.py` (line 78)
- **`SessionHandler.monitor_sessions()`** (internal variable `host_name`) in `QA-Test-Repo/avd_manager/session_handler.py` (line 106)

---

### `session_id`

An integer or string identifier for a specific user session on a session host. Used as the final positional argument to `user_sessions.disconnect()` in the Azure SDK call.

- **`SessionHandler.disconnect_user_session(..., session_id)`** in `QA-Test-Repo/avd_manager/session_handler.py` (lines 61–73)

---

### Session Monitoring

The composite operation of iterating over all session hosts in a host pool and collecting all active user sessions from each host into a single flat list. Implemented by `monitor_sessions()`.

- **`SessionHandler.monitor_sessions()`** in `QA-Test-Repo/avd_manager/session_handler.py` (lines 101–112)
- **`README.md`** (line 13): "Monitor and manage user sessions across host pools"

---

### Subscription

An Azure billing and access-control boundary identified by a UUID (`subscription_id`). All Azure SDK management clients are scoped to a single subscription. Required configuration field.

- **`ConnectionManager.__init__(subscription_id, ...)`** in `QA-Test-Repo/avd_manager/connection_manager.py` (line 17)
- **`Config._load_config()`** in `QA-Test-Repo/avd_manager/config.py` (line 38)

---

### `update_state`

A property on a session host object indicating the current update/patch status of the host VM. Surfaced in the status dictionary returned by `get_session_host_status()`.

- **`SessionHandler.get_session_host_status()`** in `QA-Test-Repo/avd_manager/session_handler.py` (line 92): `session_host.update_state`

---

## 2. Technical Terms Unique to This Project

Terms that describe project-specific design choices, classes, or patterns.

---

### `.env` File

A plain-text file conventionally named `.env` placed in the project root directory that stores environment variables in `KEY=VALUE` format. The `python-dotenv` library's `load_dotenv()` function reads this file and populates `os.environ` at application startup. The `Config.__init__()` method calls `load_dotenv()` unconditionally on every instantiation, making the `.env` file the primary configuration mechanism for development and local testing. The five recognized environment variables (`AZURE_SUBSCRIPTION_ID`, `AZURE_RESOURCE_GROUP`, `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`) are typically sourced from this file.

- **`Config.__init__()`** in `QA-Test-Repo/avd_manager/config.py` (line 22): `load_dotenv()`
- **`README.md`** (lines 31–38): instructions to create `.env` file
- **`python-dotenv` dependency** in `QA-Test-Repo/requirements.txt` (line 5)

---

### `__all__`

A Python module-level list that explicitly declares the public API surface of a package or module. When a user executes `from package import *`, only names listed in `__all__` are imported. In this project, `__all__` is defined in two locations to signal the intended public interface:

- **`avd_manager/__init__.py`** (line 10): `__all__ = ["ConnectionManager", "SessionHandler", "Config"]` — declares the three public classes
- **`avd_manager/utils/__init__.py`** (line 6): `__all__ = ["get_logger", "AzureAuthenticator"]` — declares the two public utilities

This mechanism prevents accidental exposure of internal implementation details and guides contributors on which classes/functions are stable API.

---

### `__version__`

A module-level dunder attribute in `avd_manager/__init__.py` (line 3) that stores the canonical programmatic version string `"0.1.0"`. This is the single source of truth for the package version and is distinct from the `version=` argument in `setup.py`. Tools and scripts can import and inspect `__version__` at runtime to determine the installed package version.

- **`avd_manager/__init__.py`** (line 3): `__version__ = "0.1.0"`

---

### `avd_client`

The instance of `DesktopVirtualizationMgmtClient` held by `ConnectionManager`. The primary SDK client used for all AVD-specific operations (host pools, session hosts, user sessions). Set to `None` before `connect()` and after `disconnect()`.

- **`ConnectionManager.avd_client`** in `QA-Test-Repo/avd_manager/connection_manager.py` (lines 28, 51–54)
- **`SessionHandler`** accesses it via `self.connection_manager.avd_client` throughout `QA-Test-Repo/avd_manager/session_handler.py`

---

### `avd_manager`

The importable Python package name for this project. Exposes `ConnectionManager`, `SessionHandler`, and `Config` as its public API via `__all__`.

- **`QA-Test-Repo/avd_manager/__init__.py`** (lines 1–10)

---

### `avd-manager`

The PyPI distribution name for the package, as declared in `setup.py`. Distinct from the importable name `avd_manager` (hyphen vs. underscore).

- **`setup.py`** (line 4): `name="avd-manager"`

---

### `compute_client`

The instance of `ComputeManagementClient` held by `ConnectionManager`. Provides access to Azure Compute resources (virtual machines, disks, etc.) associated with session hosts. Initialized during `connect()` and cleared during `disconnect()`.

- **`ConnectionManager.compute_client`** in `QA-Test-Repo/avd_manager/connection_manager.py` (lines 29, 55–58)

---

### `config_file`

An optional constructor parameter and instance attribute on `Config`. When provided and the file exists, the YAML file at this path is loaded first; environment variables then override any values found in the file.

- **`Config.__init__(config_file=None)`** in `QA-Test-Repo/avd_manager/config.py` (lines 14–25)
- **`Config._load_config()`** in `QA-Test-Repo/avd_manager/config.py` (lines 28–32)

---

### `network_client`

The instance of `NetworkManagementClient` held by `ConnectionManager`. Provides access to Azure Networking resources (virtual networks, NICs, etc.) associated with session host VMs. Initialized during `connect()` and cleared during `disconnect()`.

- **`ConnectionManager.network_client`** in `QA-Test-Repo/avd_manager/connection_manager.py` (lines 30, 59–62)

---

### `required_fields`

A local list inside `Config.validate()` that enumerates the configuration keys that must be non-empty for the library to operate. Currently contains `['subscription_id', 'resource_group']`.

- **`Config.validate()`** in `QA-Test-Repo/avd_manager/config.py` (line 67)

---

### Resource Path Splitting

A recurring pattern in the codebase where the full Azure ARM (Azure Resource Manager) resource path is split on the `/` delimiter and the last segment is extracted to obtain the short resource name. This pattern appears in:

- **`examples/basic_usage.py`** (line 40): `pool_name = host_pools[0].name.split('/')[-1]`
- **`SessionHandler.monitor_sessions()`** in `QA-Test-Repo/avd_manager/session_handler.py` (line 106): `host_name = host.name.split('/')[-1]`

For example, the full path `/subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.DesktopVirtualization/hostPools/my-pool` becomes `my-pool` after splitting and taking the last element. This is necessary because the Azure SDK returns full ARM paths, but the library's public methods accept short names as parameters.

---

### Status Dictionary

The Python `dict` returned by `SessionHandler.get_session_host_status()`, with keys `"name"`, `"status"`, `"sessions"`, `"last_heartbeat"`, and `"update_state"`. Provides a normalized view of session host health.

- **`SessionHandler.get_session_host_status()`** in `QA-Test-Repo/avd_manager/session_handler.py` (lines 86–93)

---

### `utils` Subpackage

The `avd_manager/utils/` directory is a distinct importable sub-package with its own `__init__.py` and `__all__` that exports `get_logger` and `AzureAuthenticator`. It serves as the internal utility layer, housing cross-cutting concerns (logging, authentication) that are used by the main package classes. The subpackage is not directly imported by end users; instead, utilities are accessed via the main `avd_manager` package or imported directly from `avd_manager.utils`.

- **`avd_manager/utils/__init__.py`** (lines 1–6)
- **`avd_manager/utils/logger.py`** (lines 1–59)
- **`avd_manager/utils/auth.py`** (lines 1–70)

---

## 3. Abbreviations and Acronyms

---

### AAD

**Azure Active Directory.** The identity and access management service in Azure. Rebranded by Microsoft to **Microsoft Entra ID** as of 2023, though the older name remains in use in documentation and code. Service principals and tenant IDs are AAD/Entra ID concepts. See also `tenant_id` and `Service Principal`.

- **`AzureAuthenticator.__init__`** in `QA-Test-Repo/avd_manager/utils/auth.py` (line 12): `tenant_id` parameter
- **`README.md`** (line 33): `AZURE_TENANT_ID` environment variable

---

### ARM

**Azure Resource Manager.** Microsoft's deployment and management service for Azure resources. All Azure resources are identified by hierarchical ARM paths in the format `/subscriptions/{subscription-id}/resourceGroups/{resource-group}/providers/{provider}/{resource-type}/{resource-name}`. The library uses resource path splitting to extract short names from these full ARM paths. See also `Resource Path Splitting`.

- **`SessionHandler.monitor_sessions()`** in `QA-Test-Repo/avd_manager/session_handler.py` (line 106): `host.name.split('/')[-1]` extracts the resource name from an ARM path

---

### AVD

**Azure Virtual Desktop.** Microsoft's cloud-based desktop and application virtualization service. The central domain of this project.

- **`QA-Test-Repo/avd_manager/__init__.py`** (line 1): module docstring "Azure Virtual Desktop Manager"
- **`QA-Test-Repo/avd_manager/session_handler.py`** (line 9): class docstring "Handles AVD user sessions"
- **`QA-Test-Repo/tests/__init__.py`** (line 1): "Test suite for AVD Manager"

---

### CI

**Continuous Integration.** Referenced in `CONTRIBUTING.md` in the context of automated checks that must pass before a pull request is merged.

- **`CONTRIBUTING.md`** (line 43): "Ensure CI checks pass"

---

### mgmt

**Management.** Prefix used in Azure Python SDK package names (`azure-mgmt-desktopvirtualization`, `azure-mgmt-compute`, `azure-mgmt-network`) and their corresponding client class names (`DesktopVirtualizationMgmtClient`, `ComputeManagementClient`, `NetworkManagementClient`).

- **`QA-Test-Repo/avd_manager/connection_manager.py`** (lines 3–5)
- **`requirements.txt`** (lines 2–4)

---

### PEP

**Python Enhancement Proposal.** A numbered design document describing a new feature, process, or standard for the Python language and ecosystem. **PEP 8** specifically is the official style guide for Python code, mandating conventions for indentation, naming, whitespace, and comments. The project's `CONTRIBUTING.md` requires contributors to follow PEP 8.

- **`CONTRIBUTING.md`** (line 26): "Follow PEP 8 guidelines"

---

### PR

**Pull Request.** A GitHub workflow concept referenced in `CONTRIBUTING.md` for submitting code changes for review.

- **`CONTRIBUTING.md`** (lines 22, 38, 43, 44): "Pull Request", "submitting PR"

---

### PyPI

**Python Package Index.** The public repository where the `avd-manager` package is intended to be distributed. Referenced implicitly by the `setup.py` configuration.

- **`setup.py`** (lines 3–26)

---

### VM

**Virtual Machine.** A software-based computer that runs on physical hardware, typically in a cloud environment. In the context of AVD, session hosts are VMs that run user sessions. The `ComputeManagementClient` provides access to VM resources. See also `Session Host` and `ComputeManagementClient`.

- **`SessionHandler`** in `QA-Test-Repo/avd_manager/session_handler.py` (line 9): session hosts are VMs
- **`ConnectionManager.compute_client`** in `QA-Test-Repo/avd_manager/connection_manager.py` (line 29): manages VM resources

---

### YAML

**YAML Ain't Markup Language.** The human-readable data serialization format used for the project's optional configuration file. Parsed using the `pyyaml` library (`yaml.safe_load`, `yaml.dump`).

- **`Config._load_config()`** in `QA-Test-Repo/avd_manager/config.py` (line 33): `yaml.safe_load(f)`
- **`Config.save()`** in `QA-Test-Repo/avd_manager/config.py` (line 82): `yaml.dump(...)`
- **`QA-Test-Repo/examples/config.yaml`** (all lines)

---

## 4. Entity Names and Business Meaning

Classes and objects that represent real-world or system-level concepts.

---

### `AzureAuthenticator`

A utility class in `avd_manager/utils/auth.py` that encapsulates Azure credential acquisition logic. Supports two strategies: default credential chain (`get_default_credential`) and explicit service principal (`get_service_principal_credential`). The `get_credential()` method selects the appropriate strategy based on whether all three service-principal fields are populated.

**Architectural Note:** `AzureAuthenticator` is imported in `connection_manager.py` (line 8) but is **never called** by `ConnectionManager.authenticate()`. Instead, `ConnectionManager.authenticate()` directly instantiates `DefaultAzureCredential` without using `AzureAuthenticator`. This represents a parallel, non-integrated authentication path. Contributors extending authentication logic should be aware of this divergence and decide whether to unify the paths or maintain both.

- **`AzureAuthenticator`** in `QA-Test-Repo/avd_manager/utils/auth.py` (lines 9–70)
- Exported from `QA-Test-Repo/avd_manager/utils/__init__.py` (line 5)

---

### `ClientSecretCredential`

An Azure SDK class (from `azure.identity`) that authenticates using an explicit service principal's `tenant_id`, `client_id`, and `client_secret`. Used by `AzureAuthenticator.get_service_principal_credential()`.

- **`AzureAuthenticator.get_service_principal_credential()`** in `QA-Test-Repo/avd_manager/utils/auth.py` (lines 48–53)

---

### `ComputeManagementClient`

An Azure SDK management client (from `azure.mgmt.compute`) for interacting with Azure Compute resources. Stored as `ConnectionManager.compute_client`.

- **`ConnectionManager.connect()`** in `QA-Test-Repo/avd_manager/connection_manager.py` (lines 55–58)

---

### `Config`

The configuration management class. Loads settings from an optional YAML file and/or environment variables, validates required fields, and provides `get`/`set` accessors. One of the three public API classes exported from the `avd_manager` package.

- **`Config`** in `QA-Test-Repo/avd_manager/config.py` (lines 12–83)
- Exported from `QA-Test-Repo/avd_manager/__init__.py` (line 9)

---

### `ConnectionManager`

The central orchestration class. Holds the Azure credential and the three management SDK clients. Provides methods to authenticate, connect, list/get host pools, and disconnect. One of the three public API classes exported from the `avd_manager` package.

- **`ConnectionManager`** in `QA-Test-Repo/avd_manager/connection_manager.py` (lines 13–103)
- Exported from `QA-Test-Repo/avd_manager/__init__.py` (line 7)

---

### `DefaultAzureCredential`

An Azure SDK class (from `azure.identity`) that automatically tries a chain of credential sources. Used by `ConnectionManager.authenticate()` and `AzureAuthenticator.get_default_credential()`.

- **`ConnectionManager.authenticate()`** in `QA-Test-Repo/avd_manager/connection_manager.py` (line 36)
- **`AzureAuthenticator.get_default_credential()`** in `QA-Test-Repo/avd_manager/utils/auth.py` (line 33)

---

### `DesktopVirtualizationMgmtClient`

An Azure SDK management client (from `azure.mgmt.desktopvirtualization`) for all AVD-specific operations. Stored as `ConnectionManager.avd_client`. Exposes sub-clients `host_pools`, `session_hosts`, and `user_sessions`.

- **`ConnectionManager.connect()`** in `QA-Test-Repo/avd_manager/connection_manager.py` (lines 51–54)

---

### `NetworkManagementClient`

An Azure SDK management client (from `azure.mgmt.network`) for interacting with Azure Networking resources. Stored as `ConnectionManager.network_client`.

- **`ConnectionManager.connect()`** in `QA-Test-Repo/avd_manager/connection_manager.py` (lines 59–62)

---

### `SessionHandler`

The class responsible for all session-level operations: listing session hosts, retrieving user sessions, disconnecting individual sessions, querying session host status, and monitoring all sessions in a pool. Depends on a `ConnectionManager` instance. One of the three public API classes exported from the `avd_manager` package.

- **`SessionHandler`** in `QA-Test-Repo/avd_manager/session_handler.py` (lines 9–112)
- Exported from `QA-Test-Repo/avd_manager/__init__.py` (line 8)

---

### `setUp()`

A lifecycle method in `unittest.TestCase` subclasses that is automatically invoked before each test method. Used to initialize shared test state and fixtures. Both `TestConfig` and `TestConnectionManager` define `setUp()` to create fresh test objects before each test runs, ensuring test isolation.

- **`TestConfig.setUp()`** in `QA-Test-Repo/tests/test_config.py` (lines 11–16): initializes `self.test_config` dictionary
- **`TestConnectionManager.setUp()`** in `QA-Test-Repo/tests/test_connection_manager.py` (lines 11–15): initializes `self.manager` instance

---

### `TestConfig`

The `unittest.TestCase` subclass covering `Config` behavior: loading from environment variables, default value retrieval, value setting, and validation success/failure.

- **`TestConfig`** in `QA-Test-Repo/tests/test_config.py` (lines 9–57)

---

### `TestConnectionManager`

The `unittest.TestCase` subclass covering `ConnectionManager` behavior: initialization state, successful and failed authentication (using mocks), and disconnection.

- **`TestConnectionManager`** in `QA-Test-Repo/tests/test_connection_manager.py` (lines 8–49)

---

## 5. API Terminology and Conventions

Method names, calling conventions, and patterns used in the public and internal API.

---

### `authenticate()`

A method on `ConnectionManager` that acquires a `DefaultAzureCredential` and stores it in `self.credential`. Returns `True` on success, `False` on failure (never raises). Called automatically by `connect()` if no credential is present.

- **`ConnectionManager.authenticate()`** in `QA-Test-Repo/avd_manager/connection_manager.py` (lines 34–41)

---

### `connect()`

A method on `ConnectionManager` that calls `authenticate()` if needed, then instantiates all three Azure management clients. Returns `True` on success, `False` on failure. Raises `ConnectionError` only if authentication itself fails.

- **`ConnectionManager.connect()`** in `QA-Test-Repo/avd_manager/connection_manager.py` (lines 43–65)

---

### `disconnect()`

A method on `ConnectionManager` that nullifies all client and credential references, effectively releasing the connection. Does not raise exceptions.

- **`ConnectionManager.disconnect()`** in `QA-Test-Repo/avd_manager/connection_manager.py` (lines 99–103)

---

### `disconnect_user_session()`

A method on `SessionHandler` that calls the Azure SDK `user_sessions.disconnect()` to forcibly terminate a specific user session identified by `host_pool_name`, `session_host_name`, and `session_id`. Returns `True` on success, `False` on failure.

- **`SessionHandler.disconnect_user_session()`** in `QA-Test-Repo/avd_manager/session_handler.py` (lines 59–73)

---

### `get()` / `set()`

Accessor methods on `Config` for reading and writing individual configuration key-value pairs from/to the internal `self.config` dictionary. `get()` accepts an optional `default` parameter.

- **`Config.get(key, default=None)`** in `QA-Test-Repo/avd_manager/config.py` (lines 60–62)
- **`Config.set(key, value)`** in `QA-Test-Repo/avd_manager/config.py` (lines 64–67)

---

### `get_credential()`

A method on `AzureAuthenticator` that selects and returns the appropriate credential type: `ClientSecretCredential` if all three service-principal fields are set, otherwise `DefaultAzureCredential`.

- **`AzureAuthenticator.get_credential()`** in `QA-Test-Repo/avd_manager/utils/auth.py` (lines 60–70)

---

### `get_host_pool()`

A method on `ConnectionManager` that retrieves a single host pool object by name from the Azure API. Returns the host pool object on success, `None` on failure.

- **`ConnectionManager.get_host_pool(host_pool_name)`** in `QA-Test-Repo/avd_manager/connection_manager.py` (lines 81–95)

---

### `get_logger()`

A module-level factory function in `avd_manager/utils/logger.py` that returns a named `logging.Logger` instance with a console handler and a standard timestamp formatter. Idempotent: does not add duplicate handlers if called multiple times with the same name.

- **`get_logger(name, level=logging.INFO)`** in `QA-Test-Repo/avd_manager/utils/logger.py` (lines 8–35)
- Exported from `QA-Test-Repo/avd_manager/utils/__init__.py` (line 4)

---

### `get_session_host_status()`

A method on `SessionHandler` that retrieves a session host object from the Azure SDK and returns a normalized status dictionary with keys `"name"`, `"status"`, `"sessions"`, `"last_heartbeat"`, and `"update_state"`. Returns `None` on failure.

- **`SessionHandler.get_session_host_status()`** in `QA-Test-Repo/avd_manager/session_handler.py` (lines 78–97)

---

### `get_user_sessions()`

A method on `SessionHandler` that returns a list of active user session objects on a specific session host, via the Azure SDK `user_sessions.list()` call.

- **`SessionHandler.get_user_sessions()`** in `QA-Test-Repo/avd_manager/session_handler.py` (lines 42–57)

---

### `list_by_resource_group()`

An Azure SDK method on the `host_pools` sub-client that returns an iterable (not a plain Python list) of all host pool objects in a resource group. The `ConnectionManager.list_host_pools()` method wraps this call in `list(...)` to convert the iterable to a concrete list, which is necessary for determining the length and iterating multiple times. This wrapping behavior is important for large environments where pagination might be involved.

- **`ConnectionManager.list_host_pools()`** in `QA-Test-Repo/avd_manager/connection_manager.py` (line 70): `list(self.avd_client.host_pools.list_by_resource_group(...))`

---

### `list_host_pools()`

A method on `ConnectionManager` that returns a Python list of all host pool objects in the configured resource group, via the Azure SDK `host_pools.list_by_resource_group()` call. Returns an empty list on failure.

- **`ConnectionManager.list_host_pools()`** in `QA-Test-Repo/avd_manager/connection_manager.py` (lines 67–79)

---

### `list_session_hosts()`

A method on `SessionHandler` that returns a Python list of all session host objects in a given host pool, via the Azure SDK `session_hosts.list()` call. Returns an empty list on failure.

- **`SessionHandler.list_session_hosts()`** in `QA-Test-Repo/avd_manager/session_handler.py` (lines 23–37)

---

### `monitor_sessions()`

A method on `SessionHandler` that aggregates all user sessions across all session hosts in a host pool into a single flat list. Internally calls `list_session_hosts()` and `get_user_sessions()` for each host.

- **`SessionHandler.monitor_sessions()`** in `QA-Test-Repo/avd_manager/session_handler.py` (lines 101–112)

---

### `patch()` / `patch.dict()` (unittest.mock)

Testing utilities from the `unittest.mock` module used to replace real objects with mocks during unit tests. `patch()` replaces a target object (typically an imported class or function) with a `Mock` instance for the duration of a test. `patch.dict()` temporarily replaces dictionary contents (typically `os.environ`) for test isolation. Both test files use these extensively:

- **`TestConfig`** in `QA-Test-Repo/tests/test_config.py` (lines 20, 33): `@patch.dict(os.environ, {...})` to mock environment variables
- **`TestConnectionManager`** in `QA-Test-Repo/tests/test_connection_manager.py` (lines 23, 31): `@patch('avd_manager.connection_manager.DefaultAzureCredential')` to mock the credential class

This mocking strategy isolates Azure SDK calls and prevents tests from requiring actual Azure credentials or network access.

---

### `save()`

A method on `Config` that serializes the current in-memory configuration dictionary to a YAML file at a specified output path.

- **`Config.save(output_file)`** in `QA-Test-Repo/avd_manager/config.py` (lines 79–83)

---

### `setup_file_logging()`

A module-level function in `avd_manager/utils/logger.py` that attaches a `FileHandler` to the root logger, creating any necessary parent directories. Intended to be called once at application startup to enable persistent log files.

- **`setup_file_logging(log_file, level=logging.INFO)`** in `QA-Test-Repo/avd_manager/utils/logger.py` (lines 38–59)

---

### `validate()`

A method on `Config` that checks that all `required_fields` (`subscription_id`, `resource_group`) are present and non-empty. Returns `True` on success; raises `ValueError` with a descriptive message listing missing fields on failure.

- **`Config.validate()`** in `QA-Test-Repo/avd_manager/config.py` (lines 65–75)

---

### `_load_config()`

A private method on `Config` called during `__init__`. Loads the YAML file (if provided and present), then overlays values from the five recognized environment variables. The environment variables always take precedence over file values.

- **`Config._load_config()`** in `QA-Test-Repo/avd_manager/config.py` (lines 28–56)

---

## 6. Configuration Keys and Environment Variables

All configuration keys (used in YAML files and the internal `Config.config` dict) and their corresponding environment variable names.

---

### `client_id` / `AZURE_CLIENT_ID`

The Application (Client) ID of the Azure AD service principal used for authentication. Optional if using default credential chain.

- **YAML key:** `client_id` — `QA-Test-Repo/examples/config.yaml` (line 9)
- **Env var:** `AZURE_CLIENT_ID` — `QA-Test-Repo/avd_manager/config.py` (line 50), `QA-Test-Repo/README.md` (line 34)
- **`AzureAuthenticator.__init__`** parameter `client_id` — `QA-Test-Repo/avd_manager/utils/auth.py` (line 12)

---

### `client_secret` / `AZURE_CLIENT_SECRET`

The client secret (password) of the Azure AD service principal. Optional if using default credential chain. Treated as a sensitive value.

- **YAML key:** `client_secret` — `QA-Test-Repo/examples/config.yaml` (line 10)
- **Env var:** `AZURE_CLIENT_SECRET` — `QA-Test-Repo/avd_manager/config.py` (line 53), `QA-Test-Repo/README.md` (line 35)
- **`AzureAuthenticator.__init__`** parameter `client_secret` — `QA-Test-Repo/avd_manager/utils/auth.py` (line 12)

---

### `host_pools` (YAML key)

A YAML list under the top-level configuration that declares named host pools with their Azure region. Used in the example configuration file only; not read by any current library code.

- **`QA-Test-Repo/examples/config.yaml`** (lines 18–22)

---

### `logging` (YAML key)

A YAML mapping under the top-level configuration that specifies the logging `level` and output `file` path. Defined in the example configuration file; consumed by application code that calls `setup_file_logging()`.

- **`QA-Test-Repo/examples/config.yaml`** (lines 13–15)

---

### `region` (YAML key)

A string value within each entry of the `host_pools` YAML list, specifying the Azure region (e.g., `"eastus"`, `"westus"`) where the host pool resides. Present in the example configuration only.

- **`QA-Test-Repo/examples/config.yaml`** (lines 20, 22)

---

### `resource_group` / `AZURE_RESOURCE_GROUP`

The name of the Azure Resource Group that contains the AVD resources. A **required** configuration field; `Config.validate()` raises `ValueError` if absent.

- **YAML key:** `resource_group` — `QA-Test-Repo/examples/config.yaml` (line 5)
- **Env var:** `AZURE_RESOURCE_GROUP` — `QA-Test-Repo/avd_manager/config.py` (line 43), `QA-Test-Repo/README.md` (line 32)
- **`ConnectionManager.__init__`** parameter — `QA-Test-Repo/avd_manager/connection_manager.py` (line 17)

---

### `subscription_id` / `AZURE_SUBSCRIPTION_ID`

The UUID identifying the Azure subscription that contains the AVD resources. A **required** configuration field; `Config.validate()` raises `ValueError` if absent.

- **YAML key:** `subscription_id` — `QA-Test-Repo/examples/config.yaml` (line 4)
- **Env var:** `AZURE_SUBSCRIPTION_ID` — `QA-Test-Repo/avd_manager/config.py` (line 38), `QA-Test-Repo/README.md` (line 31)
- **`ConnectionManager.__init__`** parameter — `QA-Test-Repo/avd_manager/connection_manager.py` (line 17)

---

### `tenant_id` / `AZURE_TENANT_ID`

The UUID of the Azure Active Directory tenant associated with the subscription and service principal. Optional if using default credential chain.

- **YAML key:** `tenant_id` — `QA-Test-Repo/examples/config.yaml` (line 8)
- **Env var:** `AZURE_TENANT_ID` — `QA-Test-Repo/avd_manager/config.py` (line 46), `QA-Test-Repo/README.md` (line 33)
- **`AzureAuthenticator.__init__`** parameter `tenant_id` — `QA-Test-Repo/avd_manager/utils/auth.py` (line 12)

---

## 7. External Dependencies and SDK Terms

Third-party packages declared in `requirements.txt` and `setup.py`, and the SDK sub-namespaces they introduce.

---

### `azure-identity` (`azure.identity`)

The Azure SDK package providing credential classes. Version pinned to `1.15.0` in `requirements.txt`. Supplies `DefaultAzureCredential` and `ClientSecretCredential`.

- **`requirements.txt`** (line 1)
- **`setup.py`** (line 12): `"azure-identity>=1.15.0"`
- **`QA-Test-Repo/avd_manager/connection_manager.py`** (line 3)
- **`QA-Test-Repo/avd_manager/utils/auth.py`** (line 3)

---

### `azure-mgmt-compute` (`azure.mgmt.compute`)

The Azure SDK management package for Compute resources. Version pinned to `30.5.0`. Supplies `ComputeManagementClient`.

- **`requirements.txt`** (line 3)
- **`setup.py`** (line 14): `"azure-mgmt-compute>=30.5.0"`
- **`QA-Test-Repo/avd_manager/connection_manager.py`** (line 4)

---

### `azure-mgmt-desktopvirtualization` (`azure.mgmt.desktopvirtualization`)

The Azure SDK management package for Azure Virtual Desktop resources. Version pinned to `1.0.0`. Supplies `DesktopVirtualizationMgmtClient` with sub-clients `host_pools`, `session_hosts`, and `user_sessions`.

- **`requirements.txt`** (line 2)
- **`setup.py`** (line 13): `"azure-mgmt-desktopvirtualization>=1.0.0"`
- **`QA-Test-Repo/avd_manager/connection_manager.py`** (line 3)

---

### `azure-mgmt-network` (`azure.mgmt.network`)

The Azure SDK management package for Networking resources. Version pinned to `25.2.0`. Supplies `NetworkManagementClient`.

- **`requirements.txt`** (line 4)
- **`setup.py`** (line 15): `"azure-mgmt-network>=25.2.0"`
- **`QA-Test-Repo/avd_manager/connection_manager.py`** (line 5)

---

### `host_pools` (SDK sub-client)

The operations sub-client on `DesktopVirtualizationMgmtClient` used to call `list_by_resource_group()` and `get()` on host pool resources.

- **`ConnectionManager.list_host_pools()`** in `QA-Test-Repo/avd_manager/connection_manager.py` (line 70): `self.avd_client.host_pools.list_by_resource_group(...)`
- **`ConnectionManager.get_host_pool()`** in `QA-Test-Repo/avd_manager/connection_manager.py` (line 85): `self.avd_client.host_pools.get(...)`

---

### `python-dotenv` (`dotenv`)

A package that loads environment variables from a `.env` file into `os.environ`. Version pinned to `1.0.0`. Called via `load_dotenv()` at the start of `Config.__init__()`.

- **`requirements.txt`** (line 5)
- **`setup.py`** (line 16): `"python-dotenv>=1.0.0"`
- **`Config.__init__()`** in `QA-Test-Repo/avd_manager/config.py` (line 22): `load_dotenv()`

---

### `pyyaml` (`yaml`)

A YAML parsing and serialization library. Version pinned to `6.0.1`. Used by `Config._load_config()` (`yaml.safe_load`) and `Config.save()` (`yaml.dump`).

- **`requirements.txt`** (line 6)
- **`setup.py`** (line 17): `"pyyaml>=6.0.1"`
- **`QA-Test-Repo/avd_manager/config.py`** (line 3): `import yaml`

---

### `requests`

The HTTP library for Python. Version pinned to `2.31.0`. Declared as a dependency in `requirements.txt` and `setup.py` but not directly imported in any current source file; reserved for future HTTP-based integrations.

- **`requirements.txt`** (line 7)
- **`setup.py`** (line 18): `"requests>=2.31.0"`

---

### `session_hosts` (SDK sub-client)

The operations sub-client on `DesktopVirtualizationMgmtClient` used to call `list()` and `get()` on session host resources.

- **`SessionHandler.list_session_hosts()`** in `QA-Test-Repo/avd_manager/session_handler.py` (line 32): `self.connection_manager.avd_client.session_hosts.list(...)`
- **`SessionHandler.get_session_host_status()`** in `QA-Test-Repo/avd_manager/session_handler.py` (line 83): `self.connection_manager.avd_client.session_hosts.get(...)`

---

### `user_sessions` (SDK sub-client)

The operations sub-client on `DesktopVirtualizationMgmtClient` used to call `list()` and `disconnect()` on user session resources.

- **`SessionHandler.get_user_sessions()`** in `QA-Test-Repo/avd_manager/session_handler.py` (line 48): `self.connection_manager.avd_client.user_sessions.list(...)`
- **`SessionHandler.disconnect_user_session()`** in `QA-Test-Repo/avd_manager/session_handler.py` (line 65): `self.connection_manager.avd_client.user_sessions.disconnect(...)`

---

## 8. Additional Implementation Notes

### Python Version Support

The project targets Python 3.8 and later, as declared in `setup.py` (line 19): `python_requires=">=3.8"`. The classifiers list explicit support for Python 3.8, 3.9, and 3.10. Code patterns such as f-strings and `pathlib.Path` usage depend on Python 3.6+ features and are compatible with the declared range.

- **`setup.py`** (line 19): `python_requires=">=3.8"`
- **`setup.py`** (lines 21–23): classifiers for Python 3.8, 3.9, 3.10

---

### Unused Import: `datetime`

The `session_handler.py` module imports `from datetime import datetime` at line 2, but this import is not used anywhere in the current source code. This is a placeholder for future timestamp-based session tracking logic (e.g., recording session start/end times, calculating session duration). Contributors should not remove this import as dead code; it signals the intended direction of future enhancements.

- **`SessionHandler`** in `QA-Test-Repo/avd_manager/session_handler.py` (line 2): `from datetime import datetime`

---

*End of Glossary. All terms verified against source files in `QA-Test-Repo/`. For system design context see [architecture.md]; for data flow see [dataflow.md]; for project layout see [structure.md]; for method-level documentation see [code.md].*